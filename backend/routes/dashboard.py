"""backend/routes/dashboard.py"""
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from backend.database import get_db

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    db = get_db(current_app.config["DATABASE"])
    sessions = db.execute(
        """SELECT id,title,updated_at,is_pinned FROM chat_sessions
           WHERE user_id=? AND is_archived=0 ORDER BY is_pinned DESC, updated_at DESC LIMIT 8""",
        (current_user.id,)
    ).fetchall()
    docs = db.execute(
        """SELECT id,title,doc_type,created_at,is_pinned FROM documents
           WHERE user_id=? AND is_archived=0 ORDER BY is_pinned DESC, created_at DESC LIMIT 8""",
        (current_user.id,)
    ).fetchall()
    analyses = db.execute(
        """SELECT id,title,created_at FROM doc_analyses
           WHERE user_id=? ORDER BY created_at DESC LIMIT 6""",
        (current_user.id,)
    ).fetchall()
    total_research = db.execute(
        "SELECT COUNT(*) FROM chat_sessions WHERE user_id=?", (current_user.id,)
    ).fetchone()[0]
    total_docs = db.execute(
        "SELECT COUNT(*) FROM documents WHERE user_id=?", (current_user.id,)
    ).fetchone()[0]
    total_analyses = db.execute(
        "SELECT COUNT(*) FROM doc_analyses WHERE user_id=?", (current_user.id,)
    ).fetchone()[0]
    db.close()
    return render_template("dashboard.html",
        sessions=sessions, docs=docs, analyses=analyses,
        total_research=total_research, total_docs=total_docs,
        total_analyses=total_analyses)
