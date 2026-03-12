# web/app.py — Ramo Pub & TeaHouse Web Panel (Tam versiya)
from __future__ import annotations

import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (
    Flask, render_template, redirect, url_for,
    session, g, send_from_directory, abort, request
)

from src.core.database.connection import get_db, init_database
from src.core.modules.auth.permissions import permission_service
from src.config.settings import Settings


def _resolve_media_file(path_value: str | None):
    """
    DB-də saxlanan şəkil yolunu web üçün oxuna bilən fayla çevir.
    Həm mütləq yol, həm nisbi yol, həm də sadəcə fayl adını dəstəkləyir.
    """
    if not path_value:
        return None

    # Əgər mütləq yol verilib və fayl mövcuddursa — birbaşa qaytar
    if os.path.isabs(path_value) and os.path.isfile(path_value):
        return os.path.dirname(path_value), os.path.basename(path_value)

    candidate = os.path.basename(path_value)
    if not candidate:
        return None

    # Kök qovluğu
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WEB = os.path.dirname(os.path.abspath(__file__))

    search_dirs = [
        # Web static uploads
        os.path.join(WEB,  "static", "uploads"),
        # Desktop assets (əsas şəkil mənbəyi)
        os.path.join(ROOT, "assets", "table_images"),
        os.path.join(ROOT, "assets", "menu_images"),
        os.path.join(ROOT, "assets"),
        # Desktop qovluğu altında
        os.path.join(ROOT, "desktop", "assets", "table_images"),
        os.path.join(ROOT, "desktop", "assets", "menu_images"),
        os.path.join(ROOT, "desktop", "assets"),
        # Fayl özünün qovluğu (mütləq yol deyilsə)
        os.path.join(ROOT, os.path.dirname(path_value)) if not os.path.isabs(path_value) else None,
    ]

    for folder in search_dirs:
        if not folder:
            continue
        full = os.path.join(folder, candidate)
        if os.path.isfile(full):
            return folder, candidate

    return None


def create_app(config: dict = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    
    # Load modern settings
    settings = Settings()
    
    # Register assets routes
    from src.web.assets_routes import register_assets_routes
    # register_assets_routes(app)  # KÖHNƏ SİL
    
    # YENİ ASSETS ROUTE
    @app.route('/assets/<path:filename>')
    def assets_static(filename):
        # Proyektin ana kökünü tap
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Şəkli 3 yerdə ardıcıl axtar (Tapana qədər):
        locations = [
            os.path.join(root, 'assets', 'table_images'),
            os.path.join(root, 'assets', 'menu_images'),
            os.path.join(root, 'assets')
        ]
        
        for loc in locations:
            target_file = os.path.join(loc, filename)
            if os.path.exists(target_file):
                return send_from_directory(loc, filename)
                
        return "Fayl tapilmadi", 404
    
    # ── Konfiqurasiya ─────────────────────────────────────────────────────────
    app.secret_key = settings.flask.secret_key or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    )
    app.config["MAX_CONTENT_LENGTH"] = settings.max_file_size

    if config:
        app.config.update(config)

    # ── Verilənlər bazası ─────────────────────────────────────────────────────
    @app.before_request
    def open_db():
        g.db = get_db()

    @app.teardown_request
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        
        # Anti-Tracking Prevention Headers for localhost
        if '127.0.0.1' in request.host or 'localhost' in request.host:
            resp.headers.setdefault("Access-Control-Allow-Origin", "*")
            resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            resp.headers.setdefault("Access-Control-Allow-Headers", "*")
            resp.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        
        return resp

    # ── Blueprint-lər ─────────────────────────────────────────────────────────
    from src.web.routes import auth_routes, dashboard, tables, menu, orders, reports
    from src.web.routes.reservations import reservations_bp
    from src.web.routes.loyalty import loyalty_bp
    from src.web.routes.inventory import inventory_bp
    from src.web.routes.staff import staff_bp
    from src.web.routes.pos import pos_bp
    from src.web.routes.settings import settings_bp
    from src.web.routes.receipt import receipt_bp
    from src.web.routes.kitchen import kitchen_bp
    # from src.web.enterprise_routes import enterprise_bp  # Commented out due to missing services

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(tables.bp)
    app.register_blueprint(menu.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(loyalty_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(receipt_bp)
    app.register_blueprint(kitchen_bp)
    # app.register_blueprint(enterprise_bp)  # Commented out due to missing services

    # ── Şablon kontekst prosessoru ────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from datetime import datetime as _dt
        return {
            "app_name":     "Ramo Pub & TeaHouse",
            "current_user": session.get("user"),
            "now":          _dt.now,
            "media_url": lambda p: (
                f"/assets/{os.path.basename(p)}" if p else ""
            ),
            "can": lambda perm: permission_service.has_permission(session.get("user", {}).get("role"), perm),
        }

    # ── Kök marşrut ───────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard.index"))

    @app.route("/media/<path:filename>")
    def media_file(filename: str):
        resolved = _resolve_media_file(filename)
        if not resolved:
            abort(404)
        folder, fname = resolved
        return send_from_directory(folder, fname)

    # ── Xəta səhifələri ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    return app


if __name__ == "__main__":
    ok, msg = init_database()
    if not ok:
        print(f"[XƏTA] Verilənlər bazasına qoşulmaq olmadı: {msg}")
        sys.exit(1)

    # Database session-ı yenilə
    from src.core.database.connection import get_db
    try:
        test_db = get_db()
        test_db.close()
        print("[OK] Database connection verified")
    except Exception as e:
        print(f"[XƏTA] Database connection failed: {e}")
        sys.exit(1)

    app = create_app()
    print("[OK] Ramo Pub Web Paneli başlayır...")
    print("[OK] http://localhost:5000")
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
