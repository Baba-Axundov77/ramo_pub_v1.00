from __future__ import annotations

from datetime import datetime
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, session

from database.models import Payment
from modules.orders.order_service import order_service
from modules.pos.pos_service import pos_service
from web.auth import permission_required

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")


@pos_bp.route("/")
@permission_required("process_payment")
def index():
    active_orders = order_service.get_active_orders(g.db)
    
    # Get daily statistics
    daily_summary = pos_service.get_daily_summary(g.db)
    total_revenue = daily_summary["total"]
    paid_today = daily_summary["count"]
    
    # Payment method statistics - use daily summary data
    cash_amount = daily_summary["by_method"].get("cash", 0)
    card_amount = daily_summary["by_method"].get("card", 0)
    online_amount = daily_summary["by_method"].get("online", 0)
    
    # Count payments by method from the same query
    start = daily_summary["start"]
    end = daily_summary["end"]
    
    cash_payments = g.db.query(Payment).filter(
        Payment.created_at >= start,
        Payment.created_at <= end,
        Payment.method == "cash"
    ).count()
    
    card_payments = g.db.query(Payment).filter(
        Payment.created_at >= start,
        Payment.created_at <= end,
        Payment.method == "card"
    ).count()
    
    online_payments = g.db.query(Payment).filter(
        Payment.created_at >= start,
        Payment.created_at <= end,
        Payment.method == "online"
    ).count()
    
    return render_template("pos/index.html", 
                         active_orders=active_orders,
                         total_revenue=total_revenue,
                         paid_today=paid_today,
                         current_user=session.get("user", {}),
                         cash_payments=cash_payments,
                         cash_amount=cash_amount,
                         card_payments=card_payments,
                         card_amount=card_amount,
                         online_payments=online_payments,
                         online_amount=online_amount)


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
