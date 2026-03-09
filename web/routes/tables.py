# web/routes/tables.py — Masa Marşrutları (Tam versiya)
from __future__ import annotations
import os
import uuid
from flask import (
    Blueprint, render_template, session, redirect,
    url_for, g, jsonify, request, flash
)
from modules.tables.table_service import TableService
from modules.orders.workflow_service import order_workflow_service
from web.auth import permission_required, permission_required_api

bp = Blueprint("tables", __name__, url_prefix="/tables")
svc = TableService()

UPLOAD_FOLDER = os.path.join("assets", "table_images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_uploaded_image(file) -> str | None:
    if not file or not file.filename:
        return None
    if not _allowed_file(file.filename):
        return None
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return f"table_images/{filename}"


def _check():
    if "user" not in session:
        return redirect(url_for("auth.login"))


def _user_id():
    return session["user"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# SƏHIFƏ
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/")
@permission_required("manage_tables")
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
@permission_required_api("manage_tables")
def set_status(table_id: int):
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
@permission_required_api("manage_tables")
def create_order(table_id: int):
    ok, result = order_workflow_service.ensure_order_for_table(
        g.db,
        table_id=table_id,
        waiter_id=_user_id(),
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400

    order = result["order"]
    created = result["created"]
    status_code = 201 if created else 409
    msg = (
        f"Sifariş #{order.id} yaradıldı"
        if created else
        f"Bu masada artıq aktiv sifariş var (#{order.id})."
    )

    return jsonify({
        "ok": created,
        "order_id": order.id,
        "redirect": f"/orders/?table_id={table_id}&order_id={order.id}&focus_menu=1",
        "msg": msg,
    }), status_code


# ─────────────────────────────────────────────────────────────────────────────
# API — REZERV ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/reserve/<int:table_id>", methods=["POST"])
@permission_required_api("manage_tables")
def reserve_table(table_id: int):
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
@permission_required_api("manage_tables")
def clean_table(table_id: int):
    ok, result = svc.set_status(g.db, table_id, "cleaning")
    return jsonify({"ok": ok, "msg": "Masa təmizlənir" if ok else str(result)})


# ─────────────────────────────────────────────────────────────────────────────
# API — BOŞ ET
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/api/free/<int:table_id>", methods=["POST"])
@permission_required_api("manage_tables")
def free_table(table_id: int):
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
@permission_required_api("manage_tables")
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
@permission_required_api("manage_tables")
def api_update_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401
    if session["user"].get("role") != "admin":
        return jsonify({"ok": False, "msg": "İcazə yoxdur"}), 403

    data = request.get_json(silent=True) or {}
    if request.form:
        data = request.form

    image_path = (data.get("image_path") or "").strip() or None
    if "image_file" in request.files:
        uploaded = _save_uploaded_image(request.files["image_file"])
        if uploaded:
            image_path = uploaded

    ok, result = svc.update(
        g.db, table_id,
        name=data.get("name"),
        capacity=int(data.get("capacity", 4) or 4),
        floor=int(data.get("floor", 1) or 1),
        image_path=image_path,
    )
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "msg": "Masa yeniləndi"})


@bp.route("/api/delete/<int:table_id>", methods=["POST"])
@permission_required_api("manage_tables")
def api_delete_table(table_id: int):
    if "user" not in session:
        return jsonify({"ok": False, "msg": "Giriş tələb olunur"}), 401
    if session["user"].get("role") != "admin":
        return jsonify({"ok": False, "msg": "İcazə yoxdur"}), 403

    ok, result = svc.delete(g.db, table_id)
    if not ok:
        return jsonify({"ok": False, "msg": str(result)}), 400
    return jsonify({"ok": True, "msg": "Masa silindi"})
