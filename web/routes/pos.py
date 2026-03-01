from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, url_for, session

from modules.orders.order_service import order_service
from modules.pos.pos_service import pos_service
from web.auth import permission_required

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")


@pos_bp.route("/")
@permission_required("process_payment")
def index():
    active_orders = order_service.get_active_orders(g.db)
    return render_template("pos/index.html", active_orders=active_orders)


@pos_bp.route("/pay", methods=["POST"])
@permission_required("process_payment")
def pay():
    order_id = int(request.form.get("order_id", "0") or 0)
    method = request.form.get("method", "cash")
    discount_code = request.form.get("discount_code", "").strip() or None
    points_used = int(request.form.get("loyalty_points_used", "0") or 0)

    ok, result = pos_service.process_payment(
        g.db,
        order_id=order_id,
        method=method,
        cashier_id=int(session.get("user", {}).get("id") or 0),
        discount_code=discount_code,
        loyalty_points_used=points_used,
    )
    if ok:
        flash(f"Ödəniş tamamlandı. Çek ID: #{result.id}", "success")
        return redirect(url_for("receipt.view_payment", payment_id=result.id))

    flash(str(result), "danger")
    return redirect(url_for("pos.index"))
