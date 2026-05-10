"""
backend/routes/analyzer.py
===========================
Document Intelligence — upload a PDF or paste text,
ask questions about it, get structured legal analysis.
"""

import io
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from backend.database import get_db
from backend.ai_service import analyze_document

analyzer_bp = Blueprint("analyzer", __name__)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()
    except ImportError:
        pass
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n\n".join(page.get_text() for page in doc).strip()
    except ImportError:
        return ""


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a .docx file."""
    try:
        from docx import Document
        from io import BytesIO
        doc = Document(BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs).strip()
    except Exception:
        return ""


@analyzer_bp.route("/")
@login_required
def index():
    db = get_db(current_app.config["DATABASE"])
    analyses = db.execute(
        """SELECT id, title, created_at FROM doc_analyses
           WHERE user_id = ? ORDER BY created_at DESC LIMIT 20""",
        (current_user.id,)
    ).fetchall()
    db.close()
    return render_template("analyzer.html", analyses=analyses)


@analyzer_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    question = request.form.get("question", "").strip()
    doc_text  = request.form.get("doc_text",  "").strip()

    # Handle file upload
    uploaded = request.files.get("doc_file")
    if uploaded and uploaded.filename:
        file_bytes = uploaded.read()
        fname = uploaded.filename.lower()
        if fname.endswith(".pdf"):
            doc_text = _extract_text_from_pdf(file_bytes)
            if not doc_text:
                return jsonify({"error": "Could not extract text from PDF. Try pasting the text directly."}), 400
        elif fname.endswith(".docx"):
            doc_text = _extract_text_from_docx(file_bytes)
        elif fname.endswith(".txt"):
            doc_text = file_bytes.decode("utf-8", errors="replace")
        else:
            return jsonify({"error": "Supported formats: PDF, DOCX, TXT"}), 400

    if not doc_text:
        return jsonify({"error": "Please provide a document (upload or paste text)."}), 400
    if not question:
        question = "Please analyse this document and identify any key legal issues, risks, or important clauses."

    api_key = current_app.get_api_key()
    result  = analyze_document(doc_text, question, api_key)

    # Save to history
    title = question[:80] + ("…" if len(question) > 80 else "")
    db = get_db(current_app.config["DATABASE"])
    try:
        cur = db.execute(
            "INSERT INTO doc_analyses (user_id, title, question, answer, doc_snippet) VALUES (?,?,?,?,?)",
            (current_user.id, title, question, result, doc_text[:500])
        )
        db.commit()
        analysis_id = cur.lastrowid
    except Exception:
        analysis_id = None
    db.close()

    return jsonify({"result": result, "analysis_id": analysis_id})


@analyzer_bp.route("/get/<int:analysis_id>")
@login_required
def get_analysis(analysis_id):
    db = get_db(current_app.config["DATABASE"])
    row = db.execute(
        "SELECT * FROM doc_analyses WHERE id = ? AND user_id = ?",
        (analysis_id, current_user.id)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "question": row["question"],
        "answer":   row["answer"],
        "snippet":  row["doc_snippet"],
        "title":    row["title"],
    })


@analyzer_bp.route("/delete/<int:analysis_id>", methods=["POST"])
@login_required
def delete(analysis_id):
    db = get_db(current_app.config["DATABASE"])
    db.execute(
        "DELETE FROM doc_analyses WHERE id = ? AND user_id = ?",
        (analysis_id, current_user.id)
    )
    db.commit()
    db.close()
    return jsonify({"ok": True})
