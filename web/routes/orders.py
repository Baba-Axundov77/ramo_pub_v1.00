# web/routes/orders.py
from __future__ import annotations
from flask import Blueprint, render_template, session, redirect, url_for, g
from modules.orders.order_service import OrderService

bp  = Blueprint("orders", __name__, url_prefix="/orders")
svc = OrderService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
def index():
    c = _check()
    if c: return c
    active  = svc.get_active_orders(g.db)
    today   = svc.get_today_orders(g.db)
    summary = svc.get_today_summary(g.db)
    return render_template("orders/index.html",
                           active=active, today=today, summary=summary)
