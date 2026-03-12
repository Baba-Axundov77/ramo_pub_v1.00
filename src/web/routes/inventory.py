# web/routes/inventory.py
from __future__ import annotations

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, g
from src.web.auth import login_required, permission_required
from src.core.modules.inventory.inventory_service import inventory_service
from src.core.database.connection import get_db

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
@login_required
def index():
    db = g.db
    low_only = request.args.get("low", "") == "1"
    search = request.args.get("q", "").strip().lower()
    items = inventory_service.get_all(db, low_stock_only=low_only)
    if search:
        items = [i for i in items if search in i.name.lower()]
    receipts = inventory_service.list_purchase_receipts(db, limit=30)
    return render_template("inventory/index.html", items=items, low_only=low_only, search=search,
                           low_count=inventory_service.get_low_stock_count(db),
                           total_value=inventory_service.get_total_value(db),
                           receipts=receipts)


@inventory_bp.route("/create", methods=["POST"])
@permission_required("manage_inventory")
def create():
    db = g.db
    ok, result = inventory_service.create(
        db,
        name=request.form["name"].strip(),
        unit=request.form["unit"].strip(),
        quantity=float(request.form.get("quantity", 0)),
        min_quantity=float(request.form.get("min_quantity", 5)),
        cost_per_unit=float(request.form.get("cost_per_unit", 0)),
        supplier=request.form.get("supplier", "").strip(),
    )
    flash(f"{'✅  Stok əlavə edildi.' if ok else '❌  ' + str(result)}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/receipt/create", methods=["POST"])
@permission_required("manage_inventory")
def create_receipt():
    db = g.db
    names = request.form.getlist("line_name[]")
    qtys = request.form.getlist("line_qty[]")
    units = request.form.getlist("line_unit[]")
    costs = request.form.getlist("line_cost[]")
    lines = []
    for idx, name in enumerate(names):
        if not name.strip():
            continue
        lines.append({
            "name": name,
            "quantity": qtys[idx] if idx < len(qtys) else 0,
            "unit": units[idx] if idx < len(units) else "ədəd",
            "unit_cost": costs[idx] if idx < len(costs) else 0
        })
    purchased_at = datetime.fromisoformat(request.form.get("purchased_at")) if request.form.get("purchased_at") else datetime.now()
    ok, result = inventory_service.create_purchase_receipt(
        db,
        purchased_at=purchased_at,
        store_name=request.form.get("store_name", "").strip(),
        note=request.form.get("note", "").strip(),
        created_by=session.get("user", {}).get("id"),
        lines=lines,
    )
    flash("✅ Alış çeki yaradıldı və stok yeniləndi." if ok else f"❌ {result}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/receipt/<int:receipt_id>/edit", methods=["POST"])
@permission_required("manage_inventory")
def edit_receipt(receipt_id: int):
    """Mövcud çeki sil, sonra yeni data ilə yenidən yarat (stock rollback + reapply)"""
    db = g.db
    # Köhnəni sil (stoku geri al)
    ok, msg = inventory_service.delete_purchase_receipt(db, receipt_id)
    if not ok:
        flash(f"❌ {msg}", "danger")
        return redirect(url_for("inventory.index"))

    # Yeni data ilə yenidən yarat
    names = request.form.getlist("line_name[]")
    qtys  = request.form.getlist("line_qty[]")
    units = request.form.getlist("line_unit[]")
    costs = request.form.getlist("line_cost[]")
    lines = []
    for idx, name in enumerate(names):
        if not name.strip():
            continue
        lines.append({
            "name": name,
            "quantity": qtys[idx] if idx < len(qtys) else 0,
            "unit": units[idx] if idx < len(units) else "ədəd",
            "unit_cost": costs[idx] if idx < len(costs) else 0
        })
    purchased_at = datetime.fromisoformat(request.form.get("purchased_at")) if request.form.get("purchased_at") else datetime.now()
    ok2, result2 = inventory_service.create_purchase_receipt(
        db,
        purchased_at=purchased_at,
        store_name=request.form.get("store_name", "").strip(),
        note=request.form.get("note", "").strip(),
        created_by=session.get("user", {}).get("id"),
        lines=lines,
    )
    flash("✅ Çek yeniləndi." if ok2 else f"❌ {result2}", "success" if ok2 else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/receipt/<int:receipt_id>/delete", methods=["POST"])
@permission_required("manage_inventory")
def delete_receipt(receipt_id: int):
    ok, msg = inventory_service.delete_purchase_receipt(g.db, receipt_id)
    flash(("✅ " if ok else "❌ ") + msg, "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/<int:item_id>/adjust", methods=["POST"])
@permission_required("manage_inventory")
def adjust(item_id: int):
    db = g.db
    mode = request.form.get("mode", "add")
    amount = float(request.form.get("amount", 0))
    reason = request.form.get("reason", "").strip()
    actor = session.get("user", {}).get("id")
    if mode == "add":
        ok, result = inventory_service.add_stock(db, item_id, amount, reason=reason or "Manual artırma", created_by=actor)
    elif mode == "waste":
        ok, result = inventory_service.remove_stock(db, item_id, amount, reason=reason or "İtki/Spoilage", created_by=actor, allow_negative=ALLOW_NEGATIVE_STOCK)
    else:
        ok, result = inventory_service.remove_stock(db, item_id, amount, reason=reason or "Manual azaltma", created_by=actor, allow_negative=ALLOW_NEGATIVE_STOCK)
    flash(f"{'✅  Stok yeniləndi.' if ok else '❌  ' + str(result)}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/<int:item_id>/delete", methods=["POST"])
@permission_required("manage_inventory")
def delete(item_id: int):
    ok, msg = inventory_service.delete(g.db, item_id)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/api/low-stock")
@login_required
def api_low_stock():
    items = inventory_service.get_all(g.db, low_stock_only=True)
    return jsonify([{"id": i.id, "name": i.name, "quantity": i.quantity, "min_quantity": i.min_quantity, "unit": i.unit} for i in items])
