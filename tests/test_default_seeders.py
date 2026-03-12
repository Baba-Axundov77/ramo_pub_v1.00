from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database.connection import Base
from src.core.database.models import MenuCategory, MenuItem, InventoryItem
from src.core.modules.inventory.inventory_service import InventoryService
from src.core.modules.menu.menu_service import MenuService


def test_menu_seed_defaults_creates_data_once(tmp_path):
    db_path = tmp_path / "seed_menu.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    svc = MenuService()
    with SessionLocal() as db:
        svc.seed_defaults(db)
        first_cat_count = db.query(MenuCategory).count()
        first_item_count = db.query(MenuItem).count()
        assert first_cat_count > 0
        assert first_item_count > 0

        svc.seed_defaults(db)
        assert db.query(MenuCategory).count() == first_cat_count
        assert db.query(MenuItem).count() == first_item_count


def test_inventory_seed_defaults_creates_data_once(tmp_path):
    db_path = tmp_path / "seed_inventory.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    svc = InventoryService()
    with SessionLocal() as db:
        svc.seed_defaults(db)
        first_count = db.query(InventoryItem).count()
        assert first_count > 0

        svc.seed_defaults(db)
        assert db.query(InventoryItem).count() == first_count
