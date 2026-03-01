from __future__ import annotations

from datetime import date

from flask import Blueprint, g, redirect, render_template, request, session, url_for, flash

from modules.staff.staff_service import staff_service
from web.auth import permission_required

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/")
@permission_required("manage_users")
def index():
    users = staff_service.get_all_staff(g.db, active_only=False)
    shifts = staff_service.get_today_shifts(g.db)
    return render_template("staff/index.html", users=users, shifts=shifts)


@staff_bp.route("/create", methods=["POST"])
@permission_required("manage_users")
def create():
    ok, result = staff_service.create_staff(
        g.db,
        username=request.form.get("username", "").strip(),
        full_name=request.form.get("full_name", "").strip(),
        password=request.form.get("password", "").strip(),
        role=request.form.get("role", "waiter").strip(),
        phone=request.form.get("phone", "").strip(),
    )
    flash("İşçi yaradıldı." if ok else str(result), "success" if ok else "danger")
    return redirect(url_for("staff.index"))


@staff_bp.route("/<int:user_id>/deactivate", methods=["POST"])
@permission_required("manage_users")
def deactivate(user_id: int):
    ok, msg = staff_service.deactivate(g.db, user_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.index"))


@staff_bp.route("/shift/create", methods=["POST"])
@permission_required("manage_users")
def create_shift():
    user_id = int(request.form.get("user_id", "0") or 0)
    shift_date = request.form.get("date", "")
    try:
        parsed_date = date.fromisoformat(shift_date)
    except ValueError:
        parsed_date = date.today()
    ok, result = staff_service.add_shift(
        g.db,
        user_id=user_id,
        shift_date=parsed_date,
        start=request.form.get("start", "09:00"),
        end=request.form.get("end", "21:00"),
        notes=request.form.get("notes", ""),
    )
    flash("Növbə əlavə edildi." if ok else str(result), "success" if ok else "danger")
    return redirect(url_for("staff.index"))
