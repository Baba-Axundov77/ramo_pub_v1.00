# web/app.py
# Python 3.10 uyğun — Flask Web Paneli
"""
Ramo Pub & TeaHouse — Web İdarə Paneli
Əsas Flask tətbiqi.
"""

from __future__ import annotations

import os
import sys
import secrets

# Proyektin kök qovluğunu Python path-ə əlavə et
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, redirect, url_for, session, request, g
from flask import (
    Flask, render_template, redirect, url_for,
    session, flash, request, jsonify, g
)
import secrets
from functools import wraps
from typing import Callable, Any

# Verilənlər bazası
from database.connection import get_db, init_database

# Route modulları
from web.routes import dashboard, tables, menu, orders, reports, auth_routes
from web.routes.reservations import reservations_bp
from web.routes.loyalty import loyalty_bp
from web.routes.inventory import inventory_bp


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def create_app(config: dict = None) -> Flask:
    """Flask tətbiqi fabrikası."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Konfiqurasiya ─────────────────────────────────────────────────────────
    app.secret_key = os.environ.get("FLASK_SECRET") or os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    if config:
        app.config.update(config)

    # ── Verilənlər bazası ─────────────────────────────────────────────────────
    @app.before_request
    def open_db():
        g.db = get_db()

    @app.before_request
    def verify_csrf():
        if request.method not in _MUTATING_METHODS:
            return None

        if request.path.startswith("/tables/api/"):
            sent = request.headers.get("X-CSRF-Token")
        else:
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

        expected = session.get("csrf_token")
        if not expected or not sent or not secrets.compare_digest(expected, sent):
            return render_template("errors/500.html"), 400
        return None

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
            "app_name": "Ramo Pub & TeaHouse",
            "current_user": session.get("user"),
            "now": _dt.now,
            "csrf_token": _csrf_token,
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


if __name__ == "__main__":
    ok, msg = init_database()
    if not ok:
        print(f"[XƏTA] Verilənlər bazasına qoşulmaq olmadı: {msg}")
        sys.exit(1)
    app = create_app()
    print("[OK] Ramo Pub Web Paneli başlayır...")
    print("[OK] http://localhost:5000")
    debug_enabled = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_enabled)
