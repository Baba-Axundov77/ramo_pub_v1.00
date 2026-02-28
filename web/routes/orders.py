# web/routes/orders.py — Sifariş Marşrutları (Tam versiya)
from __future__ import annotations
from flask import (
    Blueprint, render_template, session, redirect,
    url_for, g, request, jsonify, flash
)
from modules.orders.order_service import OrderService
from modules.tables.table_service import TableService
from modules.menu.menu_service import MenuService

bp        = Blueprint("orders", __name__, url_prefix="/orders")
svc       = OrderService()
table_svc = TableService()
menu_svc  = MenuService()


def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))


def _user_id():
    return session["user"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# SƏHIFƏ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    c = _check()
    if c:
        return c

    table_id = request.args.get("table_id", type=int)
    order_id = request.args.get("order_id", type=int)

    active  = svc.get_active_orders(g.db)
    today   = svc.get_today_orders(g.db)
    completed_today = [
        o for o in today
        if o.status.value in {"paid", "cancelled"}
    ]
    summary = svc.get_today_summary(g.db)
    tables  = table_svc.get_all(g.db)

    selected_table = table_svc.get_by_id(g.db, table_id) if table_id else None
    if selected_table:
        active = [o for o in active if o.table_id == selected_table.id]
        completed_today = [o for o in completed_today if o.table_id == selected_table.id]

    selected_order = None
    if order_id:
        selected_order = svc.get_order(g.db, order_id)
    elif selected_table and active:
        selected_order = active[0]

    # Menyu kateqoriya + məhsullar
    categories = menu_svc.get_categories(g.db)
    menu_items = menu_svc.get_items(g.db, active_only=True, available_only=True)

    return render_template(
        "orders/index.html",
        active          = active,
        today           = today,
        completed_today = completed_today,
        summary         = summary,
        tables          = tables,
        selected_table  = selected_table,
        selected_order  = selected_order,
        categories      = categories,
        menu_items      = menu_items,
    )


# ─────────────────────────────────────────────────────────────────────────────
# API — YENİ SİFARİŞ YARAT
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/create", methods=["POST"])
def api_create():
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    data     = request.get_json(silent=True) or {}
    table_id = data.get("table_id")
    notes    = data.get("notes", "")

    if not table_id:
        return jsonify({"ok": False, "msg": "Masa seçilməyib"}), 400

    ok, result = svc.create_order(
        g.db,
        table_id   = int(table_id),
        waiter_id  = _user_id(),
        notes      = notes,
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    return jsonify({
        "ok":       True,
        "order_id": result.id,
        "msg":      f"Sifariş #{result.id} yaradıldı",
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — SİFARİŞ MƏLUMATLARINI AL
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>")
def api_get(order_id: int):
    if "user" not in session:
        return jsonify({"ok": False}), 401

    order = svc.get_order(g.db, order_id)
    if not order:
        return jsonify({"ok": False, "msg": "Sifariş tapılmadı"}), 404

    items = []
    for oi in order.items:
        items.append({
            "id":         oi.id,
            "name":       oi.menu_item.name if oi.menu_item else "?",
            "quantity":   oi.quantity,
            "unit_price": float(oi.unit_price),
            "subtotal":   float(oi.subtotal),
            "notes":      oi.notes or "",
        })

    return jsonify({
        "ok": True,
        "order": {
            "id":              order.id,
            "status":          order.status.value,
            "subtotal":        float(order.subtotal or 0),
            "discount_amount": float(order.discount_amount or 0),
            "total":           float(order.total or 0),
            "notes":           order.notes or "",
            "table_number":    order.table.number if order.table else None,
            "waiter":          order.waiter.full_name if order.waiter else None,
            "created_at":      order.created_at.strftime("%H:%M") if order.created_at else "",
            "items":           items,
        }
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — MƏHSUL ƏLAVƏ ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/add-item", methods=["POST"])
def api_add_item(order_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    data         = request.get_json(silent=True) or {}
    menu_item_id = data.get("menu_item_id")
    quantity     = int(data.get("quantity", 1))
    notes        = data.get("notes", "")

    if not menu_item_id:
        return jsonify({"ok": False, "msg": "Məhsul seçilməyib"}), 400

    ok, result = svc.add_item(
        g.db, order_id, int(menu_item_id), quantity, notes
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    return jsonify({
        "ok":       True,
        "subtotal": float(result.subtotal or 0),
        "total":    float(result.total or 0),
        "msg":      "Məhsul əlavə edildi",
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — MƏHSUL SİL
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/item/<int:item_id>/remove", methods=["POST"])
def api_remove_item(item_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    ok, result = svc.remove_item(g.db, item_id)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    return jsonify({
        "ok":       True,
        "subtotal": float(result.subtotal or 0),
        "total":    float(result.total or 0),
        "msg":      "Məhsul silindi",
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — MİQDAR YENİLƏ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/item/<int:item_id>/qty", methods=["POST"])
def api_update_qty(item_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    data     = request.get_json(silent=True) or {}
    quantity = int(data.get("quantity", 1))

    ok, result = svc.update_item_qty(g.db, item_id, quantity)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    return jsonify({
        "ok":       True,
        "subtotal": float(result.subtotal or 0),
        "total":    float(result.total or 0),
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — STATUS DƏYİŞ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/status", methods=["POST"])
def api_status(order_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    data   = request.get_json(silent=True) or {}
    status = data.get("status", "")

    allowed = {"new", "preparing", "ready", "served", "paid", "cancelled"}
    if status not in allowed:
        return jsonify({"ok": False, "msg": "Yanlış status"}), 400

    ok, result = svc.update_status(g.db, order_id, status)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    return jsonify({
        "ok":     True,
        "status": result.status.value,
        "msg":    "Status yeniləndi",
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — SİFARİŞ LƏĞV ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/cancel", methods=["POST"])
def api_cancel(order_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    ok, msg = svc.cancel_order(g.db, order_id)
    return jsonify({"ok": ok, "msg": str(msg)})


# ─────────────────────────────────────────────────────────────────────────────
# API — ÖDƏNİŞ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/pay", methods=["POST"])
def api_pay(order_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    data          = request.get_json(silent=True) or {}
    method        = data.get("method", "cash")
    discount_code = data.get("discount_code", "")

    try:
        from modules.pos.pos_service import pos_service
        ok, result = pos_service.process_payment(
            g.db,
            order_id      = order_id,
            cashier_id    = _user_id(),
            method        = method,
            discount_code = discount_code or None,
        )
        if not ok:
            return jsonify({"ok": False, "msg": str(result)}), 400
        return jsonify({
            "ok":           True,
            "final_amount": float(result.final_amount),
            "msg":          "Ödəniş qəbul edildi ✅",
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — AKTİV SİFARİŞLƏR (dashboard refresh)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/active")
def api_active():
    if "user" not in session:
        return jsonify({"error": "401"}), 401

    orders = svc.get_active_orders(g.db)
    return jsonify([{
        "id":           o.id,
        "table_number": o.table.number if o.table else None,
        "status":       o.status.value,
        "total":        float(o.total or 0),
        "item_count":   len(o.items),
        "created_at":   o.created_at.strftime("%H:%M") if o.created_at else "",
    } for o in orders])


# ─────────────────────────────────────────────────────────────────────────────
# API — MENYU (sifariş zamanı)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/menu")
def api_menu():
    if "user" not in session:
        return jsonify({"error": "401"}), 401

    cat_id = request.args.get("cat_id", type=int)
    items  = menu_svc.get_items(g.db, category_id=cat_id, active_only=True, available_only=True)
    cats   = menu_svc.get_categories(g.db)

    return jsonify({
        "categories": [{"id": c.id, "name": c.name, "icon": c.icon or "🍽️"} for c in cats],
        "items": [{
            "id":    i.id,
            "name":  i.name,
            "price": float(i.price),
            "cat":   i.category.name if i.category else "",
        } for i in items],
    })
