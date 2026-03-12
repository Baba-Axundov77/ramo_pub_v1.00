from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database.connection import Base
from src.core.database.models import User, UserRole, MenuCategory, MenuItem
from src.core.modules.auth.auth_service import AuthService
import web.app as web_app_module


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test_menu.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def get_test_db():
        return TestingSessionLocal()

    monkeypatch.setattr(web_app_module, "get_db", get_test_db)
    app = web_app_module.create_app({"TESTING": True, "SECRET_KEY": "test"})

    with app.test_client() as c:
        yield c, TestingSessionLocal


def _seed_user(SessionLocal, username: str, role: UserRole):
    with SessionLocal() as db:
        db.add(
            User(
                username=username,
                full_name=username,
                password=AuthService.hash_password("pass123"),
                role=role,
                is_active=True,
            )
        )
        db.commit()


def test_menu_create_category_and_item_for_manager(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "manager1", UserRole.manager)

    c.post("/auth/login", data={"username": "manager1", "password": "pass123"}, follow_redirects=True)

    resp_cat = c.post(
        "/menu/categories/create",
        data={"name": "Test Cat", "icon": "🍽️", "sort_order": 1},
        follow_redirects=True,
    )
    assert resp_cat.status_code == 200

    with SessionLocal() as db:
        cat = db.query(MenuCategory).filter(MenuCategory.name == "Test Cat").first()
        assert cat is not None
        cat_id = cat.id

    resp_item = c.post(
        "/menu/items/create",
        data={"category_id": cat_id, "name": "Soup", "price": 5.5, "cost_price": 2.1},
        follow_redirects=True,
    )
    assert resp_item.status_code == 200

    with SessionLocal() as db:
        item = db.query(MenuItem).filter(MenuItem.name == "Soup").first()
        assert item is not None


def test_menu_create_denied_for_waiter(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "waiter2", UserRole.waiter)

    c.post("/auth/login", data={"username": "waiter2", "password": "pass123"}, follow_redirects=True)

    denied = c.post("/menu/categories/create", data={"name": "Blocked"}, follow_redirects=True)
    assert denied.status_code == 200
    assert b"icaz" in denied.data.lower()
