# config/__init__.py - Configuration Package
from .settings import Settings, DatabaseSettings, RedisSettings, FlaskSettings, LoggingSettings

# Legacy compatibility
ROLES = {
    "admin": "Admin",
    "manager": "Menecer", 
    "waiter": "Ofisiant",
    "cashier": "Kassir",
    "kitchen": "Kitchen"
}

ALLOW_NEGATIVE_STOCK = False  # Default:不允许负库存

# Restaurant Status Constants
TABLE_STATUS = {
    "available": "Mövcud",
    "occupied": "Məşğul", 
    "reserved": "Rezerv",
    "cleaning": "Təmizləmə",
    "maintenance": "Baxış"
}

ORDER_STATUS = {
    "new": "Yeni",
    "preparing": "Hazırlanır",
    "ready": "Hazırdır",
    "served": "Xidmət edildi",
    "paid": "Ödənilib",
    "cancelled": "Ləğv edilib"
}

PAYMENT_METHODS = {
    "cash": "Nağd",
    "card": "Kart",
    "online": "Online",
    "loyalty_points": "Loyallıq Xalı"
}

# Desktop Application Constants
APP_NAME = "Ramo Pub ERP"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Restaurant Management System"
DEFAULT_THEME = "luxury"
DEFAULT_LANGUAGE = "az"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Web Service Configuration
WEB_HOST = "localhost"
WEB_PORT = 5000
WEB_PROTOCOL = "http"
API_BASE_URL = f"{WEB_PROTOCOL}://{WEB_HOST}:{WEB_PORT}/api"

__all__ = ['Settings', 'DatabaseSettings', 'RedisSettings', 'FlaskSettings', 'LoggingSettings', 'ROLES', 'ALLOW_NEGATIVE_STOCK', 'TABLE_STATUS', 'ORDER_STATUS', 'PAYMENT_METHODS', 'APP_NAME', 'APP_VERSION', 'APP_DESCRIPTION', 'DEFAULT_THEME', 'DEFAULT_LANGUAGE', 'WINDOW_WIDTH', 'WINDOW_HEIGHT', 'WEB_HOST', 'WEB_PORT', 'WEB_PROTOCOL', 'API_BASE_URL']
