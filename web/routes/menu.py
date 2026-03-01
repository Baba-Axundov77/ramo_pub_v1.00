# web/routes/menu.py
from __future__ import annotations

from flask import Blueprint, render_template, session, redirect, url_for, g, request, flash

from modules.menu.menu_service import MenuService
from web.auth import permission_required

bp = Blueprint("menu", __name__, url_prefix="/menu")
svc = MenuService()


@bp.route("/")
@permission_required("manage_menu")
def index():
    category_id = request.args.get("category_id", type=int)
    categories = svc.get_categories(g.db)
    items = svc.get_items(g.db, category_id=category_id)
    return render_template("menu/index.html", categories=categories, items=items, selected_category=category_id)


@bp.route("/categories/create", methods=["POST"])
@permission_required("manage_menu")
def create_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Kateqoriya adı boş ola bilməz.", "danger")
        return redirect(url_for("menu.index"))

    ok, result = svc.create_category(
        g.db,
        name=name,
        description=request.form.get("description", "").strip() or None,
        icon=request.form.get("icon", "🍽️").strip() or "🍽️",
        sort_order=int(request.form.get("sort_order", 0) or 0),
    )
    flash("Kateqoriya yaradıldı." if ok else str(result), "success" if ok else "danger")
    return redirect(url_for("menu.index"))


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@permission_required("manage_menu")
def delete_category(cat_id: int):
    ok, msg = svc.delete_category(g.db, cat_id)
    flash(str(msg), "success" if ok else "danger")
    return redirect(url_for("menu.index"))


@bp.route("/items/create", methods=["POST"])
@permission_required("manage_menu")
def create_item():
    try:
        ok, result = svc.create_item(
            g.db,
            category_id=int(request.form.get("category_id", "0") or 0),
            name=request.form.get("name", "").strip(),
            price=float(request.form.get("price", "0") or 0),
            description=request.form.get("description", "").strip() or None,
            cost_price=float(request.form.get("cost_price", "0") or 0),
        )
        flash("Məhsul yaradıldı." if ok else str(result), "success" if ok else "danger")
    except Exception as exc:
        flash(f"Xəta: {exc}", "danger")
    return redirect(url_for("menu.index"))


@bp.route("/items/<int:item_id>/toggle", methods=["POST"])
@permission_required("manage_menu")
def toggle_item(item_id: int):
    ok, result = svc.toggle_available(g.db, item_id)
    flash("Status dəyişdirildi." if ok else str(result), "success" if ok else "danger")
    return redirect(url_for("menu.index"))


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@permission_required("manage_menu")
def delete_item(item_id: int):
    ok, msg = svc.delete_item(g.db, item_id)
    flash(str(msg), "success" if ok else "danger")
    return redirect(url_for("menu.index"))
