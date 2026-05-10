"""backend/routes/settings.py — sub-pages: profile, appearance, api, archive"""
import os
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from flask_login import login_required, current_user
from backend.models import User, ROLES
from backend.database import get_db

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
@login_required
def index():
    return redirect(url_for("settings.profile"))


@settings_bp.route("/profile")
@login_required
def profile():
    return render_template("settings/profile.html", roles=ROLES)


@settings_bp.route("/appearance")
@login_required
def appearance():
    return render_template("settings/appearance.html")


@settings_bp.route("/api-key")
@login_required
def api_key():
    has_env_key = any(
        os.environ.get(v, "").strip()
        for v in ("GEMINI_API_KEY", "GEMINIAPIKEY", "GEMINI_KEY", "GOOGLE_API_KEY")
    )
    active_env_var = next(
        (v for v in ("GEMINI_API_KEY","GEMINIAPIKEY","GEMINI_KEY","GOOGLE_API_KEY")
         if os.environ.get(v,"").strip()), None
    )
    return render_template("settings/api_key.html",
                           has_env_key=has_env_key,
                           active_env_var=active_env_var)


@settings_bp.route("/archive")
@login_required
def archive():
    db = get_db(current_app.config["DATABASE"])
    archived_chats = db.execute(
        "SELECT * FROM chat_sessions WHERE user_id=? AND is_archived=1 ORDER BY updated_at DESC",
        (current_user.id,)
    ).fetchall()
    archived_docs = db.execute(
        "SELECT * FROM documents WHERE user_id=? AND is_archived=1 ORDER BY created_at DESC",
        (current_user.id,)
    ).fetchall()
    db.close()
    return render_template("settings/archive.html",
                           archived_chats=archived_chats,
                           archived_docs=archived_docs)


# ── API endpoints ─────────────────────────────────────────────────

@settings_bp.route("/update-name", methods=["POST"])
@login_required
def update_name():
    name = request.get_json().get("name", "").strip()
    if not name: return jsonify({"error": "Name required"}), 400
    current_user.update_name(name, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@settings_bp.route("/update-role", methods=["POST"])
@login_required
def update_role():
    role = request.get_json().get("role", "").strip()
    current_user.update_role(role, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@settings_bp.route("/update-theme", methods=["POST"])
@login_required
def update_theme():
    theme = request.get_json().get("theme", "light")
    if theme not in ("light", "dark"): return jsonify({"error": "Invalid"}), 400
    current_user.update_theme(theme, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@settings_bp.route("/update-api-key", methods=["POST"])
@login_required
def update_api_key():
    key = request.get_json().get("api_key", "").strip()
    session["gemini_api_key"] = key
    session.permanent = True
    return jsonify({"ok": True})


@settings_bp.route("/unarchive-chat/<int:sid>", methods=["POST"])
@login_required
def unarchive_chat(sid):
    db = get_db(current_app.config["DATABASE"])
    db.execute("UPDATE chat_sessions SET is_archived=0 WHERE id=? AND user_id=?",
               (sid, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})


@settings_bp.route("/delete-archived-chat/<int:sid>", methods=["POST"])
@login_required
def delete_archived_chat(sid):
    db = get_db(current_app.config["DATABASE"])
    db.execute("DELETE FROM chat_messages WHERE session_id=?", (sid,))
    db.execute("DELETE FROM chat_sessions WHERE id=? AND user_id=?", (sid, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})


@settings_bp.route("/unarchive-doc/<int:did>", methods=["POST"])
@login_required
def unarchive_doc(did):
    db = get_db(current_app.config["DATABASE"])
    db.execute("UPDATE documents SET is_archived=0 WHERE id=? AND user_id=?",
               (did, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})


@settings_bp.route("/delete-archived-doc/<int:did>", methods=["POST"])
@login_required
def delete_archived_doc(did):
    db = get_db(current_app.config["DATABASE"])
    db.execute("DELETE FROM documents WHERE id=? AND user_id=?", (did, current_user.id))
    db.commit(); db.close()
    return jsonify({"ok": True})
