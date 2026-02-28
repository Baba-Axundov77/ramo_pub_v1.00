# modules/menu/menu_service.py — Menyu İş Məntiqi
from sqlalchemy.orm import Session
from database.models import MenuCategory, MenuItem


class MenuService:

    # ── KATEQORİYALAR ─────────────────────────────────────────────────────────

    def get_categories(self, db: Session, active_only: bool = True):
        q = db.query(MenuCategory)
        if active_only:
            q = q.filter(MenuCategory.is_active == True)
        return q.order_by(MenuCategory.sort_order, MenuCategory.name).all()

    def create_category(self, db: Session, name: str, description: str = None,
                        icon: str = "🍽️", sort_order: int = 0):
        cat = MenuCategory(name=name, description=description,
                           icon=icon, sort_order=sort_order)
        db.add(cat); db.commit(); db.refresh(cat)
        return True, cat

    def update_category(self, db: Session, cat_id: int, **kwargs):
        cat = db.query(MenuCategory).filter(MenuCategory.id == cat_id).first()
        if not cat: return False, "Kateqoriya tapılmadı."
        for k, v in kwargs.items():
            if hasattr(cat, k): setattr(cat, k, v)
        db.commit(); return True, cat

    def delete_category(self, db: Session, cat_id: int):
        cat = db.query(MenuCategory).filter(MenuCategory.id == cat_id).first()
        if not cat: return False, "Kateqoriya tapılmadı."
        items = db.query(MenuItem).filter(
            MenuItem.category_id == cat_id,
            MenuItem.is_active == True
        ).count()
        if items > 0:
            return False, f"Bu kateqoriyada {items} aktiv məhsul var."
        cat.is_active = False; db.commit()
        return True, "Kateqoriya silindi."

    # ── MƏHSULLAR ─────────────────────────────────────────────────────────────

    def get_items(self, db: Session, category_id: int = None,
                  active_only: bool = True, available_only: bool = False):
        q = db.query(MenuItem)
        if active_only:
            q = q.filter(MenuItem.is_active == True)
        if available_only:
            q = q.filter(MenuItem.is_available == True)
        if category_id:
            q = q.filter(MenuItem.category_id == category_id)
        return q.order_by(MenuItem.name).all()

    def get_item(self, db: Session, item_id: int):
        return db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def create_item(self, db: Session, category_id: int, name: str, price: float,
                    description: str = None, cost_price: float = 0.0):
        item = MenuItem(category_id=category_id, name=name, price=price,
                        description=description, cost_price=cost_price)
        db.add(item); db.commit(); db.refresh(item)
        return True, item

    def update_item(self, db: Session, item_id: int, **kwargs):
        item = self.get_item(db, item_id)
        if not item: return False, "Məhsul tapılmadı."
        for k, v in kwargs.items():
            if hasattr(item, k): setattr(item, k, v)
        db.commit(); return True, item

    def toggle_available(self, db: Session, item_id: int):
        item = self.get_item(db, item_id)
        if not item: return False, "Tapılmadı."
        item.is_available = not item.is_available
        db.commit(); return True, item

    def delete_item(self, db: Session, item_id: int):
        item = self.get_item(db, item_id)
        if not item: return False, "Tapılmadı."
        item.is_active = False; db.commit()
        return True, "Məhsul silindi."

    def search(self, db: Session, query: str):
        return db.query(MenuItem).filter(
            MenuItem.is_active == True,
            MenuItem.name.ilike(f"%{query}%")
        ).all()

    # ── SEED ──────────────────────────────────────────────────────────────────

    def seed_defaults(self, db: Session):
        if db.query(MenuCategory).count() > 0:
            return
        defaults = [
            ("🍺", "Pivə & İçkilər", [
                ("Xırdalan Pivə",      3.50, 1.20),
                ("Efes Pilsner",       4.00, 1.50),
                ("Heineken",           5.00, 2.00),
                ("Çay (dəmli)",        2.00, 0.30),
                ("Türk Çayı",          2.50, 0.50),
                ("Limonad",            3.00, 0.80),
            ]),
            ("🍖", "Qəlyanaltılar", [
                ("Quzu qabırğası",    12.00, 4.00),
                ("Toyuq qanadları",    8.00, 2.50),
                ("Qızardılmış soğan",  4.00, 0.80),
                ("Pendirli kartof",    5.00, 1.20),
            ]),
            ("🥗", "Salatlar", [
                ("Yunan salatı",       7.00, 2.00),
                ("Cezar salatı",       8.00, 2.50),
                ("Mevsim salatı",      5.00, 1.20),
            ]),
            ("🍕", "Əsas Yeməklər", [
                ("Lamb chop",         18.00, 6.00),
                ("Burger",            12.00, 3.50),
                ("Lahmacun",           6.00, 1.50),
                ("Pide",               8.00, 2.00),
            ]),
            ("🍰", "Desertlər", [
                ("Baklava",            5.00, 1.20),
                ("Çokolad kek",        6.00, 1.80),
                ("Dondurma",           4.00, 1.00),
            ]),
        ]
        for icon, cat_name, items in defaults:
            cat = MenuCategory(name=cat_name, icon=icon)
            db.add(cat); db.flush()
            for item_name, price, cost in items:
                db.add(MenuItem(category_id=cat.id, name=item_name,
                                price=price, cost_price=cost))
        db.commit()


menu_service = MenuService()
