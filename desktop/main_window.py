# desktop/main_window.py — Əsas Pəncərə — Bütün Modullarla
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SidebarButton(QPushButton):
    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_text = icon_text
        self.label_text = label
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(52)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        icon_lbl = QLabel(self.icon_text)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
        icon_lbl.setFixedWidth(26)
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(icon_lbl)
        text_lbl = QLabel(self.label_text)
        text_lbl.setFont(QFont("Segoe UI", 11))
        text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(text_lbl)
        layout.addStretch()


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user, db, auth_service, theme: str = "dark"):
        super().__init__()
        self.current_user = user
        self.db = db
        self.auth = auth_service
        self.theme = theme
        self.nav_buttons = {}
        self._services = {}
        self._views = {}

        self.setWindowTitle(f"Ramo Pub & TeaHouse — {user.full_name}")
        self.setMinimumSize(1280, 780)
        self.showMaximized()

        self._init_services()
        self._seed_defaults()
        self._build_ui()
        self._navigate("dashboard")

    # ─────────────────────────────────────────────────────────────────────────

    def _init_services(self):
        from modules.tables.table_service import TableService
        from modules.menu.menu_service import MenuService
        from modules.orders.order_service import OrderService
        from modules.orders.workflow_service import OrderWorkflowService
        from modules.pos.pos_service import POSService
        from modules.inventory.inventory_service import InventoryService
        from modules.reservation.reservation_service import ReservationService
        from modules.staff.staff_service import StaffService
        from modules.reports.report_service import ReportService
        from modules.loyalty.loyalty_service import LoyaltyService
        from modules.printer.printer_service import PrinterService
        from modules.orders.kitchen_service import kitchen_service

        self._services["tables"] = TableService()
        self._services["menu"] = MenuService()
        self._services["orders"] = OrderService()
        self._services["order_workflow"] = OrderWorkflowService()
        self._services["pos"] = POSService()
        self._services["inventory"] = InventoryService()
        self._services["reservation"] = ReservationService()
        self._services["staff"] = StaffService()
        self._services["reports"] = ReportService()
        self._services["loyalty"] = LoyaltyService()
        self._services["printer"] = PrinterService()
        self._services["kitchen"] = kitchen_service

    def _seed_defaults(self):
        self._services["tables"].seed_defaults(self.db)
        self._services["menu"].seed_defaults(self.db)
        self._services["inventory"].seed_defaults(self.db)
        self._services["loyalty"].seed_defaults(self.db)

    # ── UI Qurulumu ───────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_h = QHBoxLayout(central)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(224)
        self.sidebar.setStyleSheet(
            "#sidebar { background-color: #141420; border-right: 1px solid #2E2E4E; }"
        )
        sidebar_v = QVBoxLayout(self.sidebar)
        sidebar_v.setContentsMargins(0, 0, 0, 0)
        sidebar_v.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedHeight(76)
        logo_frame.setStyleSheet("background:#0D0D18; border-bottom:1px solid #2E2E4E;")
        logo_v = QVBoxLayout(logo_frame)
        logo_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.setSpacing(8)
        ico = QLabel("🍺"); ico.setFont(QFont("Segoe UI Emoji", 22))
        txt = QLabel("Ramo"); txt.setFont(QFont("Georgia", 18, QFont.Weight.Bold))
        txt.setStyleSheet("color: #E8A045;")
        logo_row.addWidget(ico); logo_row.addWidget(txt)
        logo_v.addLayout(logo_row)
        sidebar_v.addWidget(logo_frame)
        sidebar_v.addSpacing(6)

        for key, icon, label in self._get_nav_items():
            btn = SidebarButton(icon, label)
            btn.setStyleSheet(self._sidebar_btn_style())
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            self.nav_buttons[key] = btn
            sidebar_v.addWidget(btn)

        sidebar_v.addStretch()

        user_frame = QFrame()
        user_frame.setFixedHeight(72)
        user_frame.setStyleSheet("background:#0D0D18; border-top:1px solid #2E2E4E;")
        user_v = QVBoxLayout(user_frame)
        user_v.setContentsMargins(14, 8, 14, 8)
        uname = QLabel(f"👤  {self.current_user.full_name}")
        uname.setStyleSheet("color:#F0EAD6; font-size:12px; font-weight:bold;")
        from config import ROLES
        urole = QLabel(ROLES.get(self.current_user.role.value, ""))
        urole.setStyleSheet("color:#8080A0; font-size:11px;")
        out_btn = QPushButton("Çıxış  →")
        out_btn.setFixedHeight(26); out_btn.setObjectName("secondaryBtn")
        out_btn.setFont(QFont("Segoe UI", 10))
        out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        out_btn.clicked.connect(self.logout_requested.emit)
        user_v.addWidget(uname); user_v.addWidget(urole); user_v.addWidget(out_btn)
        sidebar_v.addWidget(user_frame)
        main_h.addWidget(self.sidebar)

        # Sağ tərəf
        content_v = QVBoxLayout()
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(0)

        self.header = QFrame()
        self.header.setFixedHeight(52)
        self.header.setStyleSheet("background:#1C1C2E; border-bottom:1px solid #2E2E4E;")
        header_h = QHBoxLayout(self.header)
        header_h.setContentsMargins(22, 0, 22, 0)
        self.page_title = QLabel("İdarə Paneli")
        self.page_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.page_title.setStyleSheet("color:#F0EAD6;")
        header_h.addWidget(self.page_title)
        header_h.addStretch()
        self.theme_btn = QPushButton("☀️")
        self.theme_btn.setFixedSize(34, 34)
        self.theme_btn.setObjectName("secondaryBtn")
        self.theme_btn.setToolTip("Temanı dəyiş")
        header_h.addWidget(self.theme_btn)
        content_v.addWidget(self.header)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:#0D0D0D;")
        self._setup_pages()
        content_v.addWidget(self.stack)
        main_h.addLayout(content_v)

    def _get_nav_items(self):
        from database.models import UserRole
        all_items = [
            ("dashboard",    "📊", "İdarə Paneli"),
            ("tables",       "🪑", "Masalar"),
            ("orders",       "📋", "Sifarişlər"),
            ("menu",         "🍽️",  "Menyu"),
            ("pos",          "💳", "Kassa"),
            ("inventory",    "📦", "Anbar"),
            ("reservations", "📅", "Rezervasiyalar"),
            ("loyalty",      "⭐", "Loyallıq"),
            ("staff",        "👥", "İşçilər"),
            ("reports",      "📈", "Hesabatlar"),
            ("kitchen",      "🍳", "Mətbəx"),
            ("settings",     "⚙️",  "Tənzimləmələr"),
        ]
        role = self.current_user.role
        if role == UserRole.waiter:
            allowed = {"dashboard", "tables", "orders", "menu", "reservations"}
            return [i for i in all_items if i[0] in allowed]
        elif role == UserRole.cashier:
            allowed = {"dashboard", "pos", "reports"}
            return [i for i in all_items if i[0] in allowed]
        elif role == UserRole.kitchen:
            allowed = {"dashboard", "kitchen"}
            return [i for i in all_items if i[0] in allowed]
        return all_items

    def _setup_pages(self):
        from desktop.views.tables_view import TablesView
        from desktop.views.orders_view import OrdersView
        from desktop.views.menu_view import MenuView
        from desktop.views.inventory_view import InventoryView
        from desktop.views.reservation_view import ReservationView
        from desktop.views.staff_view import StaffView
        from desktop.views.reports_view import ReportsView

        # ── Masalar ───────────────────────────────────────────────────────────
        tables_view = TablesView(self.db, self._services["tables"], self.auth)
        tables_view.open_order.connect(self._open_order_for_table)
        tables_view.view_order.connect(self._view_existing_order)
        tables_view.open_payment.connect(self._open_payment)
        self._views["tables"] = tables_view

        # ── Sifarişlər ────────────────────────────────────────────────────────
        orders_view = OrdersView(
            self.db,
            self._services["orders"],
            self._services["menu"],
            self.auth,
            workflow_service=self._services["order_workflow"],
        )
        orders_view.payment_requested.connect(self._open_payment)
        self._views["orders"] = orders_view

        # ── Menyu ─────────────────────────────────────────────────────────────
        self._views["menu"] = MenuView(self.db, self._services["menu"], self.auth)

        # ── Anbar ─────────────────────────────────────────────────────────────
        self._views["inventory"] = InventoryView(
            self.db, self._services["inventory"], self.auth
        )

        # ── Rezervasiya ───────────────────────────────────────────────────────
        self._views["reservations"] = ReservationView(
            self.db, self._services["reservation"],
            self._services["tables"], self.auth
        )

        # ── İşçilər ───────────────────────────────────────────────────────────
        self._views["staff"] = StaffView(
            self.db, self._services["staff"], self.auth
        )

        # ── Hesabatlar ────────────────────────────────────────────────────────
        self._views["reports"] = ReportsView(self.db, self._services["reports"])

        # ── Dashboard ─────────────────────────────────────────────────────────
        self._views["dashboard"] = self._make_dashboard()

        # ── Loyallıq ──────────────────────────────────────────────────────────
        from desktop.views.loyalty_view import LoyaltyView
        self._views["loyalty"] = LoyaltyView(
            self.db, self._services["loyalty"], self.auth
        )

        # ── Kassa ─────────────────────────────────────────────────────────────
        from desktop.views.pos_dashboard_view import POSDashboardView
        self._views["pos"] = POSDashboardView(
            self.db,
            self._services["orders"],
            self._services["pos"],
            self._open_payment,
        )

        # ── Mətbəx ───────────────────────────────────────────────────────────
        from desktop.views.kitchen_view import KitchenView
        self._views["kitchen"] = KitchenView(self.db, self._services["kitchen"])

        # ── Tənzimləmələr ─────────────────────────────────────────────────────
        from desktop.views.settings_view import SettingsView
        self._views["settings"] = SettingsView()

        for widget in self._views.values():
            self.stack.addWidget(widget)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _make_dashboard(self):
        w = QWidget(); w.setStyleSheet("background:#0D0D0D;")
        v = QVBoxLayout(w)
        v.setContentsMargins(30, 24, 30, 24)
        v.setSpacing(20)

        greet = QLabel(f"Xoş gəldiniz, {self.current_user.full_name}! 👋")
        greet.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
        greet.setStyleSheet("color: #E8A045;")
        v.addWidget(greet)

        stats_row = QHBoxLayout(); stats_row.setSpacing(14)
        self.dash_stat_labels = {}
        for icon, title, val, color in [
            ("🪑", "Masalar",      "0",       "#3498DB"),
            ("📋", "Aktiv Sifariş", "0",       "#E74C3C"),
            ("💰", "Bugünkü Gəlir", "0.00 ₼",  "#2ECC71"),
            ("✅", "Ödənilmiş",    "0",       "#E8A045"),
        ]:
            card = QFrame()
            card.setFixedHeight(110)
            card.setStyleSheet(f"""
                QFrame {{background:#1C1C2E; border:1px solid {color}40; border-radius:14px;}}
            """)
            cv = QVBoxLayout(card); cv.setContentsMargins(18, 14, 18, 14); cv.setSpacing(4)
            icon_lbl = QLabel(f"{icon}  {title}")
            icon_lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold;")
            cv.addWidget(icon_lbl)
            val_lbl = QLabel(val)
            val_lbl.setFont(QFont("Georgia", 22, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color:{color};")
            self.dash_stat_labels[title] = val_lbl
            cv.addWidget(val_lbl)
            stats_row.addWidget(card)
        v.addLayout(stats_row)

        ref_btn = QPushButton("🔄  Statistikanı yenilə")
        ref_btn.setFixedHeight(36); ref_btn.setObjectName("secondaryBtn")
        ref_btn.setFixedWidth(200); ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.clicked.connect(self._refresh_dashboard)
        v.addWidget(ref_btn)

        quick_lbl = QLabel("Sürətli Keçid")
        quick_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        quick_lbl.setStyleSheet("color:#8080A0;")
        v.addWidget(quick_lbl)

        quick_row = QHBoxLayout(); quick_row.setSpacing(12)
        for icon, label, key, color in [
            ("🪑", "Masalara get", "tables", "#3498DB"),
            ("📋", "Sifarişlər", "orders", "#2ECC71"),
            ("🍽️", "Menyu idarəsi", "menu", "#9B59B6"),
            ("📈", "Hesabatlar", "reports", "#E8A045"),
        ]:
            qbtn = QPushButton(f"{icon}  {label}")
            qbtn.setFixedHeight(52); qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
            qbtn.setStyleSheet(f"""
                QPushButton {{background:#1C1C2E;color:{color};
                    border:1px solid {color}60;border-radius:10px;
                    font-size:12px;font-weight:bold;}}
                QPushButton:hover {{background:{color}20;border-color:{color};}}
            """)
            qbtn.clicked.connect(lambda _, k=key: self._navigate(k))
            quick_row.addWidget(qbtn)
        v.addLayout(quick_row)
        v.addStretch()
        return w

    def _refresh_dashboard(self):
        try:
            ts = self._services["tables"].get_stats(self.db)
            os = self._services["orders"].get_today_summary(self.db)
            self.dash_stat_labels["Masalar"].setText(str(ts["total"]))
            self.dash_stat_labels["Aktiv Sifariş"].setText(str(os["active_orders"]))
            self.dash_stat_labels["Bugünkü Gəlir"].setText(f"{os['total_revenue']:.2f} ₼")
            self.dash_stat_labels["Ödənilmiş"].setText(str(os["paid_orders"]))
        except Exception as e:
            print(f"Dashboard xəta: {e}")

    def _make_placeholder(self, icon, title, color):
        w = QWidget(); v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico = QLabel(icon); ico.setFont(QFont("Segoe UI Emoji", 56))
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(ico)
        lbl = QLabel(title); lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{color};"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl)
        sub = QLabel("Mərhələ 3-də əlavə ediləcək…")
        sub.setStyleSheet("color:#4A4A6A; font-size:12px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(sub)
        return w

    # ── Naviqasiya ────────────────────────────────────────────────────────────

    def _navigate(self, key: str):
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
        titles = {
            "dashboard": "İdarə Paneli", "tables": "Masa İdarəetməsi",
            "orders": "Sifarişlər", "menu": "Menyu İdarəsi",
            "pos": "Kassa & Ödəniş", "inventory": "Anbar & Stok",
            "reservations": "Rezervasiyalar", "loyalty": "Loyallıq",
            "staff": "İşçi İdarəsi", "reports": "Hesabatlar",
            "kitchen": "Mətbəx", "settings": "Tənzimləmələr",
        }
        self.page_title.setText(titles.get(key, key))
        if key == "dashboard":
            self._refresh_dashboard()
        if key in self._views:
            self.stack.setCurrentWidget(self._views[key])

    # ── Modullar arası əlaqə ──────────────────────────────────────────────────

    def _open_order_for_table(self, table):
        self._navigate("orders")
        ov = self._views.get("orders")
        if ov: ov.open_for_table(table)

    def _view_existing_order(self, order):
        self._navigate("orders")
        ov = self._views.get("orders")
        if ov and order.table: ov.open_for_table(order.table, existing_order=order)

    def _open_payment(self, order):
        from desktop.views.pos_view import PaymentView
        dlg = PaymentView(order, self.db, self._services["pos"], self.auth, self)
        dlg.payment_done.connect(self._on_payment_done)
        dlg.exec()

    def _on_payment_done(self, payment):
        tv = self._views.get("tables")
        if tv: tv._refresh()
        ov = self._views.get("orders")
        if ov:
            ov.current_order = None; ov.current_table = None
            ov.table_lbl.setText("Masa seçilməyib")
            ov._refresh_order(); ov._load_active_orders()
        self._navigate("tables")
        self._refresh_dashboard()

    @staticmethod
    def _sidebar_btn_style():
        return """
            QPushButton {
                background:transparent; color:#7070A0; border:none;
                border-left:3px solid transparent; border-radius:0;
                text-align:left; font-size:11px;
            }
            QPushButton:hover {
                background:#1A1A2A; color:#F0EAD6;
                border-left:3px solid #E8A04580;
            }
            QPushButton:checked {
                background:#1C1C2E; color:#E8A045;
                border-left:3px solid #E8A045; font-weight:bold;
            }
        """
