# web/routes/auth_routes.py — Giriş & Çıxış
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from modules.auth.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")
_svc = AuthService()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        ok, user_or_msg = _svc.login(g.db, username, password)
        if ok:
            user = user_or_msg
            session["user"] = {
                "id":        user.id,
                "username":  user.username,
                "full_name": user.full_name,
                "role":      user.role.value,
            }
            flash(f"Xoş gəldiniz, {user.full_name}!", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash(str(user_or_msg), "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Çıxış edildi.", "info")
    return redirect(url_for("auth.login"))
