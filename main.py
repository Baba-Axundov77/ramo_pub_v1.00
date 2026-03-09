#!/usr/bin/env python3
# main.py — Ramo Pub & TeaHouse — Modern Desktop Application
import sys
import os
import logging

# Add current directory to Python path first
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load .env file first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variable for PyQt6 on Windows
if sys.platform == 'win32':
    os.environ['QT_QPA_PLATFORM'] = 'windows'
    logger.info("Set QT_QPA_PLATFORM=windows for Windows compatibility")

def main():
    """Main function with Windows compatibility fixes"""
    try:
        logger.info("Starting Ramo Pub Desktop Application...")
        
        # Import configuration first
        from config import APP_NAME, APP_VERSION, DEFAULT_THEME, WEB_HOST, WEB_PORT
        logger.info(f"Configuration loaded: {APP_NAME} v{APP_VERSION}")
        
        # Import PyQt6
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtGui import QFont
        
        logger.info("PyQt6 imported successfully")
        
        # Import desktop modules
        from modules.desktop.api_client import DesktopAPIClient
        logger.info("Desktop modules imported")
        
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setFont(QFont("Segoe UI", 13))
        
        logger.info("QApplication created")
        
        # Load theme
        def load_theme(app, theme):
            base = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(base, "desktop", "themes", f"{theme}.qss")
            if os.path.exists(qss_path):
                try:
                    with open(qss_path, "r", encoding="utf-8") as f:
                        app.setStyleSheet(f.read())
                    logger.info(f"Theme loaded: {theme}")
                    return theme
                except Exception as e:
                    logger.error(f"Error loading theme {theme}: {e}")
            return "default"
        
        current_theme = load_theme(app, DEFAULT_THEME)
        logger.info(f"Current theme: {current_theme}")
        
        # Create API client - always use 127.0.0.1 for desktop
        api_client = DesktopAPIClient(f"http://127.0.0.1:{WEB_PORT}")
        logger.info("API client created")
        
        # Import and create login view
        from desktop.views.login_view import LoginView
        login_win = LoginView(api_client)
        logger.info("Login view created")
        
        # Add login success handler
        def on_login_success(user_data):
            logger.info(f"Login successful for user: {user_data.get('username', 'Unknown')}")
            login_win.hide()
            
            # Show success message
            from PyQt6.QtWidgets import QMessageBox
            msg_box = QMessageBox.information(
                login_win,
                "Login Successful",
                f"Welcome {user_data.get('full_name', user_data.get('username', 'User'))}!\n\n"
                f"Desktop application is now connected to the web API.\n"
                f"JWT authentication successful.\n"
                f"Real-time data synchronization active.",
                QMessageBox.StandardButton.Ok
            )
            
            # Create real main window with API integration
            from desktop.main_window import MainWindow
            from database.connection import init_database, get_db
            from modules.auth.auth_service import AuthService
            
            # Initialize database first
            ok, msg = init_database()
            if not ok:
                logger.error(f"Database initialization failed: {msg}")
                QMessageBox.critical(login_win, "Database Error", f"Database initialization failed: {msg}")
                return
            
            # Convert user_data dict to simple object for MainWindow compatibility
            class UserObject:
                def __init__(self, data):
                    self.id = data.get('id')
                    self.username = data.get('username')
                    self.full_name = data.get('full_name')
                    # Convert role string to enum for MainWindow compatibility
                    role_str = data.get('role', 'admin')
                    try:
                        from database.models import UserRole
                        self.role = UserRole(role_str) if role_str in [r.value for r in UserRole] else UserRole.ADMIN
                    except ImportError:
                        # Fallback if UserRole import fails
                        self.role = role_str
                    except Exception as e:
                        logger.warning(f"Error setting user role: {e}")
                        self.role = 'admin'
            
            user_obj = UserObject(user_data)
            db = get_db()  # Get database connection
            auth_service = AuthService()  # Create auth service
            
            # Set current_user in auth_service for API integration
            auth_service.current_user = user_obj
            
            # Create MainWindow with API client passed to constructor
            main_win = MainWindow(user_obj, db, auth_service, current_theme, api_client)
            
            # Set up API client properly (this will also set it for tables view)
            main_win.set_api_client(api_client)
            
            # Set token if available
            if hasattr(api_client, 'access_token') and api_client.access_token:
                logger.info("API token passed to MainWindow")
            else:
                logger.warning("No API token available in login client")
            
            # Add logout handler
            def logout():
                main_win.close()
                login_win.clear_fields()
                login_win.show()
            
            main_win.logout_requested.connect(logout)
            main_win.show()
            logger.info("Real MainWindow opened with API integration")
        
        # Connect signal
        login_win.login_success.connect(on_login_success)
        
        # Simple test without full main window
        login_win.setWindowTitle(APP_NAME)
        login_win.resize(920, 620)
        login_win.show()
        
        # Center window
        screen = app.primaryScreen().geometry()
        login_win.move(
            (screen.width() - login_win.width()) // 2,
            (screen.height() - login_win.height()) // 2,
        )
        
        logger.info("Login window displayed")
        logger.info("Application started successfully!")
        
        # Run application
        sys.exit(app.exec())
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please install required packages:")
        logger.error("  pip install PyQt6 requests sqlalchemy")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
