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

# PostgreSQL Connection
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

# Web Panel
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
SECRET_KEY = os.getenv("SECRET_KEY")


# Inventory policy
ALLOW_NEGATIVE_STOCK = os.getenv("ALLOW_NEGATIVE_STOCK", "0") == "1"
