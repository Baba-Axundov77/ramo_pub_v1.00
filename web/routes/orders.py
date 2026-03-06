# web/routes/orders.py — Sifariş Marşrutları (Tam versiya)
from __future__ import annotations
from flask import (
    Blueprint, render_template, session, redirect,
    url_for, g, request, jsonify, flash
)
from modules.orders.order_service import OrderService
from modules.orders.workflow_service import order_workflow_service
from modules.tables.table_service import TableService
from modules.menu.menu_service import MenuService
from web.auth import permission_required, permission_required_api
from database.models import OrderStatus

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
@permission_required("take_orders")
def index():
    c = _check()
    if c:
        return c

    table_id = request.args.get("table_id", type=int)
    order_id = request.args.get("order_id", type=int)

    active  = svc.get_active_orders(g.db)
    today   = svc.get_today_orders(g.db)
    summary = svc.get_today_summary(g.db)
    tables  = table_svc.get_all(g.db)

    selected_table = table_svc.get_by_id(g.db, table_id) if table_id else None
    if selected_table:
        active = [o for o in active if o.table_id == selected_table.id]

    selected_order = None
    if order_id:
        selected_order = svc.get_order(g.db, order_id)
    elif selected_table and active:
        selected_order = active[0]

    categories = menu_svc.get_categories(g.db)
    menu_items = menu_svc.get_items(g.db, active_only=True, available_only=True)

    return render_template(
        "orders/index.html",
        active          = active,
        today           = today,
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
@permission_required_api("take_orders")
def api_create():
    data     = request.get_json(silent=True) or {}
    table_id = data.get("table_id")
    notes    = data.get("notes", "")

    if not table_id:
        return jsonify({"ok": False, "msg": "Masa seçilməyib"}), 400

    ok, result = svc.create_order(
        g.db,
        table_id  = int(table_id),
        waiter_id = _user_id(),
        notes     = notes,
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
@permission_required_api("take_orders")
def api_get(order_id: int):
    order = svc.get_order_with_details(g.db, order_id)
    if not order:
        return jsonify({"ok": False, "msg": "Sifariş tapılmadı"}), 404

    items = []
    for oi in order.items:
        # ── FIX: cancelled items-ı nə göstər, nə say ──
        if oi.status == OrderStatus.cancelled:
            continue
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
@permission_required_api("take_orders")
def api_add_item(order_id: int):
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
# API — MİQDAR YENİLƏ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/item/<int:item_id>/qty", methods=["POST"])
@permission_required_api("take_orders")
def api_update_qty(item_id: int):
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
# API — MƏHSUL SİL
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/item/<int:item_id>/remove", methods=["POST"])
@permission_required_api("take_orders")
def api_remove_item(item_id: int):
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
# API — STATUS DƏYİŞ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/status", methods=["POST"])
@permission_required_api("take_orders")
def api_status(order_id: int):
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
@permission_required_api("take_orders")
def api_cancel(order_id: int):
    ok, msg = svc.cancel_order(g.db, order_id)
    return jsonify({"ok": ok, "msg": str(msg)})


# ─────────────────────────────────────────────────────────────────────────────
# API — ÖDƏNİŞ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/pay", methods=["POST"])
@permission_required_api("process_payment")   # ← FIX: "s" yox, "process_payment"
def api_pay(order_id: int):
    data          = request.get_json(silent=True) or {}
    method        = data.get("method", "cash")
    discount_code = data.get("discount_code", "")

    # Sifarişi əvvəlcə yüklə (çek məlumatları üçün)
    order = svc.get_order_with_details(g.db, order_id)
    if not order:
        return jsonify({"ok": False, "msg": "Sifariş tapılmadı"}), 404

    # Status yoxla
    if order.status.value == "paid":
        return jsonify({"ok": False, "msg": "Bu sifariş artıq ödənilib."}), 400
    if order.status.value == "cancelled":
        return jsonify({"ok": False, "msg": "Ləğv edilmiş sifarişi ödəmək olmaz."}), 400

    # Subtotal yoxla və lazım gələrsə yenidən hesabla
    if not order.subtotal or order.subtotal <= 0:
        from modules.orders.order_service import OrderService
        OrderService()._recalculate(g.db, order)
        g.db.commit()
        g.db.refresh(order)
        if not order.subtotal or order.subtotal <= 0:
            return jsonify({"ok": False, "msg": "Sifarişdə məhsul yoxdur."}), 400

    # method yoxla
    allowed_methods = {"cash", "card", "online"}
    if method not in allowed_methods:
        method = "cash"

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

        # Çek üçün məhsul siyahısı — cancelled olanlar xaric
        items_data = []
        for oi in order.items:
            if oi.status == OrderStatus.cancelled:
                continue
            items_data.append({
                "name":       oi.menu_item.name if oi.menu_item else "?",
                "quantity":   oi.quantity,
                "unit_price": float(oi.unit_price),
                "subtotal":   float(oi.subtotal),
            })

        table_name = ""
        if order.table:
            table_name = order.table.name or f"Masa {order.table.number}"

        return jsonify({
            "ok":              True,
            "order_id":        order_id,
            "table_name":      table_name,
            "waiter":          order.waiter.full_name if order.waiter else "—",
            "amount":          float(result.amount),
            "discount_amount": float(result.discount_amount),
            "final_amount":    float(result.final_amount),
            "method":          result.method.value,
            "items":           items_data,
            "msg":             f"Ödəniş tamamlandı — {result.final_amount:.2f} ₼",
        })

    except Exception as e:
        return jsonify({"ok": False, "msg": f"Ödəniş xətası: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — AKTİV SİFARİŞLƏR
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
        "item_count":   len([i for i in o.items
                             if i.status != OrderStatus.cancelled]),
        "created_at":   o.created_at.strftime("%H:%M") if o.created_at else "",
    } for o in orders])


# ─────────────────────────────────────────────────────────────────────────────
# API — MASA ÜZRƏ AKTİV SİFARİŞ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/table/<int:table_id>/active")
@permission_required_api("take_orders")
def api_table_active(table_id: int):
    active = svc.get_active_orders(g.db)
    for o in active:
        if o.table_id == table_id:
            return jsonify({"ok": True, "order_id": o.id})
    return jsonify({"ok": False, "order_id": None})


# ─────────────────────────────────────────────────────────────────────────────
# API — MASA ÜZRƏ SİFARİŞ YARAT / VAR OLANI QAYTAR
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/tables/<int:table_id>/create-order", methods=["POST"])
@permission_required_api("take_orders")
def api_create_order_for_table(table_id: int):
    active = svc.get_active_orders(g.db)
    for o in active:
        if o.table_id == table_id:
            return jsonify({"ok": True, "order_id": o.id, "existing": True}), 200

    ok, result = svc.create_order(
        g.db,
        table_id  = table_id,
        waiter_id = _user_id(),
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 409
    return jsonify({"ok": True, "order_id": result.id, "existing": False}), 201


# ─────────────────────────────────────────────────────────────────────────────
# API — ENDİRİM TƏTBİQ ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/<int:order_id>/discount", methods=["POST"])
@permission_required_api("process_payment")
def api_apply_discount(order_id: int):
    data   = request.get_json(silent=True) or {}
    amount = float(data.get("amount", 0) or 0)
    ok, result = svc.apply_discount(g.db, order_id, amount)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({
        "ok":       True,
        "subtotal": float(result.subtotal or 0),
        "discount": float(result.discount_amount or 0),
        "total":    float(result.total or 0),
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — MENYU
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
