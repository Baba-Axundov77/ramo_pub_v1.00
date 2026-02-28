# modules/inventory/inventory_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from database.models import InventoryItem


class InventoryService:

    def get_all(self, db: Session, low_stock_only: bool = False) -> List[InventoryItem]:
        q = db.query(InventoryItem)
        if low_stock_only:
            q = q.filter(InventoryItem.quantity <= InventoryItem.min_quantity)
        return q.order_by(InventoryItem.name).all()

    def get_by_id(self, db: Session, item_id: int) -> Optional[InventoryItem]:
        return db.query(InventoryItem).filter(InventoryItem.id == item_id).first()

    def create(self, db: Session, name: str, unit: str, quantity: float,
               min_quantity: float = 5.0, cost_per_unit: float = 0.0,
               supplier: str = "") -> Tuple[bool, object]:
        item = InventoryItem(
            name=name, unit=unit, quantity=quantity,
            min_quantity=min_quantity, cost_per_unit=cost_per_unit,
            supplier=supplier,
        )
        db.add(item); db.commit(); db.refresh(item)
        return True, item

    def update(self, db: Session, item_id: int, **kwargs) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Stok mehsulu tapilmadi."
        for k, v in kwargs.items():
            if hasattr(item, k):
                setattr(item, k, v)
        db.commit()
        return True, item

    def add_stock(self, db: Session, item_id: int, amount: float) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        if amount <= 0:
            return False, "Miqdar musbet olmalidir."
        item.quantity += amount
        db.commit()
        return True, item

    def remove_stock(self, db: Session, item_id: int, amount: float) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        if amount <= 0:
            return False, "Miqdar musbet olmalidir."
        if item.quantity < amount:
            return False, f"Kifayet qeder stok yoxdur. Movcud: {item.quantity} {item.unit}"
        item.quantity -= amount
        db.commit()
        return True, item

    def delete(self, db: Session, item_id: int) -> Tuple[bool, str]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        db.delete(item); db.commit()
        return True, "Stok mehsulu silindi."

    def get_low_stock_count(self, db: Session) -> int:
        return db.query(InventoryItem).filter(
            InventoryItem.quantity <= InventoryItem.min_quantity
        ).count()

    def get_total_value(self, db: Session) -> float:
        items = self.get_all(db)
        return sum(i.quantity * i.cost_per_unit for i in items)

    def seed_defaults(self, db: Session) -> None:
        if db.query(InventoryItem).count() > 0:
            return
        defaults = [
            ("Pive (litr)",        "litr",  50.0,  10.0, 1.80, "Azerbaycan Pive"),
            ("Cay (qr)",           "qr",   500.0, 100.0, 0.05, "Cay Idxalcisi"),
            ("Seqer (kq)",         "kq",    10.0,   2.0, 0.80, "Lokal Bazari"),
            ("Quzu eti (kq)",      "kq",    15.0,   5.0, 8.50, "Et Fabriki"),
            ("Toyuq (kq)",         "kq",    20.0,   5.0, 4.20, "Et Fabriki"),
            ("Kartof (kq)",        "kq",    30.0,  10.0, 0.40, "Lokal Bazari"),
            ("Sogan (kq)",         "kq",    10.0,   3.0, 0.30, "Lokal Bazari"),
            ("Bitki yaqi (litr)",  "litr",   5.0,   2.0, 2.50, "Market"),
            ("Un (kq)",            "kq",    20.0,   5.0, 0.60, "Lokal Bazari"),
            ("Limonad (litr)",     "litr",  10.0,   3.0, 0.90, "Icki Sirketi"),
        ]
        for name, unit, qty, min_qty, cost, supplier in defaults:
            db.add(InventoryItem(
                name=name, unit=unit, quantity=qty,
                min_quantity=min_qty, cost_per_unit=cost, supplier=supplier
            ))
        db.commit()


inventory_service = InventoryService()
