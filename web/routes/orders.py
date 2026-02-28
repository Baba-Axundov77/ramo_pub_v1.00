# web/routes/orders.py
from __future__ import annotations
from flask import Blueprint, render_template, session, redirect, url_for, g, request
from modules.orders.order_service import OrderService
from modules.tables.table_service import TableService

bp  = Blueprint("orders", __name__, url_prefix="/orders")
svc = OrderService()
table_svc = TableService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
def index():
    c = _check()
    if c:
        return c

    table_id = request.args.get("table_id", type=int)
    order_id = request.args.get("order_id", type=int)

    active = svc.get_active_orders(g.db)
    today = svc.get_today_orders(g.db)
    summary = svc.get_today_summary(g.db)

    selected_table = table_svc.get_by_id(g.db, table_id) if table_id else None
    if selected_table:
        active = [o for o in active if o.table_id == selected_table.id]

    selected_order = None
    if order_id:
        selected_order = next((o for o in today if o.id == order_id), None)

    return render_template(
        "orders/index.html",
        active=active,
        today=today,
        summary=summary,
        selected_table=selected_table,
        selected_order=selected_order,
    )
