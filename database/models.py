# database/models.py — Bütün Cədvəl Modelləri
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, Date, Time, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum


# ─── ENUM Növləri ─────────────────────────────────────────────────────────────

class UserRole(enum.Enum):
    admin = "admin"
    manager = "manager"
    waiter = "waiter"
    cashier = "cashier"
    kitchen = "kitchen"


class TableStatus(enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    cleaning = "cleaning"


class OrderStatus(enum.Enum):
    new = "new"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    paid = "paid"
    cancelled = "cancelled"


class PaymentMethod(enum.Enum):
    cash = "cash"
    card = "card"
    online = "online"


# ─── İSTİFADƏÇİLƏR ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)  # bcrypt hash
    role = Column(Enum(UserRole), nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    orders = relationship("Order", back_populates="waiter")
    shifts = relationship("Shift", back_populates="user")
<<<<<<< Updated upstream
    
    # Staff management relationships
    performance_records = relationship("StaffPerformance", back_populates="staff")
    schedules = relationship("StaffSchedule", back_populates="staff", foreign_keys="StaffSchedule.staff_id")
    leave_requests = relationship("LeaveRequest", back_populates="staff", foreign_keys="LeaveRequest.staff_id")
    waste_records = relationship("WasteRecord", back_populates="staff")
    tip_distributions = relationship("TipDistribution", back_populates="staff")
    order_modifications = relationship("OrderModification", back_populates="staff")
=======
>>>>>>> Stashed changes


# ─── MASALAR ──────────────────────────────────────────────────────────────────

class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    name = Column(String(50))  # "VIP 1", "Bağ 3" və s.
    capacity = Column(Integer, default=4)
    status = Column(Enum(TableStatus), default=TableStatus.available)
    floor = Column(Integer, default=1)
    zone = Column(String(50), nullable=True)
    current_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    image_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="table", foreign_keys="Order.table_id")
    reservations = relationship("Reservation", back_populates="table")
    current_order = relationship("Order", foreign_keys=[current_order_id], post_update=True)


# ─── MENYU KATEQORİYALARI ─────────────────────────────────────────────────────

class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    name_az = Column(String(100), nullable=True)
    name_en = Column(String(100), nullable=True)
    description = Column(Text)
    icon = Column(String(50))  # emoji və ya icon adı
    sort_order = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    items = relationship("MenuItem", back_populates="category")


# ─── MENYU MÜHİMLƏRİ ──────────────────────────────────────────────────────────

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"))
    name = Column(String(150), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    cost_price = Column(Float, default=0.0)  # Maya dəyəri
    image_url = Column(Text, nullable=True)
    prep_time_min = Column(Integer, default=0)
    image_path = Column(String(255))
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=True)
    stock_usage_qty = Column(Float, default=0.0)  # 1 satışda anbardan düşəcək miqdar
<<<<<<< Updated upstream
    kitchen_station_id = Column(Integer, ForeignKey("kitchen_stations.id"), nullable=True)
=======
>>>>>>> Stashed changes
    sort_order = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    category = relationship("MenuCategory", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")
    inventory_item = relationship("InventoryItem", back_populates="menu_items")
    recipes = relationship("MenuItemRecipe", back_populates="menu_item", cascade="all, delete-orphan")
    kitchen_station = relationship("KitchenStation", back_populates="menu_items")


# ─── SİFARİŞLƏR ───────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_created_at_status", "created_at", "status"),
        Index("ix_orders_table_id_status_created_at", "table_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"))
    waiter_id = Column(Integer, ForeignKey("users.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.new)
    subtotal = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text)
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    paid_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
<<<<<<< Updated upstream
    
    # Kitchen tracking fields
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    preparation_started_at = Column(DateTime, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
=======
>>>>>>> Stashed changes

    table = relationship("Table", back_populates="orders", foreign_keys=[table_id])
    waiter = relationship("User", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payment = relationship("Payment", back_populates="order", uselist=False)
<<<<<<< Updated upstream
    modifications = relationship("OrderModification", back_populates="order")
    tip_distributions = relationship("TipDistribution", back_populates="order")
    payment_transactions = relationship("PaymentTransaction", back_populates="order")
=======
>>>>>>> Stashed changes


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    notes = Column(String(255))
    note = Column(Text)
    sent_to_kitchen_at = Column(DateTime, nullable=True)
<<<<<<< Updated upstream
    started_at = Column(DateTime, nullable=True)  # When preparation started
    completed_at = Column(DateTime, nullable=True)  # When item completed
    prepared_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Kitchen staff
    is_voided = Column(Boolean, default=False)  # For item cancellations
    void_reason = Column(String(255), nullable=True)
    voided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime, nullable=True)
    modified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    modified_at = Column(DateTime, nullable=True)
=======
>>>>>>> Stashed changes
    status = Column(Enum(OrderStatus), default=OrderStatus.new)
    created_at = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


# ─── ÖDƏNİŞLƏR ────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_created_at_method", "created_at", "method"),
    )

    id = Column(Integer, primary_key=True, index=True)
<<<<<<< Updated upstream
    order_id = Column(Integer, ForeignKey("orders.id"))  # Remove unique for split payments
    amount = Column(Float, nullable=False)
    tip_amount = Column(Float, default=0.0)  # Tip for this payment
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)  # amount + tip_amount
=======
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
>>>>>>> Stashed changes
    method = Column(Enum(PaymentMethod), nullable=False)
    cashier_id = Column(Integer, ForeignKey("users.id"))
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
<<<<<<< Updated upstream
    
    # Split payment fields
    parent_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)  # For refunds
    transaction_id = Column(String(100), nullable=True)  # Gateway transaction ID
    auth_code = Column(String(50), nullable=True)
    card_type = Column(String(50), nullable=True)
    status = Column(String(20), default="completed")  # completed, failed, refunded
    reason = Column(String(255), nullable=True)  # For refunds/voids
=======
>>>>>>> Stashed changes

    order = relationship("Order", back_populates="payment")


# ─── ANBAR & STOK ─────────────────────────────────────────────────────────────

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    unit = Column(String(30))  # kq, litr, ədəd
    quantity = Column(Float, default=0.0)
    min_quantity = Column(Float, default=5.0)  # minimum xəbərdarlıq
    cost_per_unit = Column(Float, default=0.0)
    supplier = Column(String(100))
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    menu_items = relationship("MenuItem", back_populates="inventory_item")
    purchase_items = relationship("PurchaseReceiptItem", back_populates="inventory_item")
    recipe_usages = relationship("MenuItemRecipe", back_populates="inventory_item")
    waste_records = relationship("WasteRecord", back_populates="inventory_item")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="inventory_item")


class MenuItemRecipe(Base):
    __tablename__ = "menu_item_recipes"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_per_unit = Column(Float, nullable=False, default=0.0)
    quantity_unit = Column(String(30), nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    menu_item = relationship("MenuItem", back_populates="recipes")
    inventory_item = relationship("InventoryItem", back_populates="recipe_usages")


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    delta_quantity = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True)
    adjustment_type = Column(String(30), nullable=False)  # purchase|sale|manual|waste|rollback
    reason = Column(String(255), nullable=True)
    reference = Column(String(120), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    inventory_item = relationship("InventoryItem")


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id = Column(Integer, primary_key=True, index=True)
    purchased_at = Column(DateTime, nullable=False, server_default=func.now())
    store_name = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    is_cancelled = Column(Boolean, default=False)
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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    user = relationship("User", back_populates="shifts")


# ─── MÜŞTƏRİLƏR (Loyallıq) ───────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_phone_is_active", "phone", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(100))
    points = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    birthday = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
<<<<<<< Updated upstream
    
    # Customer analytics fields
    tier_id = Column(Integer, ForeignKey("customer_tiers.id"), nullable=True)
    last_visit_date = Column(DateTime, nullable=True)
    visit_count = Column(Integer, default=0)
    avg_order_value = Column(Float, default=0.0)
    preferred_items = Column(Text)  # JSON string of preferred menu items
    loyalty_score = Column(Float, default=0.0)  # 0 to 100
    churn_risk = Column(String(20), default='low')  # low, medium, high
=======
>>>>>>> Stashed changes

    orders = relationship("Order", back_populates="customer")
    tier = relationship("CustomerTier", back_populates="customers")
    interactions = relationship("CustomerInteraction", back_populates="customer")
    behaviors = relationship("CustomerBehavior", back_populates="customer")
    lifetime_value = relationship("CustomerLifetimeValue", back_populates="customer", uselist=False)


# ─── REZERVASİYALAR ───────────────────────────────────────────────────────────

class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservations_date_table_id_is_cancelled", "date", "table_id", "is_cancelled"),
    )

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"))
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    reserved_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    guest_count = Column(Integer, default=2)
    notes = Column(Text)
    is_confirmed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    table = relationship("Table", back_populates="reservations")


# ─── ENDİRİM / KUPONLAR ───────────────────────────────────────────────────────

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)
    description = Column(String(200))
    type = Column(String(20))  # "percent" | "fixed"
    value = Column(Float, nullable=False)
    min_order = Column(Float, default=0.0)
    usage_limit = Column(Integer, default=0)  # 0 = limitsiz
    used_count = Column(Integer, default=0)
    valid_from = Column(Date)
    valid_until = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ─── CƏDVƏLLƏRİ YARAT ────────────────────────────────────────────────────────

def create_all_tables(eng):
    Base.metadata.create_all(bind=eng)


# ─── LOYALLIK ƏMƏLIYYATLARI ──────────────────────────────────────────────────

class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    points = Column(Integer, nullable=False)  # + qazanıldı, - xərcləndi
    description = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", backref="transactions")
    order = relationship("Order")


# ─── ÇEK QEYDLƏR ─────────────────────────────────────────────────────────────

class ReceiptLog(Base):
    __tablename__ = "receipt_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    printed_at = Column(DateTime, server_default=func.now())
    method = Column(String(20))  # "printer" | "pdf" | "screen"
    content = Column(Text)

    order = relationship("Order")


# ─── ENTERPRISE ORDER MANAGEMENT ───────────────────────────────────────────────

class OrderModification(Base):
    __tablename__ = "order_modifications"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    modification_type = Column(String(50), nullable=False)  # add_item, remove_item, modify_item
    reason = Column(Text, nullable=False)
    old_total = Column(Float, nullable=False)
    new_total = Column(Float, nullable=False)
    modification_time = Column(DateTime, server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="modifications")
    staff = relationship("User")


class TipDistribution(Base):
    __tablename__ = "tip_distributions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tip_amount = Column(Float, nullable=False)
    distributed_at = Column(DateTime, server_default=func.now())

    # Relationships
    order = relationship("Order")
    staff = relationship("User")


class PaymentStatus(enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    settled = "settled"


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    gateway_transaction_id = Column(String(100), unique=True, nullable=False)
    gateway_response = Column(Text)  # JSON response from gateway
    auth_code = Column(String(50))
    card_type = Column(String(50))
    status = Column(String(20), default=PaymentStatus.pending.value)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='AZN')
    created_at = Column(DateTime, server_default=func.now())
    settled_at = Column(DateTime)

    # Relationships
    order = relationship("Order")


# ─── KITCHEN DISPLAY SYSTEM ───────────────────────────────────────────────

class KitchenStation(Base):
    __tablename__ = "kitchen_stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    printer_ip = Column(String(45))  # Network printer for this station
    display_order = Column(Integer, default=1)  # Display order priority
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    menu_items = relationship("MenuItem", back_populates="kitchen_station")
    kds_messages = relationship("KDSMessage", back_populates="station")


class ItemPreparationTime(Base):
    __tablename__ = "item_preparation_times"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    prep_time_minutes = Column(Integer, nullable=False)
    prep_count = Column(Integer, default=1)  # Number of times tracked
    last_updated = Column(DateTime, server_default=func.now())

    # Relationships
    menu_item = relationship("MenuItem")


class KDSMessage(Base):
    __tablename__ = "kds_messages"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("kitchen_stations.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    message = Column(Text, nullable=False)
    message_type = Column(String(20), default='info')  # info, warning, error
    created_at = Column(DateTime, server_default=func.now())
    is_read = Column(Boolean, default=False)
    expires_at = Column(DateTime)  # Message expiration time

    # Relationships
    station = relationship("KitchenStation", back_populates="kds_messages")
    order = relationship("Order")


# ─── RECIPE COSTING & MENU ENGINEERING ───────────────────────────────────

class WasteRecord(Base):
    __tablename__ = "waste_records"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    waste_type = Column(String(50), nullable=False)  # spoilage, overportion, return, etc.
    reason = Column(Text)
    estimated_cost = Column(Float)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime, server_default=func.now())

    # Relationships
    inventory_item = relationship("InventoryItem")
    staff = relationship("User")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    contact_person = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    lead_time_days = Column(Integer, default=3)
    preferred = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(20), default='pending')  # pending, approved, ordered, received
    total_amount = Column(Float)
    order_date = Column(Date, default=func.current_date())
    expected_delivery_date = Column(Date)
    received_date = Column(Date)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    staff = relationship("User")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    received_quantity = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    inventory_item = relationship("InventoryItem")


# ─── STAFF MANAGEMENT & PERFORMANCE TRACKING ──────────────────────────

class StaffPerformance(Base):
    __tablename__ = "staff_performance"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    performance_date = Column(Date, nullable=False)
    orders_served = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0)
    table_turnover = Column(Integer, default=0)
    customer_satisfaction = Column(Integer, default=0)  # 1-5 scale
    attendance_score = Column(Integer, default=100)  # Percentage
    tips_received = Column(Float, default=0)
    hours_worked = Column(Float, default=0)  # Hours worked that day
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # Relationships
    staff = relationship("User")


class StaffSchedule(Base):
    __tablename__ = "staff_schedules"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    position = Column(String(50), nullable=False)  # waiter, kitchen, cashier, manager
    shift_type = Column(String(20), default='regular')  # morning, evening, night, regular
    is_confirmed = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    optimization_score = Column(Float, default=0)  # AI optimization score
    assignment_type = Column(String(20), default='manual')  # manual, auto_fill, optimized

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    creator = relationship("User", foreign_keys=[created_by])


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(String(20), nullable=False)  # vacation, sick, personal, emergency
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default='pending')  # pending, approved, rejected, cancelled
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    staff = relationship("User", foreign_keys=[staff_id])
    approver = relationship("User", foreign_keys=[approved_by])


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"

    id = Column(Integer, primary_key=True, index=True)
    original_shift_id = Column(Integer, ForeignKey("staff_schedules.id"), nullable=False)
    target_shift_id = Column(Integer, ForeignKey("staff_schedules.id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_staff_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(Text)
    status = Column(String(20), default='pending')  # pending, approved, rejected, cancelled
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    original_shift = relationship("StaffSchedule", foreign_keys=[original_shift_id])
    target_shift = relationship("StaffSchedule", foreign_keys=[target_shift_id])
    requester = relationship("User", foreign_keys=[requester_id])
    target_staff = relationship("User", foreign_keys=[target_staff_id])
    approver = relationship("User", foreign_keys=[approved_by])


# ─── CUSTOMER ANALYTICS & RFM SEGMENTATION ───────────────────────────

class CustomerTier(Base):
    __tablename__ = "customer_tiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    min_spent = Column(Float, nullable=False)
    max_spent = Column(Float)
    points_multiplier = Column(Float, default=1.0)
    benefits = Column(Text)  # JSON string of benefits
    color = Column(String(7), default='#808080')  # Hex color
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    customers = relationship("Customer", back_populates="tier")


class CustomerInteraction(Base):
    __tablename__ = "customer_interactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # phone_call, visit, complaint, compliment
    interaction_date = Column(DateTime, server_default=func.now())
    details = Column(Text)
    staff_id = Column(Integer, ForeignKey("users.id"))
    sentiment_score = Column(Integer, default=0)  # -1 to 1 scale
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="interactions")
    staff = relationship("User")


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    segment_type = Column(String(20), nullable=False)  # rfm, behavioral, demographic
    criteria = Column(Text)  # JSON string of segmentation criteria
    description = Column(Text)
    customer_count = Column(Integer, default=0)
    avg_order_value = Column(Float, default=0.0)
    total_revenue = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # Relationships
    segment_members = relationship("CustomerSegmentMember", back_populates="segment")


class CustomerSegmentMember(Base):
    __tablename__ = "customer_segment_members"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    segment_id = Column(Integer, ForeignKey("customer_segments.id"), nullable=False)
    score = Column(Float)  # RFM score or behavioral score
    confidence = Column(Float, default=1.0)  # Confidence of assignment
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # When this assignment expires

    # Relationships
    customer = relationship("Customer")
    segment = relationship("CustomerSegment", back_populates="segment_members")


class CustomerBehavior(Base):
    __tablename__ = "customer_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    behavior_type = Column(String(50), nullable=False)  # visit_frequency, avg_order_size, preferred_items, peak_hours
    behavior_data = Column(Text)  # JSON string of behavior data
    last_updated = Column(DateTime, server_default=func.now())
    confidence_score = Column(Float, default=0.0)

    # Relationships
    customer = relationship("Customer", back_populates="behaviors")


class CustomerLifetimeValue(Base):
    __tablename__ = "customer_lifetime_values"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    current_clv = Column(Float, default=0.0)  # Current lifetime value
    predicted_clv = Column(Float, default=0.0)  # Predicted future value
    avg_monthly_value = Column(Float, default=0.0)
    churn_probability = Column(Float, default=0.0)  # 0 to 1
    loyalty_score = Column(Float, default=0.0)  # 0 to 100
    next_visit_probability = Column(Float, default=0.0)
    calculated_at = Column(DateTime, server_default=func.now())
    model_version = Column(String(20), default="v1.0")

    # Relationships
    customer = relationship("Customer", back_populates="lifetime_value")


# ─── BUSINESS INTELLIGENCE & ANALYTICS ───────────────────────────────

class SalesForecast(Base):
    __tablename__ = "sales_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    forecast_date = Column(Date, nullable=False)
    forecast_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    predicted_revenue = Column(Float, nullable=False)
    predicted_orders = Column(Integer, nullable=False)
    predicted_customers = Column(Integer, nullable=False)
    confidence_level = Column(Float, default=0.95)  # 0.0 to 1.0
    model_version = Column(String(20), default="v1.0")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    forecast_items = relationship("SalesForecastItem", back_populates="forecast")


class SalesForecastItem(Base):
    __tablename__ = "sales_forecast_items"

    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, ForeignKey("sales_forecasts.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    predicted_quantity = Column(Integer, nullable=False)
    predicted_revenue = Column(Float, nullable=False)
    seasonality_factor = Column(Float, default=1.0)
    trend_factor = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    forecast = relationship("SalesForecast", back_populates="forecast_items")
    menu_item = relationship("MenuItem")


class BusinessMetric(Base):
    __tablename__ = "business_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(Date, nullable=False)
    metric_type = Column(String(50), nullable=False)  # revenue, orders, customers, labor, inventory
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=False)  # AZN, count, percentage, hours
    comparison_period = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    comparison_value = Column(Float)  # Previous period value for comparison
    change_percentage = Column(Float)  # Percentage change from previous period
    target_value = Column(Float)  # Target/KPI value
    achievement_percentage = Column(Float)  # Achievement as percentage of target
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    metric_details = relationship("BusinessMetricDetail", back_populates="metric")


class BusinessMetricDetail(Base):
    __tablename__ = "business_metric_details"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("business_metrics.id"), nullable=False)
    dimension = Column(String(50), nullable=False)  # category, station, staff, time_slot
    dimension_value = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    contribution_percentage = Column(Float, default=0.0)  # Contribution to total metric
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    metric = relationship("BusinessMetric", back_populates="metric_details")


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False)
    report_type = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Revenue metrics
    total_revenue = Column(Float, nullable=False)
    food_revenue = Column(Float, nullable=False)
    beverage_revenue = Column(Float, nullable=False)
    other_revenue = Column(Float, default=0.0)
    
    # Cost metrics
    food_cost = Column(Float, nullable=False)
    beverage_cost = Column(Float, nullable=False)
    labor_cost = Column(Float, nullable=False)
    overhead_cost = Column(Float, default=0.0)
    total_cost = Column(Float, nullable=False)
    
    # Profitability metrics
    gross_profit = Column(Float, nullable=False)
    net_profit = Column(Float, nullable=False)
    gross_margin = Column(Float, nullable=False)
    net_margin = Column(Float, nullable=False)
    
    # Efficiency metrics
    table_turnover_rate = Column(Float, nullable=False)
    seat_occupancy_rate = Column(Float, nullable=False)
    avg_check_size = Column(Float, nullable=False)
    covers_per_hour = Column(Float, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MenuPerformance(Base):
    __tablename__ = "menu_performance"

    id = Column(Integer, primary_key=True, index=True)
    analysis_date = Column(Date, nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    total_orders = Column(Integer, nullable=False)
    total_revenue = Column(Float, nullable=False)
    total_quantity = Column(Integer, nullable=False)
    avg_order_quantity = Column(Float, nullable=False)
    profit_margin = Column(Float, nullable=False)
    cost_percentage = Column(Float, nullable=False)
    popularity_score = Column(Float, nullable=False)  # 0 to 100 based on orders
    profitability_score = Column(Float, nullable=False)  # 0 to 100 based on profit margin
    menu_engineering_category = Column(String(20))  # star, plowhorse, puzzle, dog
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    menu_item = relationship("MenuItem")


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    widget_name = Column(String(100), nullable=False)
    widget_type = Column(String(20), nullable=False)  # chart, metric, table, gauge
    dashboard_name = Column(String(50), nullable=False)  # sales, operations, finance, staff
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)
    data_source = Column(String(100), nullable=False)  # API endpoint or data query
    refresh_interval = Column(Integer, default=300)  # Seconds
    is_active = Column(Boolean, default=True)
    config = Column(Text)  # JSON configuration for the widget
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─── CƏDVƏLLƏRİ YARAT ────────────────────────────────────────────────────────

def create_all_tables(eng):
    Base.metadata.create_all(bind=eng)
