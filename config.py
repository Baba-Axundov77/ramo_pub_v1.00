# config.py - Ramo Pub & TeaHouse Configuration
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent

# .env faylını hər zaman layihə kökündən oxu (IDE run config CWD-dən asılı olmasın)
load_dotenv(BASE_DIR / ".env")

# App Info
APP_NAME = "Ramo Pub & TeaHouse"
APP_VERSION = "1.0.0"
APP_LANG = "az"

# PostgreSQL Connection - Tamamen .env'e bağlı
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "ramo_pub"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Tam URL override imkanı (məs: Render/Heroku və s.)
DATABASE_URL = os.getenv("DATABASE_URL") or str(
    URL.create(
        "postgresql+psycopg2",
        username=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
    )
)

# Web Server Configuration
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))

# Flask Configuration
FLASK_SECRET = os.getenv("FLASK_SECRET") or os.getenv("SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
FLASK_ENV = os.getenv("FLASK_ENV", "production")

# Security Configuration
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
DEFAULT_ADMIN_PASSWORD = os.getenv("RAMO_DEFAULT_ADMIN_PASSWORD", "admin123")
ENABLE_RUNTIME_AUTO_MIGRATE = os.getenv("ENABLE_RUNTIME_AUTO_MIGRATE", "0") == "1"

# User Roles
ROLES = {
    "admin": "Admin",
    "manager": "Menecer",
    "waiter": "Ofisiant",
    "cashier": "Kassir",
    "kitchen": "Mətbəx",
}

# Table Status
TABLE_STATUS = {
    "available": "Bos",
    "occupied": "Dolu",
    "reserved": "Rezerv",
    "cleaning": "Temizlenir",
}

# Order Status
ORDER_STATUS = {
    "new": "Yeni",
    "preparing": "Hazirlanir",
    "ready": "Hazirdir",
    "served": "Verildi",
    "paid": "Odenildi",
    "cancelled": "Legv edildi",
}

# Payment Methods
PAYMENT_METHODS = {
    "cash": "Nagd",
    "card": "Kart",
    "online": "Online",
}

# Theme
DEFAULT_THEME = "dark"

# Receipt Printer
PRINTER_ENABLED = False
PRINTER_PORT = os.getenv("PRINTER_PORT", "COM1")

# Web Panel - WEB_HOST and WEB_PORT already defined above


# Inventory policy
ALLOW_NEGATIVE_STOCK = os.getenv("ALLOW_NEGATIVE_STOCK", "0") == "1"

# Additional Configuration
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
