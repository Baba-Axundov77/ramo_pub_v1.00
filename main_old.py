#!/usr/bin/env python3
# main.py — Ramo Pub & TeaHouse — Modern Desktop Application
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox, QLabel
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QTimer, Qt, QThread
from PyQt6.QtCore import pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Modern configuration imports
from config import APP_NAME, APP_VERSION, DEFAULT_THEME, WEB_HOST, WEB_PORT
from modules.desktop.api_client import DesktopAPIClient
from modules.desktop.dashboard_thread import DashboardDataThread, MetricsUpdateThread


def load_theme(app: QApplication, theme: str) -> str:
    """Load theme with fallback to enterprise theme"""
    base = os.path.dirname(os.path.abspath(__file__))
    
    # Try to load specified theme
    qss_path = os.path.join(base, "desktop", "themes", f"{theme}.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            logger.info(f"Theme loaded: {theme}")
            return theme
        except Exception as e:
            logger.error(f"Error loading theme {theme}: {str(e)}")
    
    # Fallback to dark_enterprise theme
    enterprise_theme_path = os.path.join(base, "desktop", "themes", "dark_enterprise.qss")
    if os.path.exists(enterprise_theme_path):
        try:
            with open(enterprise_theme_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            logger.info("Fallback to dark_enterprise theme")
            return "dark_enterprise"
        except Exception as e:
            logger.error(f"Error loading enterprise theme: {str(e)}")
    
    logger.warning("No theme files found, using default style")
    return "default"


class OfflineModeManager:
    """Manages offline mode and connection status"""
    
    def __init__(self):
        self.is_offline = False
        self.connection_status_timer = QTimer()
        self.connection_status_timer.timeout.connect(self.check_connection)
        self.connection_status_timer.start(30000)  # Check every 30 seconds
        
    def check_connection(self):
        """Check server connection status"""
        try:
            # Simple connection check
            api_client = DesktopAPIClient(f"http://{WEB_HOST}:{WEB_PORT}")
            self.is_offline = not api_client.check_server_connection()
        except:
            self.is_offline = True
            
    def show_offline_warning(self, parent=None):
        """Show offline mode warning"""
        QMessageBox.warning(
            parent,
            "Çevrimdışı Mod",
            "Sunucu bağlantısı kesildi. Uygulama çevrimdışı modda çalışıyor.\n\n"
            "Bazı özellikler limited olabilir.\n"
            "Bağlantı yenilendiğinde otomatik olarak çevrimiçi moduna geçilecek.",
            QMessageBox.StandardButton.Ok
        )


class ModernMainWindow:
    """Enhanced main window with API integration"""
    
    def __init__(self, user_data, api_client, theme):
        self.user_data = user_data
        self.api_client = api_client
        self.theme = theme
        self.offline_manager = OfflineModeManager()
        
        # Dashboard threads
        self.dashboard_thread = None
        self.metrics_thread = None
        
        # Setup UI
        self.setup_ui()
        self.setup_dashboard_threads()
        
    def setup_ui(self):
        """Setup modern UI with enterprise theme"""
        # This would be implemented in the actual MainWindow class
        pass
        
    def setup_dashboard_threads(self):
        """Setup background threads for real-time data"""
        self.dashboard_thread = DashboardDataThread(self.api_client)
        self.dashboard_thread.data_received.connect(self.on_dashboard_data_received)
        self.dashboard_thread.error_occurred.connect(self.on_dashboard_error)
        self.dashboard_thread.connection_lost.connect(self.on_connection_lost)
        self.dashboard_thread.connection_restored.connect(self.on_connection_restored)
        self.dashboard_thread.start()
        
        self.metrics_thread = MetricsUpdateThread(self.api_client)
        self.metrics_thread.metrics_updated.connect(self.on_metrics_updated)
        self.metrics_thread.start()
        
    def on_dashboard_data_received(self, data):
        """Handle dashboard data updates"""
        # Update UI with new data
        pass
        
    def on_dashboard_error(self, error_msg):
        """Handle dashboard errors"""
        logger.error(f"Dashboard error: {error_msg}")
        
    def on_connection_lost(self):
        """Handle connection loss"""
        self.offline_manager.show_offline_warning()
        
    def on_connection_restored(self):
        """Handle connection restoration"""
        logger.info("Connection restored")
        
    def on_metrics_updated(self, metrics):
        """Handle metrics updates"""
        # Update specific UI elements
        pass
        
    def cleanup(self):
        """Cleanup threads and connections"""
        if self.dashboard_thread:
            self.dashboard_thread.stop()
            self.dashboard_thread.wait()
        if self.metrics_thread:
            self.metrics_thread.stop()
            self.metrics_thread.wait()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
#    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    app.setFont(QFont("Segoe UI", 13))

    current_theme = load_theme(app, DEFAULT_THEME)

    # ── Verilənlər bazası ─────────────────────────────────────────────────────
    from database.connection import init_database, get_db

    ok, msg = init_database()
    if not ok:
        QMessageBox.critical(
            None, "Verilənlər Bazası Xətası",
            f"PostgreSQL-ə qoşulmaq mümkün olmadı:\n\n{msg}\n\n"
            "Zəhmət olmasa:\n"
            "1. PostgreSQL serverinin işlədiyini yoxlayın\n"
            "2. .env faylındakı DB məlumatlarını yoxlayın\n"
            "3. 'ramo_pub' bazasının mövcud olduğunu yoxlayın"
        )
        sys.exit(1)

    db = get_db()

    # ── Default admin ─────────────────────────────────────────────────────────
    from modules.auth.auth_service import auth_service, create_default_admin
    create_default_admin(db)

    # ── Pəncərələr ────────────────────────────────────────────────────────────
    from desktop.views.login_view import LoginView
    from typing import Optional
    from desktop.main_window import MainWindow

    login_win = LoginView(db, auth_service)
    main_win: Optional[MainWindow] = None

    def on_login_success(user):
        nonlocal main_win, current_theme
        login_win.hide()
        # db və auth_service-i main window-a ötür
        main_win = MainWindow(user, db, auth_service, current_theme)

        def toggle_theme():
            nonlocal current_theme
            current_theme = "light" if current_theme == "dark" else "dark"
            load_theme(app, current_theme)
            main_win.theme_btn.setText("☀️" if current_theme == "dark" else "🌙")

        main_win.theme_btn.clicked.connect(toggle_theme)
        main_win.logout_requested.connect(on_logout)
        main_win.show()

    def on_logout():
        auth_service.logout()
        if main_win:
            main_win.close()
        login_win.clear_fields()
        login_win.show()

    login_win.login_success.connect(on_login_success)
    login_win.exit_app.connect(app.quit)
    login_win.setWindowTitle(APP_NAME)
    login_win.resize(920, 620)
    login_win.show()

    screen = app.primaryScreen().geometry()
    login_win.move(
        (screen.width() - login_win.width()) // 2,
        (screen.height() - login_win.height()) // 2,
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
