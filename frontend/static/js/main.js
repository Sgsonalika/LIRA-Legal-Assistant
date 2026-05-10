/* ═══════════════════════════════════════════════════════
   LIRA — Main JavaScript
   ═══════════════════════════════════════════════════════ */

/* ── Theme toggle ─────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', async () => {
      const cur  = document.documentElement.getAttribute('data-theme') || 'light';
      const next = cur === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      try {
        await fetch('/settings/update-theme', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ theme: next }),
        });
      } catch (_) {}
    });
  }
  // Auto-dismiss flash messages
  document.querySelectorAll('.flash').forEach(el => setTimeout(() => el.remove(), 4500));
});

/* ── Full markdown renderer ────────────────────────────── */
function renderMarkdown(raw) {
  if (!raw) return '';
  let text = raw;

  // Escape HTML first
  text = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Process line by line for block elements
  const lines = text.split('\n');
  const out   = [];
  let inUl = false, inOl = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Headings
    if (/^## (.+)/.test(line)) {
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (inOl) { out.push('</ol>'); inOl = false; }
      out.push(`<h2>${applyInline(line.replace(/^## /, ''))}</h2>`);
      continue;
    }
    if (/^### (.+)/.test(line)) {
      out.push(`<h3>${applyInline(line.replace(/^### /, ''))}</h3>`);
      continue;
    }

    // Unordered list
    if (/^[-*] (.+)/.test(line)) {
      if (inOl) { out.push('</ol>'); inOl = false; }
      if (!inUl) { out.push('<ul>'); inUl = true; }
      out.push(`<li>${applyInline(line.replace(/^[-*] /, ''))}</li>`);
      continue;
    }

    // Ordered list
    if (/^\d+\. (.+)/.test(line)) {
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (!inOl) { out.push('<ol>'); inOl = true; }
      out.push(`<li>${applyInline(line.replace(/^\d+\. /, ''))}</li>`);
      continue;
    }

    // Close lists on blank line or non-list content
    if (inUl) { out.push('</ul>'); inUl = false; }
    if (inOl) { out.push('</ol>'); inOl = false; }

    if (line.trim() === '') {
      out.push('<br>');
    } else {
      out.push(`<p>${applyInline(line)}</p>`);
    }
  }

  if (inUl) out.push('</ul>');
  if (inOl) out.push('</ol>');

  return out.join('');
}

function applyInline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/_(.+?)_/g,       '<em>$1</em>')
    .replace(/`(.+?)`/g,       '<code>$1</code>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,
             '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

/* ── Extract follow-up questions ───────────────────────── */
function extractFollowups(text) {
  const match = text.match(/##\s*💬\s*Follow-up Questions?\s*\n([\s\S]*?)(?=\n##|$)/i);
  if (!match) return [];
  return match[1].split('\n')
    .map(l => l.replace(/^[-*\d.]\s*/, '').trim())
    .filter(l => l.length > 5 && l.length < 150)
    .slice(0, 3);
}

/* ── Toast notifications ───────────────────────────────── */
function showToast(msg, type = 'success') {
  const div = document.createElement('div');
  div.className = `flash flash--${type}`;
  div.innerHTML = `<span>${msg}</span><button onclick="this.parentElement.remove()">✕</button>`;
  let c = document.querySelector('.flash-container');
  if (!c) {
    c = document.createElement('div');
    c.className = 'flash-container';
    document.body.appendChild(c);
  }
  c.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

/* ── Copy text to clipboard ────────────────────────────── */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', 'success');
  } catch (_) {
    showToast('Copy failed — please select and copy manually.', 'error');
  }
}
