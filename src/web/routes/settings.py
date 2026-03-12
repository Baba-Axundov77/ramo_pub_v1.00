from __future__ import annotations

import os

from flask import Blueprint, flash, redirect, render_template, request, url_for

from src.web.auth import permission_required

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/")
@permission_required("manage_settings")
def index():
    return render_template(
        "settings/index.html",
        settings={
            "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "0"),
            "FLASK_DEBUG": os.getenv("FLASK_DEBUG", "0"),
            "DB_HOST": os.getenv("DB_HOST", "localhost"),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "DB_NAME": os.getenv("DB_NAME", "ramo_pub"),
            "ALLOW_NEGATIVE_STOCK": os.getenv("ALLOW_NEGATIVE_STOCK", "0"),
        },
    )


@settings_bp.route("/save", methods=["POST"])
@permission_required("manage_settings")
def save():
    flash("Bu panel hazırda read-only rejimindədir. Konfiqurasiyanı .env ilə idarə edin.", "info")
    return redirect(url_for("settings.index"))
