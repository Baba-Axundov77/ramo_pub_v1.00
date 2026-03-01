from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import flash, redirect, session, url_for

from modules.auth.permissions import permission_service


def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if "user" not in session:
            flash("Zəhmət olmasa, əvvəlcə giriş edin.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles: str) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any):
            if "user" not in session:
                return redirect(url_for("auth.login"))
            role = session["user"].get("role")
            if role not in roles:
                flash("Bu səhifəyə giriş icazəniz yoxdur.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


def permission_required(permission: str) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any):
            if "user" not in session:
                return redirect(url_for("auth.login"))
            role = session["user"].get("role")
            if not permission_service.has_permission(role, permission):
                flash("Bu əməliyyat üçün icazəniz yoxdur.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


def admin_required(f: Callable) -> Callable:
    return role_required("admin")(f)
