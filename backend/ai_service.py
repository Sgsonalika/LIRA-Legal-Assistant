"""
backend/ai_service.py — Gemini AI (google-genai SDK v1+)
Fixes:
  1. Filter out TTS/audio-only models (400 INVALID_ARGUMENT)
  2. API key read from env on EVERY request — no session needed
  3. Proper retry: 404→skip, 429/503→wait+retry
"""

import os, re, time

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Models to NEVER use (audio/image/embedding only)
_BLOCKED_KEYWORDS = ["tts", "audio", "imagen", "embedding", "aqa", "retrieval"]

_PREFERRED = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

_model_cache: list[str] = []


def _get_key(provided: str = "") -> str:
    """Env var ALWAYS wins — read fresh every call."""
    return os.environ.get("GEMINI_API_KEY", "").strip() or str(provided or "").strip()


def _is_text_model(name: str) -> bool:
    n = name.lower()
    return not any(kw in n for kw in _BLOCKED_KEYWORDS)


def _get_models(client) -> list[str]:
    global _model_cache
    if _model_cache:
        return _model_cache
    try:
        available = []
        for m in client.models.list():
            raw     = getattr(m, "name", "") or ""
            actions = getattr(m, "supported_actions", []) or []
            clean   = raw.replace("models/", "").strip()
            if "generateContent" in actions and clean and _is_text_model(clean):
                available.append(clean)

        def _rank(n):
            for i, p in enumerate(_PREFERRED):
                if n.startswith(p.split("-preview")[0]):
                    return i
            return len(_PREFERRED)

        _model_cache = sorted(available, key=_rank) or list(_PREFERRED)
        return _model_cache
    except Exception:
        return [m for m in _PREFERRED if _is_text_model(m)]


def _generate(api_key: str, contents, system: str = None) -> str:
    key = _get_key(api_key)
    if not key:
        raise RuntimeError("NO_API_KEY")
    if not GEMINI_AVAILABLE:
        raise RuntimeError("google-genai not installed")

    client = genai.Client(api_key=key)
    models = _get_models(client)
    errors: dict[str, str] = {}

    for model in models:
        for attempt in range(3):
            try:
                kwargs = {"model": model, "contents": contents}
                if system:
                    kwargs["config"] = {"system_instruction": system}
                return client.models.generate_content(**kwargs).text

            except Exception as exc:
                msg = str(exc)

                # 400 invalid argument (TTS model, wrong modality) → skip
                if "400" in msg or "INVALID_ARGUMENT" in msg:
                    errors[model] = "400"
                    break

                # 404 model not found → skip
                if "404" in msg or "NOT_FOUND" in msg:
                    errors[model] = "404"
                    break

                # 429 / 503 quota / unavailable → wait and retry
                if ("429" in msg or "RESOURCE_EXHAUSTED" in msg
                        or "503" in msg or "UNAVAILABLE" in msg):
                    errors[model] = "quota"
                    if attempt < 2:
                        wait = 18
                        m = re.search(r'(\d+)s', msg)
                        if m:
                            wait = min(int(m.group(1)) + 3, 45)
                        time.sleep(wait)
                        continue
                    break

                # Auth / other hard errors
                raise RuntimeError(f"API error: {msg}") from exc

    # All models failed
    has_quota = any(v == "quota" for v in errors.values())
    if has_quota:
        raise RuntimeError("QUOTA_OR_UNAVAILABLE")
    raise RuntimeError(f"NO_VALID_MODEL — tried: {list(errors.keys())}")


# ── System prompt ─────────────────────────────────────────────────────────────

LEGAL_SYSTEM = """You are LIRA — Legal Intelligence & Research Assistant.
Expert in Indian and international law. ALWAYS structure every response EXACTLY as shown below.
Use proper markdown — each section heading on its own line, bullet points with hyphens.

## 📋 Summary
[2-3 clear sentences summarising the answer]

## ⚖️ Legal Basis
- **[Act/Section]**: [Explanation]
- **[Act/Section]**: [Explanation]
- **[Case Name, Year]**: [Relevance]

## 📌 Key Points
- [Point 1]
- [Point 2]
- [Point 3]

## 🛡️ Practical Advice
1. **[Step 1]**: [Details]
2. **[Step 2]**: [Details]
3. **[Step 3]**: [Details]

## 💬 Follow-up Questions
- [Short clickable question 1?]
- [Short clickable question 2?]
- [Short clickable question 3?]

## ⚠️ Disclaimer
*AI-generated legal information for educational purposes only. Consult a qualified lawyer.*"""

ANALYSIS_SYSTEM = """You are LIRA — expert legal document analyst.
ALWAYS structure your response EXACTLY as shown. Use markdown — headings, bullet points, bold.

## 📋 Executive Summary
[2-3 sentences: what this document is and its key purpose]

## ⚖️ Key Legal Points
- **[Point]**: [Explanation]
- **[Point]**: [Explanation]

## ⚠️ Risk Areas
- **[Risk Area]**: [Why it's a risk and what could go wrong]
- **[Risk Area]**: [Why it's a risk]

## 📌 Important Clauses
- **[Clause Name]**: [Brief quote or description] — [Analysis of implications]
- **[Clause Name]**: [Brief quote or description] — [Analysis]

## 🔍 Direct Answer
[Direct answer to the user's specific question, with clause references]

## 💡 Recommendations
1. **[Action]**: [Details]
2. **[Action]**: [Details]
3. **[Action]**: [Details]

## ⚠️ Disclaimer
*For informational purposes only. Consult a qualified lawyer before signing.*"""


# ── Public API ────────────────────────────────────────────────────────────────

def legal_research(query: str, history: list, api_key: str) -> str:
    msgs = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [{"text": m["content"]}]}
        for m in history[-10:]
    ]
    msgs.append({"role": "user", "parts": [{"text": query}]})
    try:
        return _generate(api_key, msgs, system=LEGAL_SYSTEM)
    except RuntimeError as e:
        return _friendly(str(e))
    except Exception as e:
        return _friendly(str(e))


def generate_document(doc_type: str, fields: dict, api_key: str) -> str:
    try:
        return _generate(api_key, _doc_prompt(doc_type, fields))
    except RuntimeError as e:
        return _friendly(str(e), is_doc=True, doc_type=doc_type, fields=fields)
    except Exception as e:
        return _friendly(str(e), is_doc=True, doc_type=doc_type, fields=fields)


def analyze_document(text: str, question: str, api_key: str) -> str:
    prompt = (f"DOCUMENT TEXT:\n\"\"\"\n{text[:14000]}\n\"\"\"\n\n"
              f"USER QUESTION: {question}\n\n"
              "Now analyse the document following your structured format exactly.")
    try:
        return _generate(api_key, prompt, system=ANALYSIS_SYSTEM)
    except RuntimeError as e:
        return _friendly(str(e))
    except Exception as e:
        return _friendly(str(e))


def generate_title(query: str, api_key: str) -> str:
    try:
        return _generate(
            api_key,
            f"Create a 4-6 word title for this legal question (no quotes, no punctuation at all): {query}"
        ).strip()[:60]
    except Exception:
        return " ".join(query.split()[:6]) + ("…" if len(query.split()) > 6 else "")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_prompt(doc_type: str, fields: dict) -> str:
    fields_text = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}" for k, v in fields.items() if v
    )
    return (f"You are a senior Indian legal document drafter with 20+ years experience.\n\n"
            f"Draft a complete, professional {doc_type}:\n{fields_text}\n\n"
            "Requirements:\n"
            "1. Proper legal language — precise, unambiguous, professional\n"
            "2. ALL standard clauses required under Indian law\n"
            "3. Full signature blocks with space for parties, witnesses, date, place\n"
            "4. Numbered sections (1., 1.1, 1.2) with CAPITALISED headings\n"
            "5. Recitals / WHEREAS clauses at the start\n"
            "6. Governing law, dispute resolution, severability clauses\n"
            "7. Be thorough — produce a complete, court-ready document\n\n"
            "Start with the document title centered in CAPS. Generate the full document now:")


def _friendly(msg: str, is_doc=False, doc_type="", fields=None) -> str:
    if "NO_API_KEY" in msg:
        return ("## ⚙️ No API Key Configured\n\n"
                "Set your Gemini API key **before** starting the app:\n\n"
                "**Windows PowerShell:**\n"
                "```\n$env:GEMINI_API_KEY = \"AIza...\"\npython main.py\n```\n\n"
                "**macOS / Linux:**\n"
                "```\nexport GEMINI_API_KEY=\"AIza...\"\npython main.py\n```\n\n"
                "Free key: https://aistudio.google.com/app/apikey")
    if "QUOTA_OR_UNAVAILABLE" in msg:
        return ("## ⏳ All Models Temporarily Busy\n\n"
                "All Gemini models are over quota or temporarily unavailable.\n\n"
                "- **Wait 1-2 minutes** and try again (per-minute quota resets)\n"
                "- Daily quota resets at midnight\n"
                "- Upgrade at https://ai.google.dev for higher limits")
    if "NO_VALID_MODEL" in msg:
        return ("## ⚠️ No Compatible Model Found\n\n"
                "Your API key has no access to any available text models.\n"
                "Check your key at https://aistudio.google.com")
    if "401" in msg or "API_KEY_INVALID" in msg:
        return "## 🔑 Invalid API Key\n\nUpdate it in **Settings → AI Configuration**."
    if is_doc:
        p = (fields or {})
        party = p.get("employer", p.get("sender", p.get("party_a", p.get("landlord", "Party A"))))
        return (f"                    {doc_type.upper()}\n\n"
                f"⚠️ {msg[:200]}\n\nParty: {party}\n\n"
                "Please wait 1-2 minutes and try again.")
    return f"## ⚠️ Error\n\n{msg[:300]}\n\nPlease wait a moment and try again."
