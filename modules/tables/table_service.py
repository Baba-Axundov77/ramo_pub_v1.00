# modules/tables/table_service.py — Masa İş Məntiqi
from sqlalchemy.orm import Session
from database.models import Table, TableStatus, Order, OrderStatus


class TableService:

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get_all(self, db: Session):
        return db.query(Table).filter(Table.is_active == True).order_by(Table.number).all()

    def get_by_id(self, db: Session, table_id: int):
        return db.query(Table).filter(Table.id == table_id).first()

    def create(self, db: Session, number: int, name: str = None,
               capacity: int = 4, floor: int = 1):
        existing = db.query(Table).filter(Table.number == number).first()
        if existing:
            return False, f"Masa #{number} artıq mövcuddur."
        table = Table(number=number, name=name or f"Masa {number}",
                      capacity=capacity, floor=floor)
        db.add(table)
        db.commit()
        db.refresh(table)
        return True, table

    def update(self, db: Session, table_id: int, **kwargs):
        table = self.get_by_id(db, table_id)
        if not table:
            return False, "Masa tapılmadı."
        for k, v in kwargs.items():
            if hasattr(table, k):
                setattr(table, k, v)
        db.commit()
        return True, table

    def delete(self, db: Session, table_id: int):
        table = self.get_by_id(db, table_id)
        if not table:
            return False, "Masa tapılmadı."
        active = db.query(Order).filter(
            Order.table_id == table_id,
            Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
        ).first()
        if active:
            return False, "Bu masada aktiv sifariş var, silinə bilməz."
        table.is_active = False
        db.commit()
        return True, "Masa silindi."

    # ── Status ────────────────────────────────────────────────────────────────

    def set_status(self, db: Session, table_id: int, status: str):
        table = self.get_by_id(db, table_id)
        if not table:
            return False, "Masa tapılmadı."
        table.status = TableStatus[status]
        db.commit()
        return True, table

    def get_active_order(self, db: Session, table_id: int):
        """Masanın aktiv sifarişini qaytar."""
        return db.query(Order).filter(
            Order.table_id == table_id,
            Order.status.notin_([OrderStatus.paid, OrderStatus.cancelled])
        ).order_by(Order.created_at.desc()).first()

    # ── Statistika ────────────────────────────────────────────────────────────

    def get_stats(self, db: Session):
        tables = self.get_all(db)
        total     = len(tables)
        available = sum(1 for t in tables if t.status == TableStatus.available)
        occupied  = sum(1 for t in tables if t.status == TableStatus.occupied)
        reserved  = sum(1 for t in tables if t.status == TableStatus.reserved)
        cleaning  = sum(1 for t in tables if t.status == TableStatus.cleaning)
        return {"total": total, "available": available,
                "occupied": occupied, "reserved": reserved,
                "cleaning": cleaning}

    def seed_defaults(self, db: Session, count: int = 12):
        """İlk işə salma üçün default masalar yarat."""
        existing = db.query(Table).count()
        if existing > 0:
            return
        for i in range(1, count + 1):
            floor = 2 if i > 8 else 1
            db.add(Table(number=i, name=f"Masa {i}", capacity=4, floor=floor))
        db.commit()


table_service = TableService()
