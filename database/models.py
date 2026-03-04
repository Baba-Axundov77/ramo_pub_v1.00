# database/models.py — Bütün Cədvəl Modelləri
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, Date, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum


# ─── ENUM Növləri ─────────────────────────────────────────────────────────────

class UserRole(enum.Enum):
    admin   = "admin"
    manager = "manager"
    waiter  = "waiter"
    cashier = "cashier"
    kitchen = "kitchen"

class TableStatus(enum.Enum):
    available = "available"
    occupied  = "occupied"
    reserved  = "reserved"
    cleaning  = "cleaning"

class OrderStatus(enum.Enum):
    new       = "new"
    preparing = "preparing"
    ready     = "ready"
    served    = "served"
    paid      = "paid"
    cancelled = "cancelled"

class PaymentMethod(enum.Enum):
    cash   = "cash"
    card   = "card"
    online = "online"


# ─── İSTİFADƏÇİLƏR ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50), unique=True, nullable=False)
    full_name  = Column(String(100), nullable=False)
    password   = Column(String(255), nullable=False)  # bcrypt hash
    role       = Column(Enum(UserRole), nullable=False)
    phone      = Column(String(20))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    orders     = relationship("Order", back_populates="waiter")
    shifts     = relationship("Shift", back_populates="user")


# ─── MASALAR ──────────────────────────────────────────────────────────────────

class Table(Base):
    __tablename__ = "tables"

    id         = Column(Integer, primary_key=True, index=True)
    number     = Column(Integer, unique=True, nullable=False)
    name       = Column(String(50))  # "VIP 1", "Bağ 3" və s.
    capacity   = Column(Integer, default=4)
    status     = Column(Enum(TableStatus), default=TableStatus.available)
    floor      = Column(Integer, default=1)
    zone       = Column(String(50), nullable=True)
    current_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    image_path = Column(String(255), nullable=True)
    is_active  = Column(Boolean, default=True)

    orders       = relationship("Order", back_populates="table", foreign_keys="Order.table_id")
    reservations = relationship("Reservation", back_populates="table")
    current_order = relationship("Order", foreign_keys=[current_order_id], post_update=True)


# ─── MENYU KATEQORİYALARI ─────────────────────────────────────────────────────

class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    name_az     = Column(String(100), nullable=True)
    name_en     = Column(String(100), nullable=True)
    description = Column(Text)
    icon        = Column(String(50))   # emoji və ya icon adı
    sort_order  = Column(Integer, default=0)
    parent_id   = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)
    is_active   = Column(Boolean, default=True)

    items = relationship("MenuItem", back_populates="category")


# ─── MENYU MÜHİMLƏRİ ──────────────────────────────────────────────────────────

class MenuItem(Base):
    __tablename__ = "menu_items"

    id          = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"))
    name        = Column(String(150), nullable=False)
    description = Column(Text)
    price       = Column(Float, nullable=False)
    cost_price  = Column(Float, default=0.0)   # Maya dəyəri
    image_url   = Column(Text, nullable=True)
    prep_time_min = Column(Integer, default=0)
    image_path  = Column(String(255))
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=True)
    stock_usage_qty = Column(Float, default=0.0)  # 1 satışda anbardan düşəcək miqdar
    sort_order  = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())

    category    = relationship("MenuCategory", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")
    inventory_item = relationship("InventoryItem", back_populates="menu_items")
    recipes = relationship("MenuItemRecipe", back_populates="menu_item", cascade="all, delete-orphan")


# ─── SİFARİŞLƏR ───────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id             = Column(Integer, primary_key=True, index=True)
    table_id       = Column(Integer, ForeignKey("tables.id"))
    waiter_id      = Column(Integer, ForeignKey("users.id"))
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status         = Column(Enum(OrderStatus), default=OrderStatus.new)
    subtotal       = Column(Float, default=0.0)
    total_amount   = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total          = Column(Float, default=0.0)
    notes          = Column(Text)
    note           = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, onupdate=func.now())
    paid_at        = Column(DateTime, nullable=True)
    closed_at      = Column(DateTime, nullable=True)

    table    = relationship("Table", back_populates="orders", foreign_keys=[table_id])
    waiter   = relationship("User", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items    = relationship("OrderItem", back_populates="order")
    payment  = relationship("Payment", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id           = Column(Integer, primary_key=True, index=True)
    order_id     = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity     = Column(Integer, default=1)
    unit_price   = Column(Float, nullable=False)
    subtotal     = Column(Float, nullable=False)
    notes        = Column(String(255))
    note         = Column(Text)
    sent_to_kitchen_at = Column(DateTime, nullable=True)
    status       = Column(Enum(OrderStatus), default=OrderStatus.new)
    created_at   = Column(DateTime, server_default=func.now())

    order     = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


# ─── ÖDƏNİŞLƏR ────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True, index=True)
    order_id       = Column(Integer, ForeignKey("orders.id"), unique=True)
    amount         = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    final_amount   = Column(Float, nullable=False)
    method         = Column(Enum(PaymentMethod), nullable=False)
    cashier_id     = Column(Integer, ForeignKey("users.id"))
    paid_at        = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="payment")


# ─── ANBAR & STOK ─────────────────────────────────────────────────────────────

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(150), nullable=False)
    unit          = Column(String(30))   # kq, litr, ədəd
    quantity      = Column(Float, default=0.0)
    min_quantity  = Column(Float, default=5.0)  # minimum xəbərdarlıq
    cost_per_unit = Column(Float, default=0.0)
    supplier      = Column(String(100))
    last_updated  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    menu_items = relationship("MenuItem", back_populates="inventory_item")
    purchase_items = relationship("PurchaseReceiptItem", back_populates="inventory_item")
    recipe_usages = relationship("MenuItemRecipe", back_populates="inventory_item")


class MenuItemRecipe(Base):
    __tablename__ = "menu_item_recipes"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_per_unit = Column(Float, nullable=False, default=0.0)

    menu_item = relationship("MenuItem", back_populates="recipes")
    inventory_item = relationship("InventoryItem", back_populates="recipe_usages")


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id = Column(Integer, primary_key=True, index=True)
    purchased_at = Column(DateTime, nullable=False, server_default=func.now())
    store_name = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    items = relationship("PurchaseReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("purchase_receipts.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    item_name = Column(String(150), nullable=False)
    unit = Column(String(30), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    receipt = relationship("PurchaseReceipt", back_populates="items")
    inventory_item = relationship("InventoryItem", back_populates="purchase_items")


# ─── İŞÇİLƏR & NÖVBƏLƏr ──────────────────────────────────────────────────────

class Shift(Base):
    __tablename__ = "shifts"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    date       = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time   = Column(Time)
    notes      = Column(Text)

    user = relationship("User", back_populates="shifts")


# ─── MÜŞTƏRİLƏR (Loyallıq) ───────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id           = Column(Integer, primary_key=True, index=True)
    full_name    = Column(String(100), nullable=False)
    phone        = Column(String(20), unique=True)
    email        = Column(String(100))
    points       = Column(Integer, default=0)
    total_spent  = Column(Float, default=0.0)
    birthday     = Column(Date, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    orders = relationship("Order", back_populates="customer")


# ─── REZERVASİYALAR ───────────────────────────────────────────────────────────

class Reservation(Base):
    __tablename__ = "reservations"

    id            = Column(Integer, primary_key=True, index=True)
    table_id      = Column(Integer, ForeignKey("tables.id"))
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20))
    date          = Column(Date, nullable=False)
    time          = Column(Time, nullable=False)
    reserved_at   = Column(DateTime, nullable=True)
    status        = Column(String(20), default="pending")
    guest_count   = Column(Integer, default=2)
    notes         = Column(Text)
    is_confirmed  = Column(Boolean, default=False)
    is_cancelled  = Column(Boolean, default=False)
    created_at    = Column(DateTime, server_default=func.now())

    table = relationship("Table", back_populates="reservations")


# ─── ENDİRİM / KUPONLAR ───────────────────────────────────────────────────────

class Discount(Base):
    __tablename__ = "discounts"

    id          = Column(Integer, primary_key=True, index=True)
    code        = Column(String(30), unique=True, nullable=False)
    description = Column(String(200))
    type        = Column(String(20))   # "percent" | "fixed"
    value       = Column(Float, nullable=False)
    min_order   = Column(Float, default=0.0)
    usage_limit = Column(Integer, default=0)   # 0 = limitsiz
    used_count  = Column(Integer, default=0)
    valid_from  = Column(Date)
    valid_until = Column(Date)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())


# ─── CƏDVƏLLƏRİ YARAT ────────────────────────────────────────────────────────

def create_all_tables(eng):
    Base.metadata.create_all(bind=eng)


# ─── LOYALLIK ƏMƏLIYYATLARI ──────────────────────────────────────────────────

class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id           = Column(Integer, primary_key=True, index=True)
    customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id     = Column(Integer, ForeignKey("orders.id"), nullable=True)
    points       = Column(Integer, nullable=False)   # + qazanıldı, - xərcləndi
    description  = Column(String(200))
    created_at   = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", backref="transactions")
    order    = relationship("Order")


# ─── ÇEK QEYDLƏR ─────────────────────────────────────────────────────────────

class ReceiptLog(Base):
    __tablename__ = "receipt_logs"

    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(Integer, ForeignKey("orders.id"), nullable=False)
    printed_at = Column(DateTime, server_default=func.now())
    method     = Column(String(20))   # "printer" | "pdf" | "screen"
    content    = Column(Text)

    order = relationship("Order")
