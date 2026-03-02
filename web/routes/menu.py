from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, g, request, flash

from modules.menu.menu_service import MenuService
from modules.inventory.inventory_service import inventory_service
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
    inventory_items = inventory_service.get_all(g.db)
    return render_template(
        "menu/index.html",
        categories=categories,
        items=items,
        inventory_items=inventory_items,
        selected_category=category_id,
    )
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


@bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@permission_required("manage_menu")
def edit_category(cat_id: int):
    ok, result = svc.update_category(
        g.db,
        cat_id,
        name=request.form.get("name", "").strip(),
        description=request.form.get("description", "").strip() or None,
        icon=request.form.get("icon", "🍽️").strip() or "🍽️",
        sort_order=int(request.form.get("sort_order", 0) or 0),
    )
    flash("Kateqoriya yeniləndi." if ok else str(result), "success" if ok else "danger")
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
            image_path=request.form.get("image_path", "").strip() or None,
            inventory_item_id=(int(request.form.get("inventory_item_id")) if request.form.get("inventory_item_id") else None),
            stock_name=request.form.get("stock_name", "").strip() or None,
            stock_unit=request.form.get("stock_unit", "").strip() or None,
        )
        flash("Məhsul yaradıldı." if ok else str(result), "success" if ok else "danger")
    except Exception as exc:
        flash(f"Xəta: {exc}", "danger")
    return redirect(url_for("menu.index"))


@bp.route("/items/<int:item_id>/edit", methods=["POST"])
@permission_required("manage_menu")
def edit_item(item_id: int):
    ok, result = svc.update_item(
        g.db,
        item_id,
        category_id=int(request.form.get("category_id", "0") or 0),
        name=request.form.get("name", "").strip(),
        price=float(request.form.get("price", "0") or 0),
        description=request.form.get("description", "").strip() or None,
        cost_price=float(request.form.get("cost_price", "0") or 0),
        image_path=request.form.get("image_path", "").strip() or None,
        inventory_item_id=(int(request.form.get("inventory_item_id")) if request.form.get("inventory_item_id") else None),
        stock_name=request.form.get("stock_name", "").strip() or None,
        stock_unit=request.form.get("stock_unit", "").strip() or None,
        is_available=(request.form.get("is_available") == "1"),
    )
    flash("Məhsul yeniləndi." if ok else str(result), "success" if ok else "danger")
    return redirect(url_for("menu.index", category_id=request.args.get("category_id", type=int)))


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
