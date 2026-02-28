# web/routes/inventory.py  —  Python 3.10
from __future__ import annotations

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify,
)
from database.connection import get_db
from web.auth import login_required, admin_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
@login_required
def index():
    from modules.inventory.inventory_service import inventory_service
    db       = get_db()
    low_only = request.args.get("low", "") == "1"
    search   = request.args.get("q", "").strip().lower()
    items    = inventory_service.get_all(db, low_stock_only=low_only)
    if search:
        items = [i for i in items if search in i.name.lower()]
    return render_template(
        "inventory/index.html",
        items       = items,
        low_only    = low_only,
        search      = search,
        low_count   = inventory_service.get_low_stock_count(db),
        total_value = inventory_service.get_total_value(db),
    )


@inventory_bp.route("/create", methods=["POST"])
@admin_required
def create():
    from modules.inventory.inventory_service import inventory_service
    db = get_db()
    ok, result = inventory_service.create(
        db,
        name          = request.form["name"].strip(),
        unit          = request.form["unit"].strip(),
        quantity      = float(request.form.get("quantity", 0)),
        min_quantity  = float(request.form.get("min_quantity", 5)),
        cost_per_unit = float(request.form.get("cost_per_unit", 0)),
        supplier      = request.form.get("supplier", "").strip(),
    )
    flash(f"{'✅  Stok əlavə edildi.' if ok else '❌  ' + str(result)}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/<int:item_id>/adjust", methods=["POST"])
@login_required
def adjust(item_id: int):
    from modules.inventory.inventory_service import inventory_service
    db     = get_db()
    mode   = request.form.get("mode", "add")
    amount = float(request.form.get("amount", 0))
    if mode == "add":
        ok, result = inventory_service.add_stock(db, item_id, amount)
    else:
        ok, result = inventory_service.remove_stock(db, item_id, amount)
    flash(f"{'✅  Stok yeniləndi.' if ok else '❌  ' + str(result)}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete(item_id: int):
    from modules.inventory.inventory_service import inventory_service
    ok, msg = inventory_service.delete(get_db(), item_id)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/api/low-stock")
@login_required
def api_low_stock():
    from modules.inventory.inventory_service import inventory_service
    db    = get_db()
    items = inventory_service.get_all(db, low_stock_only=True)
    return jsonify([{
        "id": i.id, "name": i.name,
        "quantity": i.quantity, "min_quantity": i.min_quantity,
        "unit": i.unit,
    } for i in items])
