#!/usr/bin/env python3
# debug_main.py — Debug script for main.py issues
import sys
import os
import traceback

print("DEBUG: Starting main.py debug...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

try:
    print("DEBUG: Importing config...")
    from config import APP_NAME, APP_VERSION, DEFAULT_THEME, WEB_HOST, WEB_PORT
    print(f"DEBUG: Config loaded - {APP_NAME} v{APP_VERSION}")
    
    print("DEBUG: Importing desktop modules...")
    from modules.desktop.api_client import DesktopAPIClient
    from modules.desktop.dashboard_thread import DashboardDataThread, MetricsUpdateThread
    print("DEBUG: Desktop modules imported successfully")
    
    print("DEBUG: Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication, QMessageBox, QLabel
    from PyQt6.QtGui import QFont, QIcon
    from PyQt6.QtCore import QTimer, Qt, QThread
    from PyQt6.QtCore import pyqtSignal
    print("DEBUG: PyQt6 imported successfully")
    
    print("DEBUG: Testing API client...")
    api_client = DesktopAPIClient(f"http://{WEB_HOST}:{WEB_PORT}")
    print(f"DEBUG: API client created for {WEB_HOST}:{WEB_PORT}")
    
    print("DEBUG: All imports successful!")
    
except ImportError as e:
    print(f"DEBUG: ImportError: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"DEBUG: General error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("DEBUG: Debug script completed successfully")
