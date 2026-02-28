# web/routes/reservations.py  —  Python 3.10
from __future__ import annotations

from datetime import date, time, datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify,
)
from database.connection import get_db
from web.app import login_required

reservations_bp = Blueprint("reservations", __name__, url_prefix="/reservations")


@reservations_bp.route("/")
@login_required
def index():
    from modules.reservation.reservation_service import reservation_service
    from modules.tables.table_service import TableService
    db   = get_db()
    mode = request.args.get("mode", "today")   # today | upcoming | all
    if mode == "today":
        items = reservation_service.get_today(db)
    elif mode == "upcoming":
        items = reservation_service.get_all(db, upcoming_only=True)
    else:
        items = reservation_service.get_all(db)

    tables = TableService().get_all(db)
    return render_template(
        "reservations/index.html",
        reservations=items,
        tables=tables,
        mode=mode,
        today_count=len(reservation_service.get_today(db)),
        upcoming_count=reservation_service.get_upcoming_count(db),
    )


@reservations_bp.route("/create", methods=["POST"])
@login_required
def create():
    from modules.reservation.reservation_service import reservation_service
    db = get_db()
    try:
        res_date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        res_time = time(*map(int, request.form["time"].split(":")))
        ok, result = reservation_service.create(
            db,
            table_id       = int(request.form["table_id"]),
            customer_name  = request.form["customer_name"].strip(),
            customer_phone = request.form.get("customer_phone", "").strip(),
            res_date       = res_date,
            res_time       = res_time,
            guest_count    = int(request.form.get("guest_count", 2)),
            notes          = request.form.get("notes", "").strip(),
        )
        if ok:
            flash("✅  Rezervasiya yaradıldı.", "success")
        else:
            flash(f"❌  {result}", "danger")
    except Exception as e:
        flash(f"❌  Xəta: {e}", "danger")
    return redirect(url_for("reservations.index"))


@reservations_bp.route("/<int:res_id>/cancel", methods=["POST"])
@login_required
def cancel(res_id: int):
    from modules.reservation.reservation_service import reservation_service
    db = get_db()
    ok, msg = reservation_service.cancel(db, res_id)
    flash(f"{'✅' if ok else '❌'}  {msg}", "success" if ok else "danger")
    return redirect(url_for("reservations.index"))


@reservations_bp.route("/api/available-tables")
@login_required
def api_available_tables():
    from modules.reservation.reservation_service import reservation_service
    db = get_db()
    try:
        res_date = datetime.strptime(request.args["date"], "%Y-%m-%d").date()
        res_time = time(*map(int, request.args["time"].split(":")))
        tables   = reservation_service.get_available_tables(db, res_date, res_time)
        return jsonify([{
            "id": t.id,
            "number": t.number,
            "name": t.name or f"Masa {t.number}",
            "capacity": t.capacity,
        } for t in tables])
    except Exception as e:
        return jsonify({"error": str(e)}), 400
