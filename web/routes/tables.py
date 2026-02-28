# web/routes/tables.py
from __future__ import annotations
from flask import Blueprint, render_template, session, redirect, url_for, g, jsonify, request
from modules.tables.table_service import TableService

bp   = Blueprint("tables", __name__, url_prefix="/tables")
svc  = TableService()

def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))

@bp.route("/")
def index():
    c = _check()
    if c: return c
    tables = svc.get_all(g.db)
    stats  = svc.get_stats(g.db)
    return render_template("tables/index.html", tables=tables, stats=stats)

@bp.route("/api/all")
def api_all():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    tables = svc.get_all(g.db)
    return jsonify([{
        "id":     t.id,
        "number": t.number,
        "name":   t.name or "",
        "status": t.status.value,
        "floor":  t.floor,
        "capacity": t.capacity,
    } for t in tables])

@bp.route("/api/status/<int:table_id>", methods=["POST"])
def set_status(table_id: int):
    if "user" not in session:
        return jsonify({"error": "Giriş tələb olunur"}), 401
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "available")).strip().lower()

    allowed = {"available", "occupied", "reserved", "cleaning"}
    if status not in allowed:
        return jsonify({"ok": False, "msg": "Yanlış status göndərildi."}), 400

    ok, result = svc.set_status(g.db, table_id, status)
    return jsonify({"ok": ok, "msg": str(result)})


@bp.route("/api/active-order/<int:table_id>")
def active_order(table_id: int):
    if "user" not in session:
        return jsonify({"error": "Giriş tələb olunur"}), 401

    table = svc.get_by_id(g.db, table_id)
    if not table:
        return jsonify({"ok": False, "msg": "Masa tapılmadı."}), 404

    order = svc.get_active_order(g.db, table_id)
    if not order:
        return jsonify({"ok": True, "order": None})

    return jsonify({
        "ok": True,
        "order": {
            "id": order.id,
            "status": order.status.value,
            "total": float(order.total or 0),
        }
    })
