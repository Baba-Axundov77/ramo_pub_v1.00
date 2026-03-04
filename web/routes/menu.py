# web/routes/menu.py
from __future__ import annotations

import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, g, request, flash, current_app
from modules.menu.menu_service import MenuService
from modules.inventory.inventory_service import inventory_service
from web.auth import permission_required

bp = Blueprint("menu", __name__, url_prefix="/menu")
svc = MenuService()

UPLOAD_FOLDER = os.path.join("assets", "menu_images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_uploaded_image(file) -> str | None:
    """Yüklənmiş şəkli saxla, yolunu qaytar"""
    if not file or not file.filename:
        return None
    if not _allowed_file(file.filename):
        return None
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return f"menu/{filename}"


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
        # Şəkil yüklə
        image_path = request.form.get("image_path", "").strip() or None
        if "image_file" in request.files:
            uploaded = _save_uploaded_image(request.files["image_file"])
            if uploaded:
                image_path = uploaded

        ok, result = svc.create_item(
            g.db,
            category_id=int(request.form.get("category_id", "0") or 0),
            name=request.form.get("name", "").strip(),
            price=float(request.form.get("price", "0") or 0),
            description=request.form.get("description", "").strip() or None,
            cost_price=float(request.form.get("cost_price", "0") or 0),
            image_path=image_path,
            inventory_item_id=(int(request.form.get("inventory_item_id")) if request.form.get("inventory_item_id") else None),
            stock_name=request.form.get("stock_name", "").strip() or None,
            stock_unit=request.form.get("stock_unit", "").strip() or None,
            stock_usage_qty=float(request.form.get("stock_usage_qty", "0") or 0),
            sort_order=int(request.form.get("sort_order", 0) or 0),
        )
        flash("Məhsul yaradıldı." if ok else str(result), "success" if ok else "danger")
    except Exception as exc:
        flash(f"Xəta: {exc}", "danger")
    return redirect(url_for("menu.index"))


@bp.route("/items/<int:item_id>/edit", methods=["POST"])
@permission_required("manage_menu")
def edit_item(item_id: int):
    # Şəkil yüklə (yeni fayl varsa)
    image_path = request.form.get("image_path", "").strip() or None
    if "image_file" in request.files:
        uploaded = _save_uploaded_image(request.files["image_file"])
        if uploaded:
            image_path = uploaded

    ok, result = svc.update_item(
        g.db,
        item_id,
        category_id=int(request.form.get("category_id", "0") or 0),
        name=request.form.get("name", "").strip(),
        price=float(request.form.get("price", "0") or 0),
        description=request.form.get("description", "").strip() or None,
        cost_price=float(request.form.get("cost_price", "0") or 0),
        image_path=image_path,
        inventory_item_id=(int(request.form.get("inventory_item_id")) if request.form.get("inventory_item_id") else None),
        stock_name=request.form.get("stock_name", "").strip() or None,
        stock_unit=request.form.get("stock_unit", "").strip() or None,
        stock_usage_qty=float(request.form.get("stock_usage_qty", "0") or 0),
        is_available=(request.form.get("is_available") == "1"),
        sort_order=int(request.form.get("sort_order", 0) or 0),
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
