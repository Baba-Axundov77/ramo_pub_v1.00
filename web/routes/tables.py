# web/routes/tables.py — Masa Marşrutları (Tam versiya)
from __future__ import annotations
from flask import (
    Blueprint, render_template, session, redirect,
    url_for, g, jsonify, request, flash
)
from modules.tables.table_service import TableService
from modules.orders.workflow_service import order_workflow_service

bp = Blueprint("tables", __name__, url_prefix="/tables")
svc = TableService()


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
    tables = svc.get_all(g.db)
    stats = svc.get_stats(g.db)
    return render_template("tables/index.html", tables=tables, stats=stats)


# ─────────────────────────────────────────────────────────────────────────────
# API — BÜTÜN MASALAR
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/all")
def api_all():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    tables = svc.get_all(g.db)
    return jsonify([{
        "id":       t.id,
        "number":   t.number,
        "name":     t.name or "",
        "status":   t.status.value,
        "floor":    t.floor,
        "capacity": t.capacity,
    } for t in tables])


# ─────────────────────────────────────────────────────────────────────────────
# API — STATUS DƏYİŞ
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# API — AKTİV SİFARİŞ
# ─────────────────────────────────────────────────────────────────────────────

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
            "id":     order.id,
            "status": order.status.value,
            "total":  float(order.total or 0),
        }
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — YENİ SİFARİŞ YARAT (masadan birbaşa)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/create-order/<int:table_id>", methods=["POST"])
def create_order(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    # Aktiv sifariş varmı?
    existing = svc.get_active_order(g.db, table_id)
    if existing:
        return jsonify({
            "ok":       False,
            "msg":      f"Bu masada artıq aktiv sifariş var (#{existing.id}).",
            "order_id": existing.id,
            "redirect": f"/orders/?table_id={table_id}&order_id={existing.id}&focus_menu=1",
        }), 409

    ok, result = order_svc.create_order(
        g.db,
        table_id=table_id,
        waiter_id=_user_id(),
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    order = result["order"]
    created = result["created"]
    status_code = 201 if created else 409
    return jsonify({
        "ok":       True,
        "order_id": result.id,
        "redirect": f"/orders/?table_id={table_id}&order_id={result.id}&focus_menu=1",
        "msg":      f"Sifariş #{result.id} yaradıldı",
    })


# ─────────────────────────────────────────────────────────────────────────────
# API — REZERV ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/reserve/<int:table_id>", methods=["POST"])
def reserve_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    # Aktiv sifariş varsa rezerv etmə
    active = svc.get_active_order(g.db, table_id)
    if active:
        return jsonify({"ok": False, "msg": "Dolu masanı rezerv etmək olmaz."}), 400

    ok, result = svc.set_status(g.db, table_id, "reserved")
    return jsonify({"ok": ok, "msg": "Masa rezerv edildi" if ok else str(result)})


# ─────────────────────────────────────────────────────────────────────────────
# API — TƏMİZLƏNİR
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/clean/<int:table_id>", methods=["POST"])
def clean_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    ok, result = svc.set_status(g.db, table_id, "cleaning")
    return jsonify({"ok": ok, "msg": "Masa təmizlənir" if ok else str(result)})


# ─────────────────────────────────────────────────────────────────────────────
# API — BOŞ ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/free/<int:table_id>", methods=["POST"])
def free_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401

    # Aktiv sifariş varsa boş etmə
    active = svc.get_active_order(g.db, table_id)
    if active:
        return jsonify({
            "ok":  False,
            "msg": f"Masada aktiv sifariş var (#{active.id}). Əvvəlcə ödəniş edin."
        }), 400

    ok, result = svc.set_status(g.db, table_id, "available")
    return jsonify({"ok": ok, "msg": "Masa boşaldıldı" if ok else str(result)})


# ─────────────────────────────────────────────────────────────────────────────
# API — MASA YARAT (admin)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/create", methods=["POST"])
def api_create_table():
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401
    if session["user"].get("role") != "admin":
        return jsonify({"ok": False, "msg": "İcazə yoxdur"}), 403

    data = request.get_json(silent=True) or {}
    ok, result = svc.create(
        g.db,
        number=int(data.get("number", 0)),
        name=data.get("name"),
        capacity=int(data.get("capacity", 4)),
        floor=int(data.get("floor", 1)),
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "table_id": result.id, "msg": "Masa yaradıldı"})


# ─────────────────────────────────────────────────────────────────────────────
# API — STATİSTİKA
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/stats")
def api_stats():
    if "user" not in session:
        return jsonify({"error": "401"}), 401
    stats = svc.get_stats(g.db)
    return jsonify(stats)


# ─────────────────────────────────────────────────────────────────────────────
# API — MASA YENİLƏ (admin)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/update/<int:table_id>", methods=["POST"])
def api_update_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401
    if session["user"].get("role") != "admin":
        return jsonify({"ok": False, "msg": "İcazə yoxdur"}), 403

    data = request.get_json(silent=True) or {}
    ok, result = svc.update(
        g.db, table_id,
        name=data.get("name"),
        capacity=int(data.get("capacity", 4)),
        floor=int(data.get("floor", 1)),
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "msg": "Masa yeniləndi"})
