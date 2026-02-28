# web/app.py
# Python 3.10 uyğun — Flask Web Paneli
"""
Ramo Pub & TeaHouse — Web İdarə Paneli
Əsas Flask tətbiqi.
"""

from __future__ import annotations

import os
import sys

# Proyektin kök qovluğunu Python path-ə əlavə et
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (
    Flask, render_template, redirect, url_for,
    session, flash, request, jsonify, g
)
from functools import wraps
from typing import Callable, Any

# Verilənlər bazası
from database.connection import get_db, init_database
from modules.auth.auth_service import AuthService

# Route modulları
from web.routes import dashboard, tables, menu, orders, reports, auth_routes
from web.routes.reservations import reservations_bp
from web.routes.loyalty      import loyalty_bp
from web.routes.inventory    import inventory_bp


def create_app(config: dict = None) -> Flask:
    """Flask tətbiqi fabrikası."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Konfiqurasiya ─────────────────────────────────────────────────────────
    app.secret_key = os.environ.get("FLASK_SECRET", "ramo-pub-secret-key-2024")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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

    # ── Blueprint-lər ─────────────────────────────────────────────────────────
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(tables.bp)
    app.register_blueprint(menu.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(loyalty_bp)
    app.register_blueprint(inventory_bp)

    # ── Şablon kontekst prosessoru ────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from datetime import datetime as _dt
        return {
            "app_name":    "Ramo Pub & TeaHouse",
            "current_user": session.get("user"),
            "now":         _dt.now,
        }

    # ── Kök marşrut ───────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard.index"))

    # ── Xəta səhifələri ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    return app


# ── Giriş tələb edən decorator ────────────────────────────────────────────────
def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if "user" not in session:
            flash("Zəhmət olmasa, əvvəlcə giriş edin.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session["user"].get("role") != "admin":
            flash("Bu səhifəyə giriş icazəniz yoxdur.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


if __name__ == "__main__":
    ok, msg = init_database()
    if not ok:
        print(f"[XƏTA] Verilənlər bazasına qoşulmaq olmadı: {msg}")
        sys.exit(1)
    app = create_app()
    print("[OK] Ramo Pub Web Paneli başlayır...")
    print("[OK] http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
