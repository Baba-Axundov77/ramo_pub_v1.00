# web/routes/reports.py
from __future__ import annotations
from datetime import date
from flask import Blueprint, render_template, session, redirect, url_for, g, jsonify, request
from src.core.modules.reports.report_service import ReportService
from src.core.modules.orders.order_service import OrderService
from src.core.modules.inventory.inventory_service import inventory_service
from src.web.auth import permission_required, permission_required_api

bp      = Blueprint("reports", __name__, url_prefix="/reports")
svc     = ReportService()
ord_svc = OrderService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
@permission_required("view_reports")
def index():
    c = _check()
    if c: return c
    today           = date.today()
    daily           = svc.daily_summary(g.db, today)
    top             = svc.top_items(g.db, limit=5)
    completed_sales = svc.completed_sales(g.db, today, limit=100)
    summary         = ord_svc.get_today_summary(g.db)
    purchase_receipts = inventory_service.list_purchase_receipts(g.db, limit=30)
    return render_template(
        "reports/index.html",
        daily=daily,
        top=top,
        today=today,
        completed_sales=completed_sales,
        summary=summary,
        purchase_receipts=purchase_receipts,
    )

@bp.route("/api/monthly")
@permission_required_api("view_reports")
def api_monthly():
    year  = int(request.args.get("year",  date.today().year))
    month = int(request.args.get("month", date.today().month))
    data  = svc.monthly_summary(g.db, year, month)
    return jsonify({
        "days":   data["days"],
        "values": data["values"],
        "total":  data["revenue"],
    })

@bp.route("/api/weekly")
@permission_required_api("view_reports")
def api_weekly():
    """Son 7 günün gəliri"""
    data = svc.weekly_summary(g.db, date.today())
    return jsonify(data)

@bp.route("/api/hourly")
@permission_required_api("view_reports")
def api_hourly():
    data = svc.hourly_heatmap(g.db, date.today())
    return jsonify(data)

@bp.route("/api/top_items")
@permission_required_api("view_reports")
def api_top_items():
    items = svc.top_items(g.db, limit=10)
    return jsonify(items)
