from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import (
    InventoryItem,
    MenuCategory,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Table,
    TableStatus,
    User,
    UserRole,
)
from modules.auth.auth_service import AuthService
from modules.pos.pos_service import POSService


def _make_db(tmp_path, name: str):
    db_path = tmp_path / name
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def _seed_order_graph(db, *, stock_qty: float, usage_per_sale: float, sold_qty: int = 1):
    cashier = User(
        username="cashier",
        full_name="Cashier User",
        password=AuthService.hash_password("pass123"),
        role=UserRole.cashier,
        is_active=True,
    )
    waiter = User(
        username="waiter",
        full_name="Waiter User",
        password=AuthService.hash_password("pass123"),
        role=UserRole.waiter,
        is_active=True,
    )
    table = Table(number=1, name="M1", status=TableStatus.occupied)
    cat = MenuCategory(name="İçki", icon="☕")
    inv = InventoryItem(name="Çay yarpağı", unit="qram", quantity=stock_qty, min_quantity=10)
    db.add_all([cashier, waiter, table, cat, inv])
    db.flush()

    menu_item = MenuItem(
        category_id=cat.id,
        name="Çay",
        price=2.5,
        inventory_item_id=inv.id,
        stock_usage_qty=usage_per_sale,
    )
    db.add(menu_item)
    db.flush()

    order = Order(table_id=table.id, waiter_id=waiter.id, status=OrderStatus.new, subtotal=2.5 * sold_qty, total=2.5 * sold_qty)
    db.add(order)
    db.flush()

    db.add(
        OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=sold_qty,
            unit_price=2.5,
            subtotal=2.5 * sold_qty,
            status=OrderStatus.new,
        )
    )
    db.commit()
    return order.id, cashier.id, inv.id


def test_payment_consumes_inventory_by_menu_usage_qty(tmp_path):
    SessionLocal = _make_db(tmp_path, "consumption_ok.sqlite3")
    with SessionLocal() as db:
        order_id, cashier_id, inv_id = _seed_order_graph(db, stock_qty=500.0, usage_per_sale=10.0, sold_qty=1)
        svc = POSService()
        ok, payment = svc.process_payment(db, order_id=order_id, method=PaymentMethod.cash.value, cashier_id=cashier_id)
        assert ok is True
        assert payment is not None
        inv = db.get(InventoryItem, inv_id)
        assert inv is not None
        assert inv.quantity == 490.0


def test_payment_fails_when_stock_is_insufficient(tmp_path):
    SessionLocal = _make_db(tmp_path, "consumption_fail.sqlite3")
    with SessionLocal() as db:
        order_id, cashier_id, inv_id = _seed_order_graph(db, stock_qty=8.0, usage_per_sale=10.0, sold_qty=1)
        svc = POSService()
        ok, msg = svc.process_payment(db, order_id=order_id, method=PaymentMethod.cash.value, cashier_id=cashier_id)
        assert ok is False
        assert "Stok kifayət deyil" in str(msg)
        inv = db.get(InventoryItem, inv_id)
        assert inv is not None
        assert inv.quantity == 8.0
