from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import InventoryItem, PurchaseReceipt, PurchaseReceiptItem


class InventoryService:
    def seed_defaults(self, db: Session) -> None:
        """Boş anbar üçün ilkin stok məhsulları əlavə et."""
        if db.query(InventoryItem).first() is not None:
            return

        defaults = [
            ("Çay", "qram", 3000.0, 500.0, 0.02, "Lokal Təchizat"),
            ("Qəhvə", "qram", 2000.0, 400.0, 0.06, "Coffee Supplier"),
            ("Şəkər", "kq", 20.0, 5.0, 1.2, "Market"),
            ("Cola 330ml", "ədəd", 48.0, 12.0, 1.4, "Drink Distributor"),
        ]
        for name, unit, quantity, min_quantity, cost_per_unit, supplier in defaults:
            db.add(
                InventoryItem(
                    name=name,
                    unit=unit,
                    quantity=quantity,
                    min_quantity=min_quantity,
                    cost_per_unit=cost_per_unit,
                    supplier=supplier,
                )
            )
        db.commit()

    def get_all(self, db: Session, low_stock_only: bool = False) -> List[InventoryItem]:
        q = db.query(InventoryItem)
        if low_stock_only:
            q = q.filter(InventoryItem.quantity <= InventoryItem.min_quantity)
        return q.order_by(InventoryItem.name).all()

    def get_by_id(self, db: Session, item_id: int) -> Optional[InventoryItem]:
        return db.query(InventoryItem).filter(InventoryItem.id == item_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[InventoryItem]:
        return db.query(InventoryItem).filter(func.lower(InventoryItem.name) == name.strip().lower()).first()

    def create(self, db: Session, name: str, unit: str, quantity: float,
               min_quantity: float = 5.0, cost_per_unit: float = 0.0,
               supplier: str = "") -> Tuple[bool, object]:
        item = InventoryItem(name=name, unit=unit, quantity=quantity, min_quantity=min_quantity,
                             cost_per_unit=cost_per_unit, supplier=supplier)
        db.add(item); db.commit(); db.refresh(item)
        return True, item

    def update(self, db: Session, item_id: int, **kwargs) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Stok mehsulu tapilmadi."
        for k, v in kwargs.items():
            if hasattr(item, k):
                setattr(item, k, v)
        db.commit(); return True, item

    def add_stock(self, db: Session, item_id: int, amount: float) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        if amount <= 0:
            return False, "Miqdar musbet olmalidir."
        item.quantity += amount
        db.commit(); return True, item

    def remove_stock(self, db: Session, item_id: int, amount: float) -> Tuple[bool, object]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        if amount <= 0:
            return False, "Miqdar musbet olmalidir."
        if item.quantity < amount:
            return False, f"Kifayet qeder stok yoxdur. Movcud: {item.quantity} {item.unit}"
        item.quantity -= amount
        db.commit(); return True, item

    def delete(self, db: Session, item_id: int) -> Tuple[bool, str]:
        item = self.get_by_id(db, item_id)
        if not item:
            return False, "Tapilmadi."
        db.delete(item); db.commit()
        return True, "Stok mehsulu silindi."

    def create_purchase_receipt(self, db: Session, *, purchased_at: datetime, store_name: str, note: str, created_by: int | None, lines: list[dict]):
        if not lines:
            return False, "Çek üçün ən azı 1 məhsul olmalıdır."
        receipt = PurchaseReceipt(purchased_at=purchased_at, store_name=store_name or None, note=note or None, total_amount=0.0, created_by=created_by)
        db.add(receipt)
        total = 0.0
        for line in lines:
            name = (line.get("name") or "").strip()
            if not name:
                continue
            qty = float(line.get("quantity") or 0)
            unit_cost = float(line.get("unit_cost") or 0)
            unit = (line.get("unit") or "ədəd").strip()
            if qty <= 0:
                continue
            inv = self.get_by_name(db, name)
            if not inv:
                inv = InventoryItem(name=name, unit=unit, quantity=0.0, cost_per_unit=unit_cost)
                db.add(inv)
                db.flush()
            inv.quantity += qty
            inv.cost_per_unit = unit_cost
            if not inv.unit:
                inv.unit = unit
            line_total = qty * unit_cost
            total += line_total
            db.add(PurchaseReceiptItem(receipt=receipt, inventory_item_id=inv.id, item_name=name, unit=unit, quantity=qty, unit_cost=unit_cost, line_total=line_total))
        receipt.total_amount = total
        db.commit(); db.refresh(receipt)
        return True, receipt

    def list_purchase_receipts(self, db: Session, limit: int = 100):
        return db.query(PurchaseReceipt).order_by(PurchaseReceipt.purchased_at.desc(), PurchaseReceipt.id.desc()).limit(limit).all()

    def get_purchase_receipt(self, db: Session, receipt_id: int):
        return db.query(PurchaseReceipt).filter(PurchaseReceipt.id == receipt_id).first()

    def delete_purchase_receipt(self, db: Session, receipt_id: int):
        receipt = self.get_purchase_receipt(db, receipt_id)
        if not receipt:
            return False, "Çek tapılmadı"
        for it in receipt.items:
            inv = it.inventory_item
            if inv:
                inv.quantity = max(0.0, (inv.quantity or 0.0) - float(it.quantity or 0.0))
        db.delete(receipt)
        db.commit()
        return True, "Çek silindi və stok geri alındı"

    def get_low_stock_count(self, db: Session) -> int:
        return db.query(InventoryItem).filter(InventoryItem.quantity <= InventoryItem.min_quantity).count()

    def get_total_value(self, db: Session) -> float:
        items = self.get_all(db)
        return sum(i.quantity * i.cost_per_unit for i in items)


inventory_service = InventoryService()
