# database/connection.py
from __future__ import annotations
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

# Configure logging for database operations
logging.basicConfig(level=logging.INFO)
db_logger = logging.getLogger(__name__)

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
    ("menu_items",   "stock_usage_qty",   "FLOAT DEFAULT 0.0"),
    ("menu_items",   "sort_order",        "INTEGER DEFAULT 0"),


    # menu_item_recipes
    ("menu_item_recipes", "quantity_unit",   "VARCHAR(30)"),
    ("menu_item_recipes", "valid_from",      "DATE"),
    ("menu_item_recipes", "valid_until",     "DATE"),
    ("menu_item_recipes", "is_active",       "BOOLEAN DEFAULT 1"),
    ("menu_item_recipes", "created_at",      "TIMESTAMP"),

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
    """Verilənlər bazasına qos, cedvelleri yarat, eksik sutunlari elave et.
    
    KRİTİK: SQLite fallback tamamen kaldırıldı. Sistem PostgreSQL olmadan başlamaz.
    Optimizasyon: Connection pooling ve retry mekanizması eklendi.
    """
    global engine, SessionLocal
    SessionLocal = None  # Reset
    
    # Retry mechanism for PostgreSQL connection
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            db_logger.info(f"PostgreSQL bağlantı denemesi {attempt + 1}/{max_retries}")
            
            engine = create_engine(
                DATABASE_URL,
                # Optimized connection pooling
                pool_pre_ping=True,
                pool_size=20,           # Increased from 10
                max_overflow=10,         # Reduced from 20 for better control
                pool_timeout=30,         # New: Connection timeout
                pool_recycle=1800,       # New: Recycle connections after 30 minutes
                echo=False,              # Set to True for SQL debugging
                # PostgreSQL specific optimizations
                connect_args={
                    "application_name": "ramo_pub_enterprise",
                    "connect_timeout": 10,
                }
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                db_logger.info("PostgreSQL bağlantısı başarılı")
            
            # If connection successful, break the retry loop
            break
            
        except OperationalError as e:
            db_logger.error(f"PostgreSQL bağlantı xətası (deneme {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                db_logger.info(f"{retry_delay} saniye sonra yeniden denenecek...")
                time.sleep(retry_delay)
            else:
                # KRİTİK: SQLite fallback kaldırıldı - sistem PostgreSQL olmadan başlamamalı
                error_msg = (
                    f"PostgreSQL bağlantı xətası: {str(e)}\n\n"
                    f"{max_retries} deneme başarısız oldu.\n\n"
                    "Zəhmət olmasa:\n"
                    "1. PostgreSQL serverinin işlədiyini yoxlayın\n"
                    "2. .env faylındakı DB məlumatlarını yoxlayın\n"
                    "3. 'ramo_pub' bazasının mövcud olduğunu yoxlayın\n"
                    "4. PostgreSQL user şifrəsinin düzgün olduğunu yoxlayın\n"
                    "5. Firewall və network bağlantısını yoxlayın"
                )
                db_logger.critical(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Beklenmedik xeta: {str(e)}"
            db_logger.critical(error_msg)
            return False, error_msg

    try:
        SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=engine,
            # Additional session configuration
            expire_on_commit=False
        )

        # Yeni cedvelleri yarat (movcudlari deyismir)
        from database.models import create_all_tables
        create_all_tables(engine)
        db_logger.info("Veritabanı tabloları başarıyla oluşturuldu/kontrol edildi")

        # Alembic-first axını: runtime auto-migrate yalnız açıq şəkildə istənəndə işləsin.
        run_auto_migrate = os.getenv("ENABLE_RUNTIME_AUTO_MIGRATE", "0") == "1"
        if run_auto_migrate:
            with engine.connect() as conn:
                _auto_migrate(conn)
                db_logger.info("Runtime auto-migration tamamlandı")

        success_msg = (
            "Verilənlər bazası PostgreSQL üzerinden başarıyla bağlandı.\n"
            f"Connection Pool: pool_size=20, max_overflow=10, pool_timeout=30s"
        )
        db_logger.info(success_msg)
        return True, success_msg
        
    except OperationalError as e:
        error_msg = f"PostgreSQL bağlantı xətası (session oluşturma): {str(e)}"
        db_logger.critical(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Session oluşturma xətası: {str(e)}"
        db_logger.critical(error_msg)
        return False, error_msg


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

def get_db_session():
    """Generator-based database session for Flask app context"""
    if SessionLocal is None:
        raise RuntimeError("Verilənlər bazası inisializasiya edilməyib.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
