from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database.connection import Base
from src.core.database.models import User, UserRole
from src.core.modules.auth.auth_service import AuthService
import web.app as web_app_module


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.sqlite3"
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
        user = User(
            username=username,
            full_name=username,
            password=AuthService.hash_password("pass123"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()


def test_staff_route_requires_admin(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "waiter1", UserRole.waiter)

    resp = c.post("/auth/login", data={"username": "waiter1", "password": "pass123"}, follow_redirects=True)
    assert resp.status_code == 200

    denied = c.get("/staff/", follow_redirects=True)
    assert denied.status_code == 200
    assert b"icaz" in denied.data.lower()


def test_staff_route_accessible_for_admin(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "admin1", UserRole.admin)

    c.post("/auth/login", data={"username": "admin1", "password": "pass123"}, follow_redirects=True)
    ok = c.get("/staff/", follow_redirects=True)
    assert ok.status_code == 200
    assert b"I\xc5\x9f\xc3\xa7" in ok.data or b"staff" in ok.data.lower()


def test_tables_mutation_denied_for_cashier(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "cash1", UserRole.cashier)

    c.post("/auth/login", data={"username": "cash1", "password": "pass123"}, follow_redirects=True)
    denied = c.post("/tables/api/status/1", json={"status": "cleaning"})
    assert denied.status_code == 403
    data = denied.get_json()
    assert data and data.get("ok") is False


def test_kitchen_page_access_for_kitchen_role(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "kitchen1", UserRole.kitchen)

    c.post("/auth/login", data={"username": "kitchen1", "password": "pass123"}, follow_redirects=True)
    ok = c.get("/kitchen/", follow_redirects=True)
    assert ok.status_code == 200
    assert b"kitchen" in ok.data.lower() or b"queue" in ok.data.lower()


def test_kitchen_page_denied_for_waiter(client):
    c, SessionLocal = client
    _seed_user(SessionLocal, "waitx", UserRole.waiter)

    c.post("/auth/login", data={"username": "waitx", "password": "pass123"}, follow_redirects=True)
    denied = c.get("/kitchen/", follow_redirects=True)
    assert denied.status_code == 200
    assert b"icaz" in denied.data.lower()
