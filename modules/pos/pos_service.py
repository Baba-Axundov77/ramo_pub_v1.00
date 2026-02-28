# modules/pos/pos_service.py — Kassa & Ödəniş İş Məntiqi
from sqlalchemy.orm import Session
from datetime import datetime, date
from database.models import (
    Payment, Order, OrderStatus, PaymentMethod,
    Customer, Discount
)


class POSService:

    def process_payment(self, db: Session, order_id: int,
                        method: str, cashier_id: int,
                        discount_code: str = None,
                        loyalty_points_used: int = 0):
        """
        Ödənişi icra et.
        Qaytarır: (True, payment_obj) | (False, xəta_mesajı)
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return False, "Sifariş tapılmadı."
        if order.status == OrderStatus.paid:
            return False, "Bu sifariş artıq ödənilib."
        if order.status == OrderStatus.cancelled:
            return False, "Ləğv edilmiş sifariş ödənilə bilməz."

        discount_amount = order.discount_amount or 0.0

        # ── Endirim kodu ──────────────────────────────────────────────────────
        if discount_code:
            ok, disc_result = self._apply_discount_code(db, order, discount_code)
            if ok:
                discount_amount += disc_result
            else:
                return False, disc_result

        # ── Loyallıq xalları ──────────────────────────────────────────────────
        if loyalty_points_used > 0 and order.customer_id:
            ok, points_value = self._use_loyalty_points(
                db, order.customer_id, loyalty_points_used
            )
            if ok:
                discount_amount += points_value

        final_amount = max(0.0, order.subtotal - discount_amount)
        order.discount_amount = discount_amount
        order.total = final_amount

        # ── Ödəniş yaz ────────────────────────────────────────────────────────
        payment = Payment(
            order_id        = order_id,
            amount          = order.subtotal,
            discount_amount = discount_amount,
            final_amount    = final_amount,
            method          = PaymentMethod[method],
            cashier_id      = cashier_id,
        )
        db.add(payment)

        # ── Sifariş statusu ───────────────────────────────────────────────────
        order.status  = OrderStatus.paid
        order.paid_at = datetime.now()
        if order.table:
            from database.models import TableStatus
            order.table.status = TableStatus.available

        # ── Loyallıq xalı qazandır ────────────────────────────────────────────
        if order.customer_id:
            self._earn_loyalty_points(db, order.customer_id, final_amount)

        db.commit()
        db.refresh(payment)
        return True, payment

    # ── ENDİRİM KODU ──────────────────────────────────────────────────────────

    def _apply_discount_code(self, db: Session, order: Order, code: str):
        today = date.today()
        disc = db.query(Discount).filter(
            Discount.code      == code.upper(),
            Discount.is_active == True,
        ).first()
        if not disc:
            return False, "Endirim kodu tapılmadı."
        if disc.valid_from and disc.valid_from > today:
            return False, "Endirim kodu hələ aktiv deyil."
        if disc.valid_until and disc.valid_until < today:
            return False, "Endirim kodunun vaxtı keçib."
        if disc.usage_limit > 0 and disc.used_count >= disc.usage_limit:
            return False, "Endirim kodunun istifadə limiti dolub."
        if order.subtotal < disc.min_order:
            return False, f"Minimum sifariş məbləği {disc.min_order:.2f} ₼ olmalıdır."

        disc.used_count += 1
        if disc.type == "percent":
            amount = order.subtotal * (disc.value / 100)
        else:
            amount = disc.value
        return True, amount

    # ── LOYALLIK XALLAR ───────────────────────────────────────────────────────

    def _earn_loyalty_points(self, db: Session, customer_id: int, amount: float):
        """Hər 1 ₼ = 1 xal."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            points = int(amount)
            customer.points      += points
            customer.total_spent += amount

    def _use_loyalty_points(self, db: Session, customer_id: int, points: int):
        """100 xal = 1 ₼ endirim."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return False, 0
        if customer.points < points:
            return False, f"Kifayət qədər xal yoxdur. Mövcud: {customer.points}"
        customer.points -= points
        value = points / 100.0
        return True, value

    # ── HESABAT ──────────────────────────────────────────────────────────────

    def get_daily_summary(self, db: Session, target_date: date = None):
        if not target_date:
            target_date = date.today()
        start = datetime.combine(target_date, datetime.min.time())
        end   = datetime.combine(target_date, datetime.max.time())

        payments = db.query(Payment).filter(
            Payment.created_at >= start,
            Payment.created_at <= end,
        ).all()

        total      = sum(p.final_amount for p in payments)
        by_method  = {}
        for pm in PaymentMethod:
            method_payments = [p for p in payments if p.method == pm]
            by_method[pm.value] = sum(p.final_amount for p in method_payments)

        return {
            "date":        target_date,
            "count":       len(payments),
            "total":       total,
            "by_method":   by_method,
            "discount_total": sum(p.discount_amount for p in payments),
        }

    def check_discount_code(self, db: Session, code: str, order_subtotal: float):
        """Endirim kodunu yoxla (preview üçün)."""
        today = date.today()
        disc = db.query(Discount).filter(
            Discount.code      == code.upper(),
            Discount.is_active == True,
        ).first()
        if not disc:
            return False, "Endirim kodu tapılmadı."
        if disc.valid_until and disc.valid_until < today:
            return False, "Endirim kodunun vaxtı keçib."
        if disc.usage_limit > 0 and disc.used_count >= disc.usage_limit:
            return False, "Limit dolub."
        if order_subtotal < disc.min_order:
            return False, f"Min. məbləğ: {disc.min_order:.2f} ₼"
        if disc.type == "percent":
            amount = order_subtotal * (disc.value / 100)
            label  = f"%{disc.value:.0f} endirim"
        else:
            amount = disc.value
            label  = f"{disc.value:.2f} ₼ endirim"
        return True, {"amount": amount, "label": label, "discount": disc}


pos_service = POSService()
