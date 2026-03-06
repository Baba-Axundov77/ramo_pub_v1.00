# modules/orders/order_service.py — Sifariş İş Məntiqi
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import desc
from datetime import datetime, date
from database.models import (
    Order, OrderItem, OrderStatus, Table, TableStatus, MenuItem
)


class OrderService:

    # ── SİFARİŞ YARAT ─────────────────────────────────────────────────────────

    def create_order(self, db: Session, table_id: int, waiter_id: int,
                     customer_id: int = None, notes: str = None):
        table = db.query(Table).filter(Table.id == table_id).first()
        if not table:
            return False, "Masa tapılmadı."

        existing = db.query(Order).filter(
            Order.table_id == table_id,
            Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
        ).first()
        if existing:
            return False, f"Bu masada artıq aktiv sifariş var (#{existing.id})."

        order = Order(
            table_id    = table_id,
            waiter_id   = waiter_id,
            customer_id = customer_id,
            notes       = notes,
            status      = OrderStatus.new,
        )
        db.add(order)
        table.status = TableStatus.occupied
        db.commit()
        db.refresh(order)
        return True, order

    # ── SİFARİŞ OXUMA ─────────────────────────────────────────────────────────

    def get_order(self, db: Session, order_id: int):
        return db.query(Order).filter(Order.id == order_id).first()

    def get_order_with_details(self, db: Session, order_id: int):
        return (
            db.query(Order)
            .options(
                joinedload(Order.table),
                joinedload(Order.waiter),
                selectinload(Order.items).joinedload(OrderItem.menu_item),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_active_orders(self, db: Session):
        return db.query(Order).filter(
            Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
        ).order_by(desc(Order.created_at)).all()

    def get_today_orders(self, db: Session):
        today = date.today()
        return db.query(Order).filter(
            Order.created_at >= datetime.combine(today, datetime.min.time())
        ).order_by(desc(Order.created_at)).all()

    def get_orders_by_table(self, db: Session, table_id: int):
        return db.query(Order).filter(
            Order.table_id == table_id
        ).order_by(desc(Order.created_at)).all()

    # ── SİFARİŞ KALEMİ ƏLAVƏ ET ──────────────────────────────────────────────

    def add_item(self, db: Session, order_id: int, menu_item_id: int,
                 quantity: int = 1, notes: str = None):
        order = self.get_order(db, order_id)
        if not order:
            return False, "Sifariş tapılmadı."
        if order.status in [OrderStatus.paid, OrderStatus.cancelled]:
            return False, "Ödənilmiş və ya ləğv edilmiş sifarişə əlavə edilə bilməz."

        menu_item = db.query(MenuItem).filter(
            MenuItem.id == menu_item_id,
            MenuItem.is_active == True
        ).first()
        if not menu_item:
            return False, "Menyu məhsulu tapılmadı."

        existing = db.query(OrderItem).filter(
            OrderItem.order_id     == order_id,
            OrderItem.menu_item_id == menu_item_id,
            OrderItem.status.notin_([OrderStatus.cancelled])
        ).first()

        if existing:
            existing.quantity += quantity
            existing.subtotal  = existing.quantity * existing.unit_price
        else:
            oi = OrderItem(
                order_id     = order_id,
                menu_item_id = menu_item_id,
                quantity     = quantity,
                unit_price   = menu_item.price,
                subtotal     = menu_item.price * quantity,
                notes        = notes,
            )
            db.add(oi)
            # ── FIX: yeni item DB-ə flush et ki _recalculate onu görsün ──
            db.flush()

        self._recalculate(db, order)
        db.commit()
        # ── FIX: commit sonra order Python obyektini yenilə ──
        db.refresh(order)
        return True, order

    def remove_item(self, db: Session, order_item_id: int):
        oi = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
        if not oi:
            return False, "Tapılmadı."
        order = self.get_order(db, oi.order_id)
        db.delete(oi)
        self._recalculate(db, order)
        db.commit()
        db.refresh(order)
        return True, order

    def update_item_qty(self, db: Session, order_item_id: int, quantity: int):
        oi = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
        if not oi:
            return False, "Tapılmadı."
        if quantity <= 0:
            return self.remove_item(db, order_item_id)
        oi.quantity = quantity
        oi.subtotal = oi.unit_price * quantity
        self._recalculate(db, oi.order)
        db.commit()
        db.refresh(oi.order)
        return True, oi.order

    # ── STATUS ────────────────────────────────────────────────────────────────

    def update_status(self, db: Session, order_id: int, status: str):
        order = self.get_order(db, order_id)
        if not order:
            return False, "Tapılmadı."
        order.status = OrderStatus[status]
        if status == "paid":
            order.paid_at = datetime.now()
            if order.table:
                order.table.status = TableStatus.available
        db.commit()
        return True, order

    def cancel_order(self, db: Session, order_id: int, reason: str = None):
        order = self.get_order(db, order_id)
        if not order:
            return False, "Tapılmadı."
        if order.status == OrderStatus.paid:
            return False, "Ödənilmiş sifarişi ləğv etmək mümkün deyil."
        order.status = OrderStatus.cancelled
        if order.table:
            order.table.status = TableStatus.available
        db.commit()
        return True, "Sifariş ləğv edildi."

    # ── ENDİRİM ───────────────────────────────────────────────────────────────

    def apply_discount(self, db: Session, order_id: int, discount_amount: float):
        order = self.get_order(db, order_id)
        if not order:
            return False, "Tapılmadı."
        order.discount_amount = discount_amount
        order.total = max(0, order.subtotal - discount_amount)
        db.commit()
        return True, order

    # ── HESABLAMA ─────────────────────────────────────────────────────────────

    def _recalculate(self, db: Session, order: Order):
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.status   != OrderStatus.cancelled
        ).all()
        subtotal = sum(i.subtotal for i in items)
        order.subtotal = subtotal
        order.total    = max(0, subtotal - (order.discount_amount or 0))

    # ── STATİSTİKA ────────────────────────────────────────────────────────────

    def get_today_summary(self, db: Session):
        orders = self.get_today_orders(db)
        paid   = [o for o in orders if o.status == OrderStatus.paid]
        return {
            "total_orders":  len(orders),
            "paid_orders":   len(paid),
            "total_revenue": sum(o.total for o in paid),
            "active_orders": len([o for o in orders
                                  if o.status not in [OrderStatus.paid, OrderStatus.cancelled]]),
        }


order_service = OrderService()
