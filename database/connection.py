# database/connection.py
from __future__ import annotations
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

Base = declarative_base()
engine = None
SessionLocal = None

# ── Avtomatik migration: DB-ye eksik sutunlari elave et ──────────────────────
# (table_name, column_name, column_sql_definition)
_MIGRATIONS = [
    # tables
    ("tables",       "image_path",        "VARCHAR(255)"),
    ("tables",       "floor",             "INTEGER DEFAULT 1"),
    ("tables",       "name",              "VARCHAR(50)"),

    # menu_items — inventory_item_id və digər eksik sütunlar əlavə edildi
    ("menu_items",   "image_path",        "VARCHAR(255)"),
    ("menu_items",   "image_url",         "TEXT"),
    ("menu_items",   "cost_price",        "FLOAT DEFAULT 0.0"),
    ("menu_items",   "prep_time_min",     "INTEGER DEFAULT 0"),
    ("menu_items",   "is_available",      "BOOLEAN DEFAULT 1"),
    ("menu_items",   "inventory_item_id", "INTEGER"),           # ← ƏSAS FIX
    ("menu_items",   "sort_order",        "INTEGER DEFAULT 0"),

    # orders
    ("orders",       "customer_id",       "INTEGER"),
    ("orders",       "subtotal",          "FLOAT DEFAULT 0.0"),
    ("orders",       "discount_amount",   "FLOAT DEFAULT 0.0"),
    ("orders",       "paid_at",           "TIMESTAMP"),

    # order_items
    ("order_items",  "notes",             "VARCHAR(255)"),

    # payments
    ("payments",     "discount_amount",   "FLOAT DEFAULT 0.0"),

    # users
    ("users",        "updated_at",        "TIMESTAMP"),
    ("users",        "phone",             "VARCHAR(20)"),

    # inventory_items
    ("inventory_items", "supplier",       "VARCHAR(100)"),
    ("inventory_items", "min_quantity",   "FLOAT DEFAULT 5.0"),
    ("inventory_items", "cost_per_unit",  "FLOAT DEFAULT 0.0"),
]


def _auto_migrate(conn):
    """Eksik sutunlari DB-ye elave et - movcud cedveller deyisdirilmir."""
    try:
        insp = inspect(conn)
        existing_tables = insp.get_table_names()
        for table, column, col_def in _MIGRATIONS:
            if table not in existing_tables:
                continue
            existing_cols = [c["name"] for c in insp.get_columns(table)]
            if column not in existing_cols:
                try:
                    # IF NOT EXISTS SQLite 3.37+ tələb edir,
                    # try/except artıq qoruyur — sildik
                    conn.execute(text(
                        f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_def}'
                    ))
                    conn.commit()
                    print(f"[MIGRATE] {table}.{column} elave edildi")
                except Exception as e:
                    conn.rollback()
                    print(f"[MIGRATE SKIP] {table}.{column}: {e}")
    except Exception as e:
        print(f"[MIGRATE ERROR] {e}")


def init_database():
    """Verilənlər bazasına qos, cedvelleri yarat, eksik sutunlari elave et."""
    global engine, SessionLocal
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        sqlite_url = os.getenv("SQLITE_FALLBACK_URL", "sqlite:///ramo_pub.sqlite3")
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Yeni cedvelleri yarat (movcudlari deyismir)
        from database.models import create_all_tables
        create_all_tables(engine)

        # AUTO-MIGRATE həmişə işləyir — env flag silindi
        with engine.connect() as conn:
            _auto_migrate(conn)

        return True, "Verilənlər bazasına ugurla qosuldu."
    except OperationalError as e:
        return False, f"Baglanti xetasi: {str(e)}"
    except Exception as e:
        return False, f"Xeta: {str(e)}"


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Verilənlər bazası inisializasiya edilməyib.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Verilənlər bazası inisializasiya edilməyib.")
    return SessionLocal()
