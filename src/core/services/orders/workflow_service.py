# modules/orders/workflow_service.py — Sifariş İş Akışı Servisi
from sqlalchemy.orm import Session
from datetime import datetime
from src.core.database.models import Order, OrderStatus, Table, TableStatus


class OrderWorkflowService:
    """Sifariş iş axını üçün servis"""
    
    def ensure_order_for_table(self, db: Session, table_id: int, waiter_id: int):
        """
        Masada aktiv sifariş yoxdursa yeni sifariş yaradır,
        varsa mövcud sifarişi qaytarır.
        
        Returns:
            tuple: (created: bool, result: dict)
        """
        try:
            # Masanın mövcudluğunu yoxla
            table = db.query(Table).filter(Table.id == table_id).first()
            if not table:
                return False, "Masa tapılmadı."
            
            # Aktiv sifarişi axtar
            existing_order = db.query(Order).filter(
                Order.table_id == table_id,
                Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
            ).first()
            
            if existing_order:
                # Mövcud sifariş var
                return False, {
                    "order": existing_order,
                    "created": False
                }
            
            # Yeni sifariş yarad
            new_order = Order(
                table_id=table_id,
                waiter_id=waiter_id,
                status=OrderStatus.new,
                created_at=datetime.utcnow()
            )
            
            db.add(new_order)
            
            # Masanın statusunu dəyiş
            table.status = TableStatus.occupied
            
            db.commit()
            db.refresh(new_order)
            
            return True, {
                "order": new_order,
                "created": True
            }
            
        except Exception as e:
            db.rollback()
            return False, f"Sifariş yaradılarkən xəta: {str(e)}"
    
    def get_active_order_for_table(self, db: Session, table_id: int):
        """Masadakı aktiv sifarişi tapır"""
        return db.query(Order).filter(
            Order.table_id == table_id,
            Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
        ).first()
    
    def can_create_order_for_table(self, db: Session, table_id: int):
        """Masada yeni sifariş yaradıla bilərmi?"""
        table = db.query(Table).filter(Table.id == table_id).first()
        if not table:
            return False, "Masa tapılmadı."
        
        if table.status == TableStatus.reserved:
            return False, "Rezerv olunmuş masaya sifariş yaradıla bilməz."
        
        # Aktiv sifarişi yoxla
        active_order = self.get_active_order_for_table(db, table_id)
        if active_order:
            return False, f"Masada artıq aktiv sifariş var (#{active_order.id})."
        
        return True, None


# Singleton instance
order_workflow_service = OrderWorkflowService()
