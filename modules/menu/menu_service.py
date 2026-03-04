from datetime import date
from typing import Optional, List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import MenuCategory, MenuItem, InventoryItem, MenuItemRecipe


class MenuService:
    def seed_defaults(self, db: Session) -> None:
        """Boş sistem üçün minimal default menyu məlumatları yarat."""
        has_active_category = (
            db.query(MenuCategory)
            .filter(MenuCategory.is_active == True)
            .first()
            is not None
        )
        if has_active_category:
            return

        defaults = [
            {
                "name": "İsti İçkilər",
                "icon": "☕",
                "items": [
                    ("Çay", 1.5, "Qara çay"),
                    ("Amerikano", 4.0, "Klassik qəhvə"),
                ],
            },
            {
                "name": "Sərinləşdirici",
                "icon": "🥤",
                "items": [
                    ("Cola", 3.0, "330ml"),
                    ("Mineral Su", 1.0, "500ml"),
                ],
            },
            {
                "name": "Qəlyanaltı",
                "icon": "🍟",
                "items": [
                    ("Kartof Fri", 5.0, "Xırt-xırt"),
                    ("Nuggets", 6.5, "6 ədəd"),
                ],
            },
        ]

        for sort_order, category_data in enumerate(defaults, start=1):
            category = MenuCategory(
                name=category_data["name"],
                icon=category_data["icon"],
                sort_order=sort_order,
                is_active=True,
            )
            db.add(category)
            db.flush()

            for item_order, (item_name, price, description) in enumerate(category_data["items"], start=1):
                db.add(
                    MenuItem(
                        category_id=category.id,
                        name=item_name,
                        price=price,
                        description=description,
                        sort_order=item_order,
                        is_available=True,
                        is_active=True,
                    )
                )
        db.commit()

    def get_categories(self, db: Session, active_only: bool = True):
        q = db.query(MenuCategory)
        if active_only:
            q = q.filter(MenuCategory.is_active == True)
        return q.order_by(MenuCategory.sort_order, MenuCategory.name).all()

    def create_category(self, db: Session, name: str, description: str = None,
                        icon: str = "🍽️", sort_order: int = 0):
        cat = MenuCategory(name=name, description=description, icon=icon, sort_order=sort_order)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return True, cat

    def update_category(self, db: Session, cat_id: int, **kwargs):
        cat = db.query(MenuCategory).filter(MenuCategory.id == cat_id).first()
        if not cat:
            return False, "Kateqoriya tapılmadı."
        for k, v in kwargs.items():
            if hasattr(cat, k):
                setattr(cat, k, v)
        db.commit()
        db.refresh(cat)
        return True, cat

    def delete_category(self, db: Session, cat_id: int):
        cat = db.query(MenuCategory).filter(MenuCategory.id == cat_id).first()
        if not cat:
            return False, "Kateqoriya tapılmadı."
        items = db.query(MenuItem).filter(MenuItem.category_id == cat_id, MenuItem.is_active == True).count()
        if items > 0:
            return False, f"Bu kateqoriyada {items} aktiv məhsul var."
        cat.is_active = False
        db.commit()
        return True, "Kateqoriya silindi."

    def get_items(self, db: Session, category_id: int = None, active_only: bool = True, available_only: bool = False):
        q = db.query(MenuItem)
        if active_only:
            q = q.filter(MenuItem.is_active == True)
        if available_only:
            q = q.filter(MenuItem.is_available == True)
        if category_id:
            q = q.filter(MenuItem.category_id == category_id)
        return q.order_by(MenuItem.sort_order, MenuItem.name).all()

    def get_item(self, db: Session, item_id: int):
        return db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def _find_or_create_inventory_item(self, db: Session, stock_name: str, unit: str, cost_price: float):
        normalized = stock_name.strip().lower()
        item = db.query(InventoryItem).filter(func.lower(InventoryItem.name) == normalized).first()
        if item:
            if unit and not item.unit:
                item.unit = unit
            if cost_price and (item.cost_per_unit or 0) <= 0:
                item.cost_per_unit = cost_price
            return item
        item = InventoryItem(name=stock_name.strip(), unit=unit or "ədəd", quantity=0.0, cost_per_unit=cost_price or 0.0)
        db.add(item)
        db.flush()
        return item

    def create_item(self, db: Session, category_id: int, name: str, price: float,
                    description: str = None, cost_price: float = 0.0, image_path: str = None,
                    inventory_item_id: int | None = None, stock_name: str | None = None,
                    stock_unit: str | None = None, stock_usage_qty: float = 0.0,
                    sort_order: int = 0, recipe_lines: list[dict] | None = None):
        inv_id = inventory_item_id
        if stock_name and stock_name.strip():
            inv = self._find_or_create_inventory_item(db, stock_name, stock_unit or "ədəd", cost_price)
            inv_id = inv.id

        item = MenuItem(
            category_id=category_id,
            name=name,
            price=price,
            description=description,
            cost_price=cost_price,
            image_path=(image_path or None),
            inventory_item_id=inv_id,
            sort_order=sort_order or 0,
            stock_usage_qty=max(0.0, float(stock_usage_qty or 0.0)),
        )
        db.add(item)
        db.flush()

        if recipe_lines is not None:
            self.replace_recipes(db, item.id, recipe_lines)
        else:
            db.commit()
        db.refresh(item)
        return True, item

    def update_item(self, db: Session, item_id: int, **kwargs):
        item = self.get_item(db, item_id)
        if not item:
            return False, "Məhsul tapılmadı."

        stock_name = kwargs.pop("stock_name", None)
        stock_unit = kwargs.pop("stock_unit", None)
        recipe_lines = kwargs.pop("recipe_lines", None)
        if stock_name and stock_name.strip():
            inv = self._find_or_create_inventory_item(
                db,
                stock_name,
                stock_unit or "ədəd",
                kwargs.get("cost_price", item.cost_price or 0),
            )
            kwargs["inventory_item_id"] = inv.id

        if "stock_usage_qty" in kwargs:
            kwargs["stock_usage_qty"] = max(0.0, float(kwargs.get("stock_usage_qty") or 0.0))

        for k, v in kwargs.items():
            if hasattr(item, k):
                setattr(item, k, v)

        if recipe_lines is not None:
            self.replace_recipes(db, item.id, recipe_lines)
        else:
            db.commit()
        db.refresh(item)
        return True, item

    def get_item_recipes(self, db: Session, menu_item_id: int):
        today = date.today()
        return (
            db.query(MenuItemRecipe)
            .filter(MenuItemRecipe.menu_item_id == menu_item_id, MenuItemRecipe.is_active == True)
            .filter((MenuItemRecipe.valid_from == None) | (MenuItemRecipe.valid_from <= today))
            .filter((MenuItemRecipe.valid_until == None) | (MenuItemRecipe.valid_until >= today))
            .all()
        )

    def replace_recipes(self, db: Session, menu_item_id: int, recipe_lines: list[dict]):
        today = date.today()
        active_rows = db.query(MenuItemRecipe).filter(
            MenuItemRecipe.menu_item_id == menu_item_id,
            MenuItemRecipe.is_active == True,
        ).all()
        for row in active_rows:
            row.is_active = False
            row.valid_until = today

        for line in recipe_lines or []:
            inv_id = int(line.get("inventory_item_id") or 0)
            qty = float(line.get("quantity_per_unit") or 0)
            qty_unit = (line.get("quantity_unit") or "").strip() or None
            if inv_id <= 0 or qty <= 0:
                continue
            db.add(
                MenuItemRecipe(
                    menu_item_id=menu_item_id,
                    inventory_item_id=inv_id,
                    quantity_per_unit=qty,
                    quantity_unit=qty_unit,
                    valid_from=today,
                    is_active=True,
                )
            )
        db.commit()

    def toggle_available(self, db: Session, item_id: int):
        item = self.get_item(db, item_id)
        if not item:
            return False, "Tapılmadı."
        item.is_available = not item.is_available
        db.commit()
        return True, item

    def delete_item(self, db: Session, item_id: int):
        item = self.get_item(db, item_id)
        if not item:
            return False, "Tapılmadı."
        item.is_active = False
        db.commit()
        return True, "Məhsul silindi."


menu_service = MenuService()
