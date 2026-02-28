#!/usr/bin/env python3
# main.py — Ramo Pub & TeaHouse — Başlanğıc Nöqtəsi
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
# from PyQt6.QtCore import Qt

from config import APP_NAME, APP_VERSION, DEFAULT_THEME


def load_theme(app: QApplication, theme: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base, "desktop", "themes", f"{theme}.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    return theme


def main():
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
