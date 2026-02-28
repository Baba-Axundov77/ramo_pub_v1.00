# web/routes/reports.py
from __future__ import annotations

from datetime import date
from flask import Blueprint, render_template, g, jsonify, request
from modules.reports.report_service import ReportService
from web.auth_utils import login_required

bp = Blueprint("reports", __name__, url_prefix="/reports")
svc = ReportService()


@bp.route("/")
@login_required
def index():
    today = date.today()
    daily = svc.daily_summary(g.db, today)
    top = svc.top_items(g.db, limit=5)
    return render_template("reports/index.html", daily=daily, top=top, today=today)


@bp.route("/api/monthly")
@login_required
def api_monthly():
    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    data = svc.monthly_summary(g.db, year, month)
    return jsonify({"days": data["days"], "values": data["values"], "total": data["revenue"]})


@bp.route("/api/hourly")
@login_required
def api_hourly():
    data = svc.hourly_heatmap(g.db, date.today())
    return jsonify(data)


@bp.route("/api/top_items")
@login_required
def api_top_items():
    items = svc.top_items(g.db, limit=10)
    return jsonify(items)
