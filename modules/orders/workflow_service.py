from __future__ import annotations

from datetime import date, datetime
from sqlalchemy.orm import Session

from database.models import Order, OrderStatus, Table, TableStatus


class OrderWorkflowService:
    """Shared table→order workflow for both Web and Desktop."""

    ACTIVE_STATUSES = {
        OrderStatus.new,
        OrderStatus.preparing,
        OrderStatus.ready,
        OrderStatus.served,
    }

    def get_active_order_for_table(self, db: Session, table_id: int):
        return (
            db.query(Order)
            .filter(
                Order.table_id == table_id,
                Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled]),
            )
            .order_by(Order.created_at.desc())
            .first()
        )

    def ensure_order_for_table(self, db: Session, table_id: int, waiter_id: int):
        """
        Pro flow:
        - if table has active order => open it
        - else create order bound to table
        Returns: (ok, {order, created, table}) | (False, msg)
        """
        table = db.query(Table).filter(Table.id == table_id, Table.is_active == True).first()
        if not table:
            return False, "Masa tapılmadı və ya deaktivdir."

        if waiter_id is None or int(waiter_id) <= 0:
            return False, "İstifadəçi identifikasiyası yanlışdır."

        if table.status == TableStatus.cleaning:
            return False, "Masa təmizlikdədir. Əvvəlcə statusu dəyişin."

        existing = self.get_active_order_for_table(db, table_id)
        if existing:
            return True, {"order": existing, "created": False, "table": table}

        order = Order(
            table_id=table_id,
            waiter_id=int(waiter_id),
            status=OrderStatus.new,
        )
        db.add(order)
        table.status = TableStatus.occupied
        db.commit()
        db.refresh(order)
        return True, {"order": order, "created": True, "table": table}

    def validate_order_context(self, db: Session, order_id: int, table_id: int | None):
        """Prevent cross-table order opening by URL tampering."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return False, "Sifariş tapılmadı.", None

        if table_id and order.table_id != table_id:
            return False, "Sifariş seçilən masaya aid deyil.", None

        return True, "ok", order

    def get_completed_orders(self, db: Session, table_id: int | None = None, only_today: bool = True):
        q = db.query(Order).filter(Order.status.in_([OrderStatus.paid, OrderStatus.cancelled]))
        if only_today:
            today = date.today()
            q = q.filter(Order.created_at >= datetime.combine(today, datetime.min.time()))
        if table_id:
            q = q.filter(Order.table_id == table_id)
        return q.order_by(Order.created_at.desc()).all()


order_workflow_service = OrderWorkflowService()
