# modules/pos/pos_service.py — Kassa & Ödəniş İş Məntiqi
from sqlalchemy.orm import Session
from datetime import datetime, date
from config import ALLOW_NEGATIVE_STOCK
from modules.inventory.unit_conversion import convert_quantity
from database.models import (
    Payment, Order, OrderStatus, PaymentMethod,
    Customer, Discount, InventoryItem, MenuItemRecipe, InventoryAdjustment
    Customer, Discount, InventoryItem
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

        # ── Anbardan istifadə olunan xammalı çıx ───────────────────────────
        ok, stock_result = self._consume_inventory_for_order(db, order)
        if not ok:
            return False, stock_result

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

    def _consume_inventory_for_order(self, db: Session, order: Order):
        shortages: list[str] = []
        consumptions: list[tuple[InventoryItem, float, str]] = []

        for oi in order.items:
            menu_item = oi.menu_item
            if not menu_item:
                continue

            today = date.today()
            recipe_lines = db.query(MenuItemRecipe).filter(
                MenuItemRecipe.menu_item_id == menu_item.id,
                MenuItemRecipe.is_active == True
            ).filter((MenuItemRecipe.valid_from == None) | (MenuItemRecipe.valid_from <= today)).filter((MenuItemRecipe.valid_until == None) | (MenuItemRecipe.valid_until >= today)).all()
            if recipe_lines:
                for line in recipe_lines:
                    inv = db.query(InventoryItem).filter(InventoryItem.id == line.inventory_item_id).first()
                    if not inv:
                        continue
                    required_raw = float(line.quantity_per_unit or 0.0) * float(oi.quantity or 0)
                    ok_conv, required, msg = convert_quantity(required_raw, line.quantity_unit or inv.unit, inv.unit)
                    if not ok_conv:
                        shortages.append(f"{menu_item.name} -> {inv.name}: {msg}")
                        continue
                    if required <= 0:
                        continue
                    current_qty = float(inv.quantity or 0.0)
                    if (not ALLOW_NEGATIVE_STOCK) and current_qty < required:
                        unit = inv.unit or "vahid"
                        shortages.append(
                            f"{menu_item.name} -> {inv.name}: tələb {required:.2f} {unit}, mövcud {current_qty:.2f} {unit}"
                        )
                    consumptions.append((inv, required, menu_item.name))
                continue

            # geriyə uyğunluq: köhnə tək-stok modeli
            if not menu_item.inventory_item_id:

        for oi in order.items:
            menu_item = oi.menu_item
            if not menu_item or not menu_item.inventory_item_id:
                continue
            usage_per_item = float(menu_item.stock_usage_qty or 0.0)
            if usage_per_item <= 0:
                continue
            inv = db.query(InventoryItem).filter(InventoryItem.id == menu_item.inventory_item_id).first()
            if not inv:
                continue
            required = usage_per_item * float(oi.quantity or 0)
            current_qty = float(inv.quantity or 0.0)
            if (not ALLOW_NEGATIVE_STOCK) and current_qty < required:

            inv = db.query(InventoryItem).filter(InventoryItem.id == menu_item.inventory_item_id).first()
            if not inv:
                continue

            required = usage_per_item * float(oi.quantity or 0)
            current_qty = float(inv.quantity or 0.0)
            if current_qty < required:
                unit = inv.unit or "vahid"
                shortages.append(
                    f"{menu_item.name}: tələb {required:.2f} {unit}, mövcud {current_qty:.2f} {unit}"
                )
            consumptions.append((inv, required, menu_item.name))

        if shortages:
            return False, "Stok kifayət deyil: " + " | ".join(shortages)

        for inv, required, menu_name in consumptions:
            inv.quantity = float(inv.quantity or 0.0) - required
            db.add(
                InventoryAdjustment(
                    inventory_item_id=inv.id,
                    delta_quantity=-required,
                    unit=inv.unit,
                    adjustment_type="sale",
                    reason=f"Satış: {menu_name}",
                    reference=f"order:{order.id}",
                )
            )
        for oi in order.items:
            menu_item = oi.menu_item
            if not menu_item or not menu_item.inventory_item_id:
                continue
            usage_per_item = float(menu_item.stock_usage_qty or 0.0)
            if usage_per_item <= 0:
                continue

            inv = db.query(InventoryItem).filter(InventoryItem.id == menu_item.inventory_item_id).first()
            if not inv:
                continue

            inv.quantity = float(inv.quantity or 0.0) - (usage_per_item * float(oi.quantity or 0))

        return True, None

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
        is_expired = bool(disc.valid_until and disc.valid_until < today)
        is_limit_over = bool(disc.usage_limit > 0 and disc.used_count >= disc.usage_limit)
        if is_expired and is_limit_over:
            return False, "Bu endirim kodunun vaxtı bitib və istifadə limiti də qurtarıb."
        if is_expired:
            return False, "Bu endirim kodunun vaxtı bitib."
        if is_limit_over:
            return False, "Bu endirim kodunun istifadə limiti qurtarıb."
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
        is_expired = bool(disc.valid_until and disc.valid_until < today)
        is_limit_over = bool(disc.usage_limit > 0 and disc.used_count >= disc.usage_limit)
        if is_expired and is_limit_over:
            return False, "Bu endirim kodunun vaxtı bitib və istifadə limiti də qurtarıb."
        if is_expired:
            return False, "Bu endirim kodunun vaxtı bitib."
        if is_limit_over:
            return False, "Bu endirim kodunun istifadə limiti qurtarıb."
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
