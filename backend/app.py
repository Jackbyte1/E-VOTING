import os
from pathlib import Path

from flask import Flask, send_from_directory, session
from flask_cors import CORS

from backend.config import AUTO_SEED_ON_STARTUP, BASE_DIR, FRONTEND_ORIGIN, SECRET_KEY, SESSION_COOKIE_SECURE
from backend.routes.admin_routes import admin_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.voting_routes import voting_bp
from backend.seed import seed_sample_data
from backend.utils.db import init_db
from backend.utils.responses import error


def create_app() -> Flask:
    frontend_dir = BASE_DIR / "frontend"
    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="",
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
    app.config["PREFERRED_URL_SCHEME"] = "https" if SESSION_COOKIE_SECURE else "http"
    CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN])

    init_db()
    if AUTO_SEED_ON_STARTUP:
        seed_sample_data()
    app.register_blueprint(auth_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir / "html", "login.html")

    @app.get("/pages/<path:filename>")
    def pages(filename):
        protected_pages = {
            "dashboard.html": "student",
            "vote.html": "student",
            "profile.html": "student",
            "verify.html": "student",
            "confirmation.html": "student",
            "admin.html": "admin",
        }
        required_role = protected_pages.get(filename)
        if required_role and (
            not session.get("user_id")
            or not session.get("otp_verified")
            or session.get("role") != required_role
        ):
            return send_from_directory(frontend_dir / "html", "login.html")
        return send_from_directory(frontend_dir / "html", filename)

    @app.errorhandler(404)
    def not_found(_):
        return error("Route not found.", 404)

    @app.errorhandler(500)
    def server_error(_):
        return error("Unexpected server error.", 500)

    return app


app = create_app()


if __name__ == "__main__":
    if not Path(BASE_DIR / "database" / "evoting.db").exists():
        seed_sample_data()
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug, host="0.0.0.0", port=port, use_reloader=False)
