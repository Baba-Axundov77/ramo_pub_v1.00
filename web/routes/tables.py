# web/routes/tables.py
from __future__ import annotations

from flask import Blueprint, render_template, g, jsonify, request
from modules.tables.table_service import TableService
from web.auth_utils import login_required

bp = Blueprint("tables", __name__, url_prefix="/tables")
svc = TableService()


@bp.route("/")
@login_required
def index():
    tables = svc.get_all(g.db)
    stats = svc.get_stats(g.db)
    return render_template("tables/index.html", tables=tables, stats=stats)


@bp.route("/api/all")
@login_required
def api_all():
    tables = svc.get_all(g.db)
    return jsonify([
        {
            "id": t.id,
            "number": t.number,
            "name": t.name or "",
            "status": t.status.value,
            "floor": t.floor,
            "capacity": t.capacity,
        }
        for t in tables
    ])


@bp.route("/api/status/<int:table_id>", methods=["POST"])
@login_required
def set_status(table_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "available")
    ok, result = svc.set_status(g.db, table_id, status)
    return jsonify({"ok": ok, "msg": str(result)})
