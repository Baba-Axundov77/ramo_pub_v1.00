# web/routes/orders.py
from __future__ import annotations

from flask import Blueprint, render_template, g
from modules.orders.order_service import OrderService
from web.auth_utils import login_required

bp = Blueprint("orders", __name__, url_prefix="/orders")
svc = OrderService()


@bp.route("/")
@login_required
def index():
    active = svc.get_active_orders(g.db)
    today = svc.get_today_orders(g.db)
    summary = svc.get_today_summary(g.db)
    return render_template("orders/index.html", active=active, today=today, summary=summary)
