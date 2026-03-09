#!/usr/bin/env python3
# simple_main.py — Simplified test for main.py
import sys
import os

print("Starting simplified main.py test...")

try:
    # Test basic imports
    from PyQt6.QtWidgets import QApplication
    from config import APP_NAME, APP_VERSION, WEB_HOST, WEB_PORT
    from modules.desktop.api_client import DesktopAPIClient
    
    print("Basic imports successful")
    print(f"   App: {APP_NAME} v{APP_VERSION}")
    print(f"   Web: {WEB_HOST}:{WEB_PORT}")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    print("QApplication created")
    
    # Test API client
    api_client = DesktopAPIClient(f"http://{WEB_HOST}:{WEB_PORT}")
    print("API client created")
    
    # Test login view import
    try:
        from desktop.views.login_view import LoginView
        login_view = LoginView(api_client)
        print("LoginView created with API client")
    except Exception as e:
        print(f"LoginView error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Simplified test completed successfully")
    
except ImportError as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"General error: {e}")
    import traceback
    traceback.print_exc()

print("Test finished.")
