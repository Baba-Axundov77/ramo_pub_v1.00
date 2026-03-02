from __future__ import annotations

from flask import Blueprint, g, jsonify, render_template

from modules.orders.kitchen_service import kitchen_service
from web.auth import permission_required, permission_required_api

kitchen_bp = Blueprint("kitchen", __name__, url_prefix="/kitchen")


@kitchen_bp.route("/")
@permission_required("manage_kitchen")
def index():
    queue = kitchen_service.get_queue(g.db)
    return render_template("kitchen/index.html", queue=queue)


@kitchen_bp.route("/api/queue")
@permission_required_api("manage_kitchen")
def api_queue():
    queue = kitchen_service.get_queue(g.db)
    payload = []
    for order in queue:
        payload.append(
            {
                "id": order.id,
                "table": order.table.name if order.table and order.table.name else (f"Masa {order.table.number}" if order.table else "-"),
                "status": order.status.value,
                "created_at": order.created_at.strftime("%H:%M") if order.created_at else "",
                "items": [
                    {
                        "id": item.id,
                        "name": item.menu_item.name if item.menu_item else "?",
                        "qty": item.quantity,
                        "status": item.status.value,
                    }
                    for item in order.items
                ],
            }
        )
    return jsonify({"ok": True, "queue": payload})


@kitchen_bp.route("/api/<int:order_id>/preparing", methods=["POST"])
@permission_required_api("manage_kitchen")
def api_preparing(order_id: int):
    ok, result = kitchen_service.mark_preparing(g.db, order_id)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "status": result.status.value})


@kitchen_bp.route("/api/<int:order_id>/ready", methods=["POST"])
@permission_required_api("manage_kitchen")
def api_ready(order_id: int):
    ok, result = kitchen_service.mark_ready(g.db, order_id)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "status": result.status.value})


@kitchen_bp.route("/api/item/<int:item_id>/ready", methods=["POST"])
@permission_required_api("manage_kitchen")
def api_item_ready(item_id: int):
    ok, result = kitchen_service.bump_item_ready(g.db, item_id)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "status": result.status.value})
