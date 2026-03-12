# modules/pos/pos_service.py — Kassa & Ödəniş İş Məntiqi
from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.exc import SQLAlchemyError
from src.core.database.models import (
    Payment,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Customer,
    Discount,
    InventoryItem,
    MenuItemRecipe,
    InventoryAdjustment,
)
from src.core.modules.inventory.unit_conversion import convert_quantity
from src.core.modules.audit.audit_logger import audit_action, AuditLogger


class POSService:
    @audit_action("PROCESS", "payment")
    def process_payment(self, db: Session, order_id: int,
                        method: str, cashier_id: int,
                        discount_code: str = None,
                        loyalty_points_used: int = 0):
        """
        Ödənişi icra et.
        Qaytarır: (True, payment_obj) | (False, xəta_mesajı)
        """
        try:
            # SQLAlchemy 2.0 syntax with select()
            stmt = (
                select(Order)
                .options(
                    joinedload(Order.table),
                    selectinload(Order.items).joinedload(OrderItem.menu_item),
                )
                .where(Order.id == order_id)
            )
            
            result = db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                return False, "Sifariş tapılmadı."
            if order.status == OrderStatus.paid:
                return False, "Bu sifariş artıq ödənilib."
            if order.status == OrderStatus.cancelled:
                return False, "Ləğv edilmiş sifariş ödənilə bilməz."

            discount_amount = order.discount_amount or 0.0

            if discount_code:
                ok, disc_result = self._apply_discount_code(db, order, discount_code)
                if ok:
                    discount_amount += disc_result
                else:
                    return False, disc_result

            if loyalty_points_used > 0 and order.customer_id:
                ok, points_value = self._use_loyalty_points(
                    db, order.customer_id, loyalty_points_used
                )
                if ok:
                    discount_amount += points_value

            final_amount = max(0.0, order.subtotal - discount_amount)
            order.discount_amount = discount_amount
            order.total = final_amount

            ok, stock_result = self._consume_inventory_for_order(db, order)
            if not ok:
                db.rollback()
                return False, stock_result

            payment = Payment(
                order_id=order_id,
                amount=order.subtotal,
                discount_amount=discount_amount,
                final_amount=final_amount,
                method=PaymentMethod[method],
                cashier_id=cashier_id,
            )
            db.add(payment)

            order.status = OrderStatus.paid
            order.paid_at = datetime.now()
            if order.table:
                from src.core.database.models import TableStatus
                order.table.status = TableStatus.available

            if order.customer_id:
                self._earn_loyalty_points(db, order.customer_id, final_amount)

            db.commit()
            db.refresh(payment)
            return True, payment
        except Exception as e:
            db.rollback()
            return False, f"Ödəniş zamanı xəta: {str(e)}"

    @audit_action("UPDATE", "inventory")
    def _consume_inventory_for_order(self, db: Session, order: Order):
        shortages: list[str] = []
        consumption_by_inventory: dict[int, float] = {}
        menu_names_by_inventory: dict[int, set[str]] = {}

        active_items = [oi for oi in order.items if oi.status != OrderStatus.cancelled]
        if not active_items:
            return True, None

        # Bulk load all recipe lines and inventory items at once
        menu_item_ids = {oi.menu_item_id for oi in active_items if oi.menu_item_id}
        today = date.today()
        
        # Load all recipe lines in single query
        stmt = (
            select(MenuItemRecipe)
            .where(
                MenuItemRecipe.menu_item_id.in_(menu_item_ids),
                MenuItemRecipe.is_active == True,
                (MenuItemRecipe.valid_from == None) | (MenuItemRecipe.valid_from <= today),
                (MenuItemRecipe.valid_until == None) | (MenuItemRecipe.valid_until >= today)
            )
        )
        
        result = db.execute(stmt)
        recipe_lines = result.scalars().all() if menu_item_ids else []

        # Collect all inventory IDs needed
        inventory_ids = set()
        for line in recipe_lines:
            if line.inventory_item_id:
                inventory_ids.add(line.inventory_item_id)
        
        for oi in active_items:
            if oi.menu_item and oi.menu_item.inventory_item_id:
                inventory_ids.add(oi.menu_item.inventory_item_id)

        # Bulk load all inventory items at once with SELECT FOR UPDATE
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.id.in_(inventory_ids))
            .with_for_update()  # Critical: Prevent race conditions
        )
        
        result = db.execute(stmt)
        inventory_rows = result.scalars().all() if inventory_ids else []
        
        # Create lookup dictionaries for O(1) access
        inventory_map = {inv.id: inv for inv in inventory_rows}
        recipes_by_menu_item = {}
        for line in recipe_lines:
            recipes_by_menu_item.setdefault(line.menu_item_id, []).append(line)

        for oi in active_items:
            menu_item = oi.menu_item
            if not menu_item:
                continue

            menu_recipes = recipes_by_menu_item.get(menu_item.id, [])

            if menu_recipes:
                for line in menu_recipes:
                    inv = inventory_map.get(line.inventory_item_id)
                    if not inv:
                        continue
                    required_raw = float(line.quantity_per_unit or 0.0) * float(oi.quantity or 0)
                    ok_conv, required, msg = convert_quantity(
                        required_raw,
                        line.quantity_unit or inv.unit,
                        inv.unit,
                    )
                    if not ok_conv:
                        shortages.append(f"{menu_item.name} -> {inv.name}: {msg}")
                        continue
                    if required <= 0:
                        continue
                    current_qty = float(inv.quantity or 0.0)
                    already_planned = float(consumption_by_inventory.get(inv.id, 0.0))
                    available_qty = current_qty - already_planned
                    if (not ALLOW_NEGATIVE_STOCK) and available_qty < required:
                        unit = inv.unit or "vahid"
                        shortages.append(
                            f"{menu_item.name} -> {inv.name}: tələb {required:.2f} {unit}, mövcud {max(0.0, available_qty):.2f} {unit}"
                        )
                    consumption_by_inventory[inv.id] = already_planned + required
                    menu_names_by_inventory.setdefault(inv.id, set()).add(menu_item.name)
                continue

            if not menu_item.inventory_item_id:
                continue

            usage_per_item = float(menu_item.stock_usage_qty or 0.0)
            if usage_per_item <= 0:
                continue

            inv = inventory_map.get(menu_item.inventory_item_id)
            if not inv:
                continue

            required = usage_per_item * float(oi.quantity or 0)
            current_qty = float(inv.quantity or 0.0)
            already_planned = float(consumption_by_inventory.get(inv.id, 0.0))
            available_qty = current_qty - already_planned
            if (not ALLOW_NEGATIVE_STOCK) and available_qty < required:
                unit = inv.unit or "vahid"
                shortages.append(
                    f"{menu_item.name}: tələb {required:.2f} {unit}, mövcud {max(0.0, available_qty):.2f} {unit}"
                )
            consumption_by_inventory[inv.id] = already_planned + required
            menu_names_by_inventory.setdefault(inv.id, set()).add(menu_item.name)

        if shortages:
            return False, "Stok kifayət deyil: " + " | ".join(shortages)

        for inv_id, required in consumption_by_inventory.items():
            inv = inventory_map.get(inv_id)
            if not inv:
                continue
            inv.quantity = float(inv.quantity or 0.0) - required
            menu_names = sorted(menu_names_by_inventory.get(inv_id, set()))
            reason = f"Satış: {', '.join(menu_names)}" if menu_names else "Satış"
            db.add(
                InventoryAdjustment(
                    inventory_item_id=inv.id,
                    delta_quantity=-required,
                    unit=inv.unit,
                    adjustment_type="sale",
                    reason=reason,
                    reference=f"order:{order.id}",
                )
            )

        return True, None

    def _apply_discount_code(self, db: Session, order: Order, code: str):
        today = date.today()
        disc = db.query(Discount).filter(
            Discount.code == code.upper(),
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

    def _earn_loyalty_points(self, db: Session, customer_id: int, amount: float):
        """Hər 1 ₼ = 1 xal."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            points = int(amount)
            customer.points += points
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

    def get_daily_summary(self, db: Session, target_date: date = None):
        if not target_date:
            target_date = date.today()
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())

        payments = db.query(Payment).filter(
            Payment.created_at >= start,
            Payment.created_at <= end,
        ).all()

        total = sum(p.final_amount for p in payments)
        by_method = {}
        for pm in PaymentMethod:
            method_payments = [p for p in payments if p.method == pm]
            by_method[pm.value] = sum(p.final_amount for p in method_payments)

        return {
            "date": target_date,
            "count": len(payments),
            "total": total,
            "by_method": by_method,
            "discount_total": sum(p.discount_amount for p in payments),
            "start": start,
            "end": end,
        }

    def check_discount_code(self, db: Session, code: str, order_subtotal: float):
        """Endirim kodunu yoxla (preview üçün)."""
        today = date.today()
        disc = db.query(Discount).filter(
            Discount.code == code.upper(),
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
            label = f"%{disc.value:.0f} endirim"
        else:
            amount = disc.value
            label = f"{disc.value:.2f} ₼ endirim"
        return True, {"amount": amount, "label": label, "discount": disc}


pos_service = POSService()
