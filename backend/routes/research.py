"""backend/routes/research.py — with pin/archive/rename"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from backend.database import get_db
from backend.ai_service import legal_research, generate_title

research_bp = Blueprint("research", __name__)


@research_bp.route("/")
@login_required
def index():
    db = get_db(current_app.config["DATABASE"])
    sessions = db.execute(
        """SELECT * FROM chat_sessions WHERE user_id=? AND is_archived=0
           ORDER BY is_pinned DESC, updated_at DESC""",
        (current_user.id,)
    ).fetchall()
    db.close()
    return render_template("research.html", sessions=sessions, active_session=None, messages=[])


@research_bp.route("/session/<int:session_id>")
@login_required
def session(session_id):
    db = get_db(current_app.config["DATABASE"])
    sess = db.execute(
        "SELECT * FROM chat_sessions WHERE id=? AND user_id=?",
        (session_id, current_user.id)
    ).fetchone()
    if not sess:
        db.close()
        return redirect(url_for("research.index"))
    sessions = db.execute(
        """SELECT * FROM chat_sessions WHERE user_id=? AND is_archived=0
           ORDER BY is_pinned DESC, updated_at DESC""",
        (current_user.id,)
    ).fetchall()
    messages = db.execute(
        "SELECT * FROM chat_messages WHERE session_id=? ORDER BY created_at",
        (session_id,)
    ).fetchall()
    db.close()
    return render_template("research.html", sessions=sessions,
                           active_session=sess, messages=messages)


@research_bp.route("/new", methods=["POST"])
@login_required
def new_session():
    db  = get_db(current_app.config["DATABASE"])
    cur = db.execute(
        "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
        (current_user.id, "New Research")
    )
    db.commit()
    sid = cur.lastrowid
    db.close()
    return redirect(url_for("research.session", session_id=sid))


@research_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    data       = request.get_json()
    session_id = data.get("session_id")
    query      = data.get("query", "").strip()
    if not query or not session_id:
        return jsonify({"error": "Missing query or session"}), 400

    db   = get_db(current_app.config["DATABASE"])
    sess = db.execute(
        "SELECT * FROM chat_sessions WHERE id=? AND user_id=?",
        (session_id, current_user.id)
    ).fetchone()
    if not sess:
        db.close()
        return jsonify({"error": "Session not found"}), 404

    history = [
        {"role": r["role"], "content": r["content"]}
        for r in db.execute(
            "SELECT role,content FROM chat_messages WHERE session_id=? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    ]

    # Save user message
    db.execute(
        "INSERT INTO chat_messages (session_id,role,content) VALUES (?,?,?)",
        (session_id, "user", query)
    )

    # Auto-title on first message
    if not history:
        title = generate_title(query, current_app.get_api_key())
        db.execute(
            "UPDATE chat_sessions SET title=?, updated_at=datetime('now') WHERE id=?",
            (title, session_id)
        )
    else:
        db.execute(
            "UPDATE chat_sessions SET updated_at=datetime('now') WHERE id=?",
            (session_id,)
        )
    db.commit()

    answer = legal_research(query, history, current_app.get_api_key())

    db.execute(
        "INSERT INTO chat_messages (session_id,role,content) VALUES (?,?,?)",
        (session_id, "assistant", answer)
    )
    db.commit()

    updated_title = db.execute(
        "SELECT title FROM chat_sessions WHERE id=?", (session_id,)
    ).fetchone()["title"]
    db.close()

    return jsonify({"answer": answer, "title": updated_title})


@research_bp.route("/rename/<int:session_id>", methods=["POST"])
@login_required
def rename(session_id):
    data  = request.get_json()
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    db = get_db(current_app.config["DATABASE"])
    db.execute("UPDATE chat_sessions SET title=? WHERE id=? AND user_id=?",
               (title, session_id, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})


@research_bp.route("/pin/<int:session_id>", methods=["POST"])
@login_required
def pin(session_id):
    db  = get_db(current_app.config["DATABASE"])
    row = db.execute("SELECT is_pinned FROM chat_sessions WHERE id=? AND user_id=?",
                     (session_id, current_user.id)).fetchone()
    if not row:
        db.close(); return jsonify({"error": "Not found"}), 404
    new_val = 0 if row["is_pinned"] else 1
    db.execute("UPDATE chat_sessions SET is_pinned=? WHERE id=?", (new_val, session_id))
    db.commit(); db.close()
    return jsonify({"ok": True, "pinned": bool(new_val)})


@research_bp.route("/archive/<int:session_id>", methods=["POST"])
@login_required
def archive(session_id):
    db = get_db(current_app.config["DATABASE"])
    db.execute("UPDATE chat_sessions SET is_archived=1 WHERE id=? AND user_id=?",
               (session_id, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})


@research_bp.route("/delete/<int:session_id>", methods=["POST"])
@login_required
def delete(session_id):
    db = get_db(current_app.config["DATABASE"])
    db.execute("DELETE FROM chat_messages WHERE session_id=?", (session_id,))
    db.execute("DELETE FROM chat_sessions WHERE id=? AND user_id=?",
               (session_id, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})
