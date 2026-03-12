# src/core/config.py - Central Configuration and Path Management
import os
from pathlib import Path

# ═════════════════════════════════════════════════════════════
# PROJECT ROOT AND PATHS
# ═════════════════════════════════════════════════════════════

# Proyektin ana kökü (project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"

# Assets qovluğu (ana kökdə)
ASSETS_DIR = BASE_DIR / "assets"
TABLE_IMAGES_DIR = ASSETS_DIR / "table_images"
MENU_IMAGES_DIR = ASSETS_DIR / "menu_images"
RECEIPTS_DIR = ASSETS_DIR / "receipts"

# Upload qovluqları
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"

# ═════════════════════════════════════════════════════════════
# PATH UTILITIES
# ═════════════════════════════════════════════════════════════

def get_assets_path(*path_parts):
    """Assets qovluğu üçün dinamik yol"""
    return os.path.join(ASSETS_DIR, *path_parts)

def get_table_images_path(filename=""):
    """Table images üçün yol"""
    return os.path.join(TABLE_IMAGES_DIR, filename)

def get_menu_images_path(filename=""):
    """Menu images üçün yol"""
    return os.path.join(MENU_IMAGES_DIR, filename)

def get_receipts_path(filename=""):
    """Receipts üçün yol"""
    return os.path.join(RECEIPTS_DIR, filename)

def get_uploads_path(*path_parts):
    """Uploads üçün dinamik yol"""
    return os.path.join(UPLOADS_DIR, *path_parts)

def get_static_path(*path_parts):
    """Static fayllar üçün yol"""
    return os.path.join(STATIC_DIR, *path_parts)

# ═════════════════════════════════════════════════════════════
# PATH VALIDATION
# ═════════════════════════════════════════════════════════════

def ensure_directories():
    """Vacib qovluqları yarat"""
    directories = [
        ASSETS_DIR,
        TABLE_IMAGES_DIR,
        MENU_IMAGES_DIR,
        RECEIPTS_DIR,
        UPLOADS_DIR,
        STATIC_DIR,
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

def validate_assets_structure():
    """Assets strukturunu yoxla"""
    required_dirs = [
        ASSETS_DIR,
        TABLE_IMAGES_DIR,
        MENU_IMAGES_DIR,
        RECEIPTS_DIR,
    ]
    
    missing_dirs = []
    for directory in required_dirs:
        if not os.path.exists(directory):
            missing_dirs.append(str(directory))
    
    if missing_dirs:
        print(f"Missing directories: {missing_dirs}")
        return False
    
    return True

# ═════════════════════════════════════════════════════════════
# EXPORTED CONSTANTS
# ═══════════════════════════════════════════════════════════

# Path constants for easy import
__all__ = [
    'BASE_DIR',
    'SRC_DIR', 
    'ASSETS_DIR',
    'TABLE_IMAGES_DIR',
    'MENU_IMAGES_DIR',
    'RECEIPTS_DIR',
    'UPLOADS_DIR',
    'STATIC_DIR',
    'get_assets_path',
    'get_table_images_path',
    'get_menu_images_path',
    'get_receipts_path',
    'get_uploads_path',
    'get_static_path',
    'ensure_directories',
    'validate_assets_structure'
]

# ═════════════════════════════════════════════════════════════
# INITIALIZATION
# ═════════════════════════════════════════════════════════════

# Başlanğıcda qovluqları yarat
if __name__ == "__main__":
    ensure_directories()
    validate_assets_structure()
    print(f"Project Root: {BASE_DIR}")
    print(f"Assets Directory: {ASSETS_DIR}")
