# web/routes/auth_routes.py — Giriş & Çıxış (JWT + Session Hybrid)
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, jsonify
from modules.auth.auth_service import AuthService
from modules.auth.token_manager import token_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/auth")
_svc = AuthService()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        # Check if this is an API login (JSON) or web login (form)
        if request.is_json:
            return _api_login()
        else:
            return _web_login()

    return render_template("auth/login.html")


def _web_login():
    """Web-based login with session"""
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


def _api_login():
    """API-based login with JWT token"""
    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "message": "JSON data required"
        }), 400
    
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password required"
        }), 400
    
    ok, user_or_msg = _svc.login(g.db, username, password)
    if ok:
        user = user_or_msg
        
        # Generate JWT token
        user_data = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value
        }
        
        access_token = token_manager.generate_token(user_data)
        refresh_token = token_manager.generate_refresh_token(user_data)
        
        logger.info(f"API login successful for user: {username}")
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 86400,  # 24 hours in seconds
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role.value
                }
            }
        })
    else:
        logger.warning(f"API login failed for user: {username}")
        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401


@bp.route("/logout")
def logout():
    session.clear()
    flash("Çıxış edildi.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/api/logout", methods=["POST"])
def api_logout():
    """API logout endpoint"""
    # For JWT, logout is typically client-side (token deletion)
    # But we can provide a blacklist endpoint if needed
    return jsonify({
        "success": True,
        "message": "Logout successful. Please delete the token from client storage."
    })


@bp.route("/api/refresh", methods=["POST"])
def refresh_token():
    """Refresh access token using refresh token"""
    data = request.get_json()
    if not data or not data.get("refresh_token"):
        return jsonify({
            "success": False,
            "message": "Refresh token required"
        }), 400
    
    refresh_token = data.get("refresh_token")
    new_access_token = token_manager.refresh_access_token(refresh_token)
    
    if new_access_token:
        return jsonify({
            "success": True,
            "message": "Token refreshed successfully",
            "data": {
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": 86400
            }
        })
    else:
        return jsonify({
            "success": False,
            "message": "Invalid or expired refresh token"
        }), 401
