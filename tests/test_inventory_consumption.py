from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database.connection import Base
from src.core.database.models import (
    InventoryItem,
    MenuCategory,
    MenuItem,
    MenuItemRecipe,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Table,
    TableStatus,
    User,
    UserRole,
    InventoryAdjustment,
)
from src.core.modules.auth.auth_service import AuthService
from src.core.modules.pos.pos_service import POSService


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


def test_payment_consumes_multiple_recipe_ingredients(tmp_path):
    SessionLocal = _make_db(tmp_path, "consumption_recipe.sqlite3")
    with SessionLocal() as db:
        cashier = User(
            username="cashier2",
            full_name="Cashier User2",
            password=AuthService.hash_password("pass123"),
            role=UserRole.cashier,
            is_active=True,
        )
        waiter = User(
            username="waiter2",
            full_name="Waiter User2",
            password=AuthService.hash_password("pass123"),
            role=UserRole.waiter,
            is_active=True,
        )
        table = Table(number=2, name="M2", status=TableStatus.occupied)
        cat = MenuCategory(name="Çaylar", icon="🫖")
        tea = InventoryItem(name="Çay", unit="qram", quantity=450.0, min_quantity=10)
        herb = InventoryItem(name="Kəklik otu", unit="qram", quantity=50.0, min_quantity=5)
        db.add_all([cashier, waiter, table, cat, tea, herb])
        db.flush()

        menu_item = MenuItem(category_id=cat.id, name="Çaynikdə çay", price=6.0)
        db.add(menu_item)
        db.flush()

        db.add_all([
            MenuItemRecipe(menu_item_id=menu_item.id, inventory_item_id=tea.id, quantity_per_unit=10.0),
            MenuItemRecipe(menu_item_id=menu_item.id, inventory_item_id=herb.id, quantity_per_unit=2.0),
        ])

        order = Order(table_id=table.id, waiter_id=waiter.id, status=OrderStatus.new, subtotal=12.0, total=12.0)
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, menu_item_id=menu_item.id, quantity=2, unit_price=6.0, subtotal=12.0, status=OrderStatus.new))
        db.commit()

        svc = POSService()
        ok, _ = svc.process_payment(db, order_id=order.id, method=PaymentMethod.cash.value, cashier_id=cashier.id)
        assert ok is True

        tea_after = db.get(InventoryItem, tea.id)
        herb_after = db.get(InventoryItem, herb.id)
        assert tea_after.quantity == 430.0
        assert herb_after.quantity == 46.0


def test_recipe_unit_conversion_and_adjustment_log(tmp_path):
    SessionLocal = _make_db(tmp_path, "consumption_convert.sqlite3")
    with SessionLocal() as db:
        cashier = User(username="cashier3", full_name="Cashier3", password=AuthService.hash_password("pass123"), role=UserRole.cashier, is_active=True)
        waiter = User(username="waiter3", full_name="Waiter3", password=AuthService.hash_password("pass123"), role=UserRole.waiter, is_active=True)
        table = Table(number=3, name="M3", status=TableStatus.occupied)
        cat = MenuCategory(name="İçki", icon="🥤")
        cola_bulk = InventoryItem(name="Cola bulk", unit="litr", quantity=5.0, min_quantity=1)
        db.add_all([cashier, waiter, table, cat, cola_bulk]); db.flush()

        menu_item = MenuItem(category_id=cat.id, name="Cola 1L", price=4.0)
        db.add(menu_item); db.flush()
        db.add(MenuItemRecipe(menu_item_id=menu_item.id, inventory_item_id=cola_bulk.id, quantity_per_unit=1000.0, quantity_unit="ml"))

        order = Order(table_id=table.id, waiter_id=waiter.id, status=OrderStatus.new, subtotal=8.0, total=8.0)
        db.add(order); db.flush()
        db.add(OrderItem(order_id=order.id, menu_item_id=menu_item.id, quantity=2, unit_price=4.0, subtotal=8.0, status=OrderStatus.new))
        db.commit()

        ok, _ = POSService().process_payment(db, order_id=order.id, method=PaymentMethod.cash.value, cashier_id=cashier.id)
        assert ok is True

        after = db.get(InventoryItem, cola_bulk.id)
        assert after.quantity == 3.0
        logs = db.query(InventoryAdjustment).filter(InventoryAdjustment.reference == f"order:{order.id}").all()
        assert len(logs) >= 1
