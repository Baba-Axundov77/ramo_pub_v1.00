from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.core.database.connection import Base
from src.core.database.models import User, UserRole, MenuCategory, MenuItem, Table, TableStatus, Order, InventoryItem
from src.core.modules.auth.auth_service import AuthService
import web.app as web_app_module


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test_s3.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def get_test_db():
        return SessionLocal()

    monkeypatch.setattr(web_app_module, "get_db", get_test_db)
    app = web_app_module.create_app({"TESTING": True, "SECRET_KEY": "test"})

    with app.test_client() as c:
        yield c, SessionLocal


def _seed_user(SessionLocal, username: str, role: UserRole):
    with SessionLocal() as db:
        db.add(User(username=username, full_name=username, password=AuthService.hash_password("pass123"), role=role, is_active=True))
        db.commit()


def test_menu_edit_category_and_item(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "managerx", UserRole.manager)
    c.post("/auth/login", data={"username": "managerx", "password": "pass123"}, follow_redirects=True)
    with SessionLocal() as db:
        cat = MenuCategory(name="Old", icon="🍽️")
        db.add(cat); db.flush()
        item = MenuItem(category_id=cat.id, name="Cola", price=2.0)
        db.add(item); db.commit()
        cat_id, item_id = cat.id, item.id

    c.post(f"/menu/categories/{cat_id}/edit", data={"name": "New", "icon": "🥤", "description": "d", "sort_order": 3}, follow_redirects=True)
    c.post(f"/menu/items/{item_id}/edit", data={"category_id": cat_id, "name": "Cola XL", "price": 3.5, "cost_price": 1.2, "is_available": "1", "stock_name": "Cola 1lt", "stock_unit": "ədəd"}, follow_redirects=True)

    with SessionLocal() as db:
        assert db.get(MenuCategory, cat_id).name == "New"
        edited = db.get(MenuItem, item_id)
        assert edited.name == "Cola XL"
        assert edited.inventory_item_id is not None


def test_reserved_arrived_creates_order(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "manager2", UserRole.manager)
    c.post("/auth/login", data={"username": "manager2", "password": "pass123"}, follow_redirects=True)
    with SessionLocal() as db:
        t = Table(number=99, name="M99", status=TableStatus.reserved)
        db.add(t); db.commit(); tid = t.id

    res = c.post(f"/tables/api/create-order/{tid}")
    assert res.status_code in (201, 409)
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.table_id == tid).first()
        assert order is not None


def test_purchase_receipt_updates_and_rollbacks_stock(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "adminx", UserRole.admin)
    c.post("/auth/login", data={"username": "adminx", "password": "pass123"}, follow_redirects=True)

    c.post("/inventory/receipt/create", data={
        "store_name": "Market", "note": "bulk",
        "line_name[]": ["Soğan", "Cola 1lt"],
        "line_qty[]": ["2", "5"],
        "line_unit[]": ["kq", "ədəd"],
        "line_cost[]": ["1.8", "1.4"],
    }, follow_redirects=True)

    with SessionLocal() as db:
        onion = db.query(InventoryItem).filter(InventoryItem.name == "Soğan").first()
        assert onion and onion.quantity == 2
        receipt = db.execute(text("select id from purchase_receipts limit 1")).fetchone()
        assert receipt is not None
        rid = int(receipt[0])

    c.post(f"/inventory/receipt/{rid}/delete", follow_redirects=True)
    with SessionLocal() as db:
        onion = db.query(InventoryItem).filter(InventoryItem.name == "Soğan").first()
        assert onion and onion.quantity == 0
