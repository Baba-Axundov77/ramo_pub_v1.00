# web/routes/reports.py
from __future__ import annotations
from datetime import date
from flask import Blueprint, render_template, session, redirect, url_for, g, jsonify, request
from modules.reports.report_service import ReportService
from modules.orders.order_service import OrderService

bp      = Blueprint("reports", __name__, url_prefix="/reports")
svc     = ReportService()
ord_svc = OrderService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
def index():
    c = _check()
    if c: return c
    today           = date.today()
    daily           = svc.daily_summary(g.db, today)
    top             = svc.top_items(g.db, limit=5)
    completed_sales = svc.completed_sales(g.db, today, limit=100)
    # Sifarişlər bölməsindən köçürülmüş statistika
    summary         = ord_svc.get_today_summary(g.db)
    return render_template(
        "reports/index.html",
        daily=daily,
        top=top,
        today=today,
        completed_sales=completed_sales,
        summary=summary,
    )

@bp.route("/api/monthly")
def api_monthly():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    year  = int(request.args.get("year",  date.today().year))
    month = int(request.args.get("month", date.today().month))
    data  = svc.monthly_summary(g.db, year, month)
    return jsonify({
        "days":   data["days"],
        "values": data["values"],
        "total":  data["revenue"],
    })

@bp.route("/api/hourly")
def api_hourly():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    data = svc.hourly_heatmap(g.db, date.today())
    return jsonify(data)

@bp.route("/api/top_items")
def api_top_items():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    items = svc.top_items(g.db, limit=10)
    return jsonify(items)
