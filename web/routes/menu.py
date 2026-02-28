# web/routes/menu.py
from __future__ import annotations

from flask import Blueprint, render_template, g, request, redirect, url_for, flash
from modules.menu.menu_service import MenuService
from web.auth_utils import login_required, admin_required

bp = Blueprint("menu", __name__, url_prefix="/menu")
svc = MenuService()


@bp.route("/")
@login_required
def index():
    categories = svc.get_categories(g.db)
    items = svc.get_items(g.db)
    return render_template("menu/index.html", categories=categories, items=items)


@bp.route("/categories/create", methods=["POST"])
@admin_required
def create_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("❌ Kateqoriya adı boş ola bilməz.", "danger")
        return redirect(url_for("menu.index"))

    icon = request.form.get("icon", "🍽️").strip() or "🍽️"
    description = request.form.get("description", "").strip() or None
    try:
        sort_order = int(request.form.get("sort_order", "0") or 0)
    except ValueError:
        sort_order = 0

    ok, result = svc.create_category(g.db, name=name, description=description, icon=icon, sort_order=sort_order)
    flash("✅ Kateqoriya əlavə edildi." if ok else f"❌ {result}", "success" if ok else "danger")
    return redirect(url_for("menu.index"))


@bp.route("/categories/<int:cat_id>/update", methods=["POST"])
@admin_required
def update_category(cat_id: int):
    name = request.form.get("name", "").strip()
    if not name:
        flash("❌ Kateqoriya adı boş ola bilməz.", "danger")
        return redirect(url_for("menu.index"))

    icon = request.form.get("icon", "🍽️").strip() or "🍽️"
    description = request.form.get("description", "").strip() or None
    try:
        sort_order = int(request.form.get("sort_order", "0") or 0)
    except ValueError:
        sort_order = 0

    ok, result = svc.update_category(
        g.db,
        cat_id,
        name=name,
        icon=icon,
        description=description,
        sort_order=sort_order,
    )
    flash("✅ Kateqoriya yeniləndi." if ok else f"❌ {result}", "success" if ok else "danger")
    return redirect(url_for("menu.index"))


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def delete_category(cat_id: int):
    ok, result = svc.delete_category(g.db, cat_id)
    flash("✅ Kateqoriya silindi." if ok else f"❌ {result}", "success" if ok else "danger")
    return redirect(url_for("menu.index"))
