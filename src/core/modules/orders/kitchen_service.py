from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.core.database.models import Order, OrderItem, OrderStatus


class KitchenService:
    """Mətbəx (KDS) üçün sifariş axını servis qatı."""

    def get_queue(self, db: Session) -> list[Order]:
        return (
            db.query(Order)
            .filter(Order.status.in_([OrderStatus.new, OrderStatus.preparing]))
            .order_by(Order.created_at.asc())
            .all()
        )

    def mark_preparing(self, db: Session, order_id: int) -> tuple[bool, Any]:
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, "Sifariş tapılmadı."
            if order.status in [OrderStatus.paid, OrderStatus.cancelled]:
                return False, "Bu sifariş mətbəx üçün aktiv deyil."

            order.status = OrderStatus.preparing
            now = datetime.now()
            for item in order.items:
                if item.status == OrderStatus.new:
                    item.status = OrderStatus.preparing
                    if hasattr(item, "sent_to_kitchen_at") and not item.sent_to_kitchen_at:
                        item.sent_to_kitchen_at = now
            db.commit()
            return True, order
        except Exception as e:
            db.rollback()
            return False, f"Sifariş hazırlığa alınarkən xəta: {str(e)}"

    def mark_ready(self, db: Session, order_id: int) -> tuple[bool, Any]:
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, "Sifariş tapılmadı."
            if order.status in [OrderStatus.paid, OrderStatus.cancelled]:
                return False, "Bu sifariş mətbəx üçün aktiv deyil."

            order.status = OrderStatus.ready
            for item in order.items:
                if item.status not in [OrderStatus.cancelled]:
                    item.status = OrderStatus.ready
            db.commit()
            return True, order
        except Exception as e:
            db.rollback()
            return False, f"Sifariş hazır olaraq qeyd edilərkən xəta: {str(e)}"

    def bump_item_ready(self, db: Session, item_id: int) -> tuple[bool, Any]:
        try:
            item = db.query(OrderItem).filter(OrderItem.id == item_id).first()
            if not item:
                return False, "Məhsul tapılmadı."
            if item.status == OrderStatus.cancelled:
                return False, "Ləğv edilmiş məhsul hazır edilə bilməz."

            item.status = OrderStatus.ready
            if item.order and all(i.status in [OrderStatus.ready, OrderStatus.cancelled] for i in item.order.items):
                item.order.status = OrderStatus.ready
            db.commit()
            return True, item
        except Exception as e:
            db.rollback()
            return False, f"Məhsul hazır olaraq qeyd edilərkən xəta: {str(e)}"


kitchen_service = KitchenService()
