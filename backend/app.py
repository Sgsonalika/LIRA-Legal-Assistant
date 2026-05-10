"""backend/app.py"""
import os
from flask import Flask, session
from flask_login import LoginManager
from backend.database import init_db, migrate_db
from backend.models import User


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "lira-secret-2026")
    app.config["DATABASE"]   = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "lira.db"
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30

    lm = LoginManager()
    lm.login_view = "auth.login"
    lm.login_message = "Please log in to access LIRA."
    lm.init_app(app)

    @lm.user_loader
    def load_user(uid):
        return User.get_by_id(uid, app.config["DATABASE"])

    def get_api_key():
        """
        Try every common env var name the user might have set,
        then fall back to the session key entered via Settings.
        Checked fresh on every single call.
        """
        for var in ("GEMINI_API_KEY", "GEMINIAPIKEY", "GEMINI_KEY", "GOOGLE_API_KEY"):
            val = os.environ.get(var, "").strip()
            if val:
                return val
        return session.get("gemini_api_key", "").strip()

    app.get_api_key = get_api_key

    with app.app_context():
        init_db(app.config["DATABASE"])
        migrate_db(app.config["DATABASE"])

    from backend.routes.home      import home_bp
    from backend.routes.auth      import auth_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.research  import research_bp
    from backend.routes.drafting  import drafting_bp
    from backend.routes.analyzer  import analyzer_bp
    from backend.routes.settings  import settings_bp
    from backend.routes.pages     import pages_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp,       url_prefix="/auth")
    app.register_blueprint(dashboard_bp,  url_prefix="/dashboard")
    app.register_blueprint(research_bp,   url_prefix="/research")
    app.register_blueprint(drafting_bp,   url_prefix="/drafting")
    app.register_blueprint(analyzer_bp,   url_prefix="/analyzer")
    app.register_blueprint(settings_bp,   url_prefix="/settings")
    app.register_blueprint(pages_bp)

    return app
