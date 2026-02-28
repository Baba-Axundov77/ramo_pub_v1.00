# web/routes/menu.py
from __future__ import annotations
from flask import Blueprint, render_template, session, redirect, url_for, g
from modules.menu.menu_service import MenuService

bp  = Blueprint("menu", __name__, url_prefix="/menu")
svc = MenuService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
def index():
    c = _check()
    if c: return c
    categories = svc.get_categories(g.db)
    items      = svc.get_items(g.db)
    return render_template("menu/index.html", categories=categories, items=items)
