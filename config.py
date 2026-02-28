# config.py - Ramo Pub & TeaHouse Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# App Info
APP_NAME    = "Ramo Pub & TeaHouse"
APP_VERSION = "1.0.0"
APP_LANG    = "az"

# PostgreSQL Connection
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME",     "ramo_pub"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}
DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# User Roles
ROLES = {
    "admin":   "Admin",
    "waiter":  "Ofisiant",
    "cashier": "Kassir",
}

# Table Status
TABLE_STATUS = {
    "available": "Bos",
    "occupied":  "Dolu",
    "reserved":  "Rezerv",
    "cleaning":  "Temizlenir",
}

# Order Status
ORDER_STATUS = {
    "new":       "Yeni",
    "preparing": "Hazirlanir",
    "ready":     "Hazirdir",
    "served":    "Verildi",
    "paid":      "Odenildi",
    "cancelled": "Legv edildi",
}

# Payment Methods
PAYMENT_METHODS = {
    "cash":   "Nagd",
    "card":   "Kart",
    "online": "Online",
}

# Theme
DEFAULT_THEME = "dark"

# Receipt Printer
PRINTER_ENABLED = False
PRINTER_PORT    = os.getenv("PRINTER_PORT", "COM1")

# Web Panel
WEB_HOST   = "0.0.0.0"
WEB_PORT   = 5000
SECRET_KEY = os.getenv("SECRET_KEY", "ramo-pub-secret-2024")
