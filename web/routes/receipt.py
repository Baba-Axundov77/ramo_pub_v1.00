from __future__ import annotations

from flask import Blueprint, g, render_template

from database.models import Payment
from web.auth import permission_required

receipt_bp = Blueprint("receipt", __name__, url_prefix="/receipt")


@receipt_bp.route("/<int:payment_id>")
@permission_required("print_receipts")
def view_payment(payment_id: int):
    payment = g.db.query(Payment).filter(Payment.id == payment_id).first()
    return render_template("receipt/view.html", payment=payment)
