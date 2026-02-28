# web/routes/dashboard.py
from __future__ import annotations

from flask import Blueprint, render_template, session, redirect, url_for, g
from modules.tables.table_service    import TableService
from modules.orders.order_service    import OrderService
from modules.reports.report_service  import ReportService
from datetime import date

bp  = Blueprint("dashboard", __name__, url_prefix="/dashboard")
t_svc = TableService()
o_svc = OrderService()
r_svc = ReportService()


def _check_login():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return None


@bp.route("/")
def index():
    redir = _check_login()
    if redir:
        return redir

    table_stats   = t_svc.get_stats(g.db)
    order_summary = o_svc.get_today_summary(g.db)
    daily         = r_svc.daily_summary(g.db, date.today())

    return render_template(
        "dashboard/index.html",
        table_stats=table_stats,
        order_summary=order_summary,
        daily=daily,
    )
