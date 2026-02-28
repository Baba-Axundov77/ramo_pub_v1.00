from __future__ import annotations

from functools import wraps
from typing import Callable, Any
from flask import session, flash, redirect, url_for


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
