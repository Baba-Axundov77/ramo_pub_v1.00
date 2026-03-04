from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import MenuCategory, MenuItem, InventoryItem, MenuItemRecipe
from modules.menu.menu_service import MenuService


def test_replace_recipes_deactivates_old_versions(tmp_path):
    db_path = tmp_path / "recipe_version.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    svc = MenuService()
    with SessionLocal() as db:
        cat = MenuCategory(name="Test", icon="🍽️")
        inv1 = InventoryItem(name="Çay", unit="qram", quantity=1000)
        inv2 = InventoryItem(name="Kəklik", unit="qram", quantity=500)
        db.add_all([cat, inv1, inv2]); db.flush()
        item = MenuItem(category_id=cat.id, name="Çaynik", price=5)
        db.add(item); db.commit(); db.refresh(item)

        svc.replace_recipes(db, item.id, [{"inventory_item_id": inv1.id, "quantity_per_unit": 10}])
        svc.replace_recipes(db, item.id, [{"inventory_item_id": inv2.id, "quantity_per_unit": 2}])

        active = db.query(MenuItemRecipe).filter(MenuItemRecipe.menu_item_id == item.id, MenuItemRecipe.is_active == True).all()
        all_rows = db.query(MenuItemRecipe).filter(MenuItemRecipe.menu_item_id == item.id).all()

        assert len(active) == 1
        assert active[0].inventory_item_id == inv2.id
        assert len(all_rows) == 2
