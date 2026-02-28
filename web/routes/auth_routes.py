# web/routes/auth_routes.py — Giriş & Çıxış
from __future__ import annotations

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from modules.auth.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")
_svc = AuthService()

_MAX_ATTEMPTS = 5
_LOCK_MINUTES = 5


def _is_locked() -> bool:
    lock_until = session.get("login_lock_until")
    if not lock_until:
        return False
    try:
        return datetime.utcnow() < datetime.fromisoformat(lock_until)
    except ValueError:
        return False


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        if _is_locked():
            flash("❌ Çox cəhd edildi. 5 dəqiqə sonra yenidən yoxlayın.", "danger")
            return render_template("auth/login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        ok, user_or_msg = _svc.login(g.db, username, password)
        if ok:
            user = user_or_msg
            session["login_attempts"] = 0
            session.pop("login_lock_until", None)
            session["user"] = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value,
            }
            flash(f"Xoş gəldiniz, {user.full_name}!", "success")
            return redirect(url_for("dashboard.index"))

        attempts = int(session.get("login_attempts", 0)) + 1
        session["login_attempts"] = attempts
        if attempts >= _MAX_ATTEMPTS:
            session["login_lock_until"] = (datetime.utcnow() + timedelta(minutes=_LOCK_MINUTES)).isoformat()
            flash("❌ Çox səhv cəhd. Hesab qısa müddətlik kilidləndi.", "danger")
        else:
            flash("❌ İstifadəçi adı və ya şifrə yanlışdır.", "danger")

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Çıxış edildi.", "info")
    return redirect(url_for("auth.login"))
