# web/routes/loyalty.py  —  Python 3.10
from __future__ import annotations

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify,
)
from database.connection import get_db
from web.auth_utils import login_required, admin_required

loyalty_bp = Blueprint("loyalty", __name__, url_prefix="/loyalty")


@loyalty_bp.route("/")
@login_required
def index():
    from modules.loyalty.loyalty_service import loyalty_service
    db      = get_db()
    search  = request.args.get("q", "")
    customers = loyalty_service.get_all_customers(db, search)
    summary   = loyalty_service.get_summary(db)
    discounts = loyalty_service.get_all_discounts(db)
    return render_template(
        "loyalty/index.html",
        customers  = customers,
        summary    = summary,
        discounts  = discounts,
        search     = search,
    )


@loyalty_bp.route("/customers/create", methods=["POST"])
@login_required
def create_customer():
    from modules.loyalty.loyalty_service import loyalty_service
    from datetime import date
    db   = get_db()
    bday = None
    bd   = request.form.get("birthday", "").strip()
    if bd:
        try:
            from datetime import datetime
            bday = datetime.strptime(bd, "%Y-%m-%d").date()
        except ValueError:
            pass
    ok, result = loyalty_service.create_customer(
        db,
        full_name = request.form["full_name"].strip(),
        phone     = request.form["phone"].strip(),
        email     = request.form.get("email", "").strip(),
        birthday  = bday,
    )
    if ok:
        flash(f"✅  {result.full_name} əlavə edildi. 🎉 20 xoş gəldiniz xalı verildi!", "success")
    else:
        flash(f"❌  {result}", "danger")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/customers/<int:customer_id>/delete", methods=["POST"])
@admin_required
def delete_customer(customer_id: int):
    from modules.loyalty.loyalty_service import loyalty_service
    db = get_db()
    ok, msg = loyalty_service.delete_customer(db, customer_id)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/customers/<int:customer_id>/points", methods=["POST"])
@login_required
def adjust_points(customer_id: int):
    from modules.loyalty.loyalty_service import loyalty_service
    db     = get_db()
    mode   = request.form.get("mode", "add")
    try:
        points = int(request.form.get("points", 0))
    except ValueError:
        flash("❌ Xal dəyəri rəqəm olmalıdır.", "danger")
        return redirect(url_for("loyalty.index"))
    reason = request.form.get("reason", "Manuel əməliyyat")
    pts    = points if mode == "add" else -points
    ok, msg = loyalty_service.adjust_points(db, customer_id, pts, reason)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/discounts/create", methods=["POST"])
@admin_required
def create_discount():
    from modules.loyalty.loyalty_service import loyalty_service
    db = get_db()
    try:
        value = float(request.form["value"])
        min_order = float(request.form.get("min_order", 0))
        usage_limit = int(request.form.get("usage_limit", 0))
    except ValueError:
        flash("❌ Endirim parametrlərində rəqəm formatı yanlışdır.", "danger")
        return redirect(url_for("loyalty.index"))

    ok, result = loyalty_service.create_discount(
        db,
        code=request.form["code"].strip().upper(),
        description=request.form.get("description", "").strip(),
        dtype=request.form.get("type", "percent"),
        value=value,
        min_order=min_order,
        usage_limit=usage_limit,
    )
    flash(f"{'✅  Kod yaradıldı.' if ok else '❌  ' + str(result)}", "success" if ok else "danger")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/discounts/<int:discount_id>/toggle", methods=["POST"])
@admin_required
def toggle_discount(discount_id: int):
    from modules.loyalty.loyalty_service import loyalty_service
    loyalty_service.toggle_discount(get_db(), discount_id)
    flash("✅  Status dəyişdirildi.", "success")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/discounts/<int:discount_id>/delete", methods=["POST"])
@admin_required
def delete_discount(discount_id: int):
    from modules.loyalty.loyalty_service import loyalty_service
    ok, msg = loyalty_service.delete_discount(get_db(), discount_id)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("loyalty.index"))


@loyalty_bp.route("/api/lookup")
@login_required
def api_lookup():
    """Telefon ilə müştəri axtar — POS inteqrasiyası üçün."""
    from modules.loyalty.loyalty_service import loyalty_service
    phone = request.args.get("phone", "").strip()
    if not phone:
        return jsonify({"found": False})
    db = get_db()
    c  = loyalty_service.get_by_phone(db, phone)
    if not c:
        return jsonify({"found": False})
    stats = loyalty_service.get_customer_stats(db, c.id)
    return jsonify({
        "found":       True,
        "id":          c.id,
        "full_name":   c.full_name,
        "phone":       c.phone,
        "points":      c.points,
        "tier":        stats["tier"]["name"],
        "manat_value": c.points / 100,
    })
