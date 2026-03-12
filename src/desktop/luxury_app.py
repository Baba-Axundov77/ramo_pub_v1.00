#!/usr/bin/env python3
"""
 ═══════════════════════════════════════════════════════════
   Ramo Pub PyQt6 Luxury Desktop Application
   Web-Desktop Visual Synchronization
   ═══════════════════════════════════════════════════════════
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# DPI Scaling for high-resolution monitors (4K support)
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QTextEdit, QTabWidget, QGroupBox, QStatusBar,
    QMenuBar, QMenu, QToolBar, QSplitter, QScrollArea, QFrame,
    QProgressBar, QSlider, QCheckBox, QRadioButton, QListWidget,
    QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox, QDateEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QThread, QObject, QSize, QRect,
    pyqtProperty, QPropertyAnimation, QEasingCurve, QUrl
)
from PyQt6.QtGui import (
    QFont, QFontDatabase, QIcon, QPalette, QColor, QPixmap,
    QPainter, QLinearGradient, QPen, QBrush, QRegion
)
from PyQt6.QtMultimedia import QSoundEffect

# Import matplotlib for charts
try:
    import matplotlib
    matplotlib.use('Qt6Agg')
    from matplotlib.backends.backend_qt6agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not available. Charts will be disabled.")


class LuxuryButton(QPushButton):
    """Luxury styled button with sound effects and enhanced interactions"""
    
    def __init__(self, text: str = "", sound_manager: Optional[SoundManager] = None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.sound_manager = sound_manager
        self.setup_luxury_style()
        self.setup_connections()
    
    def setup_luxury_style(self):
        """Setup luxury styling with DPI awareness"""
        self.setObjectName("luxury-button")
        # Ensure proper scaling on high DPI displays
        self.setMinimumSize(120, 40)
        
        # Set luxury font
        font = FontManager().get_inter_font(14, QFont.Weight.Bold)
        self.setFont(font)
    
    def setup_connections(self):
        """Setup click sound and visual feedback"""
        self.clicked.connect(self.play_click_sound)
        self.pressed.connect(self.add_press_feedback)
        self.released.connect(self.remove_press_feedback)
    
    def play_click_sound(self):
        """Play premium click sound"""
        if self.sound_manager:
            self.sound_manager.play_click()
    
    def add_press_feedback(self):
        """Add visual press feedback"""
        self.setStyleSheet("""
            QPushButton {
                transform: scale(0.98);
                opacity: 0.9;
            }
        """)
    
    def remove_press_feedback(self):
        """Remove press feedback animation"""
        self.setStyleSheet("")  # Reset to default QSS styling
    
    def set_primary_style(self):
        """Set primary button style"""
        self.setProperty("class", "primary")
        self.style().unpolish(self)
        self.style().polish(self)
    
    def set_secondary_style(self):
        """Set secondary button style"""
        self.setProperty("class", "secondary")
        self.style().unpolish(self)
        self.style().polish(self)


class SoundManager:
    """Manages premium sound effects for luxury experience"""
    
    def __init__(self):
        self.enabled = True
        self.click_sound = None
        self.success_sound = None
        self.setup_sounds()
    
    def setup_sounds(self):
        """Setup sound effects with fallback to system beep"""
        try:
            # Try to create premium click sound
            self.click_sound = QSoundEffect()
            # Generate a soft metal click sound programmatically
            # In production, you would load actual sound files
            self.click_sound.setSource(QUrl.fromLocalFile("sounds/click.wav"))
            
            # Success sound for payments
            self.success_sound = QSoundEffect()
            self.success_sound.setSource(QUrl.fromLocalFile("sounds/success.wav"))
            
        except Exception as e:
            print(f"Sound setup failed, using system beep: {e}")
            self.enabled = False
    
    def play_click(self):
        """Play premium click sound"""
        if not self.enabled:
            # Fallback to system beep
            QApplication.beep()
            return
        
        try:
            if self.click_sound:
                self.click_sound.play()
            else:
                # Generate soft beep programmatically
                QApplication.beep()
        except Exception:
            pass  # Silent fail
    
    def play_success(self):
        """Play success sound for payments"""
        if not self.enabled:
            # Fallback to system beep
            QApplication.beep()
            return
        
        try:
            if self.success_sound:
                self.success_sound.play()
            else:
                # Generate success beep
                QApplication.beep()
        except Exception:
            pass  # Silent fail
    
    def toggle_enabled(self):
        """Toggle sound effects on/off"""
        self.enabled = not self.enabled
        return self.enabled


class FontManager:
    """Manages font loading and application-wide font settings"""
    
    def __init__(self):
        self.font_db = QFontDatabase()
        self._load_fonts()
    
    def _load_fonts(self):
        """Load Inter and Playfair Display fonts"""
        # Try to load system fonts first
        self.inter_font = QFont("Inter", 12, QFont.Weight.Normal)
        self.playfair_font = QFont("Playfair Display", 16, QFont.Weight.Bold)
        
        # Check if fonts are available, fallback to system fonts
        if not self.font_db.hasFamily("Inter"):
            print("Inter font not found, using system font")
            self.inter_font = QFont("Segoe UI", 12, QFont.Weight.Normal)
        
        if not self.font_db.hasFamily("Playfair Display"):
            print("Playfair Display font not found, using system serif font")
            self.playfair_font = QFont("Times New Roman", 16, QFont.Weight.Bold)
    
    def get_inter_font(self, size: int = 12, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        """Get Inter font with specified size and weight"""
        font = QFont(self.inter_font)
        font.setPointSize(size)
        font.setWeight(weight)
        return font
    
    def get_playfair_font(self, size: int = 16, weight: QFont.Weight = QFont.Weight.Bold) -> QFont:
        """Get Playfair Display font with specified size and weight"""
        font = QFont(self.playfair_font)
        font.setPointSize(size)
        font.setWeight(weight)
        return font
    
    def get_mono_font(self, size: int = 14) -> QFont:
        """Get monospace font for numbers"""
        return QFont("Consolas", size, QFont.Weight.Bold)


class LuxuryCard(QFrame):
    """A luxury styled card widget with glass effect"""
    
    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.setObjectName("luxury-card")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        
        if self.title:
            title_label = QLabel(self.title)
            title_label.setObjectName("gold-accent")
            title_label.setFont(FontManager().get_playfair_font(18))
            layout.addWidget(title_label)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        layout.addWidget(self.content_widget)
    
    def add_widget(self, widget: QWidget):
        """Add a widget to the card content"""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Add a layout to the card content"""
        self.content_layout.addLayout(layout)


class StatCard(LuxuryCard):
    """A card for displaying statistics with luxury styling"""
    
    def __init__(self, title: str, value: str, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("stat-value")
        self.value_label.setFont(FontManager().get_mono_font(24))
        self.add_widget(self.value_label)
    
    def update_value(self, new_value: str):
        """Update the stat value with animation"""
        self.value_label.setText(new_value)


class TableCard(LuxuryCard):
    """A card representing a table with status"""
    
    def __init__(self, table_id: int, table_number: str, status: str = "available", 
                 amount: float = 0.0, parent: Optional[QWidget] = None):
        super().__init__(f"Masa {table_number}", parent)
        self.table_id = table_id
        self.table_number = table_number
        self.status = status
        self.amount = amount
        self.setup_table_ui()
    
    def setup_table_ui(self):
        # Table number
        number_label = QLabel(self.table_number)
        number_label.setFont(FontManager().get_mono_font(28))
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_label.setObjectName("gold-accent")
        self.add_widget(number_label)
        
        # Status
        status_label = QLabel(self.get_status_text())
        status_label.setFont(FontManager().get_inter_font(12))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(status_label)
        
        # Amount if occupied
        if self.status == "occupied" and self.amount > 0:
            amount_label = QLabel(f"{self.amount:.2f} ₼")
            amount_label.setFont(FontManager().get_mono_font(16))
            amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_label.setObjectName("gold-acent")
            self.add_widget(amount_label)
    
    def get_status_text(self) -> str:
        """Get status text in Azerbaijani"""
        status_map = {
            "available": "Boş",
            "occupied": "Dolu",
            "reserved": "Rezerv",
            "cleaning": "Təmizlik"
        }
        return status_map.get(self.status, self.status)
    
    def update_status(self, new_status: str, new_amount: float = 0.0):
        """Update table status and amount"""
        self.status = new_status
        self.amount = new_amount
        self.setProperty("status", new_status)
        self.setup_table_ui()


class OrderCard(LuxuryCard):
    """A card for displaying order information"""
    
    def __init__(self, order_data: Dict, parent: Optional[QWidget] = None):
        super().__init__(f"Order #{order_data.get('id', 'N/A')}", parent)
        self.order_data = order_data
        self.setup_order_ui()
    
    def setup_order_ui(self):
        # Customer info
        customer_label = QLabel(f"Customer: {self.order_data.get('customer', 'Walk-in')}")
        customer_label.setFont(FontManager().get_inter_font(14))
        self.add_widget(customer_label)
        
        # Items count
        items_label = QLabel(f"Items: {len(self.order_data.get('items', []))}")
        items_label.setFont(FontManager().get_inter_font(12))
        self.add_widget(items_label)
        
        # Total amount
        total = self.order_data.get('total', 0.0)
        total_label = QLabel(f"Total: {total:.2f} ₼")
        total_label.setFont(FontManager().get_mono_font(16))
        total_label.setObjectName("gold-acent")
        self.add_widget(total_label)
        
        # Status
        status = self.order_data.get('status', 'pending')
        self.setProperty("status", status)


class ChartWidget(QWidget):
    """A widget for displaying matplotlib charts with luxury styling"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.figure = None
        self.canvas = None
        self.setup_chart()
    
    def setup_chart(self):
        if not MATPLOTLIB_AVAILABLE:
            # Fallback to simple text if matplotlib is not available
            layout = QVBoxLayout(self)
            label = QLabel("Charts not available\n(Matplotlib required)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #94a3b8; font-size: 14px;")
            layout.addWidget(label)
            return
        
        # Create matplotlib figure with luxury styling
        self.figure = Figure(figsize=(8, 6), facecolor='#0f172a')
        self.canvas = FigureCanvas(self.figure)
        
        # Style the plot
        plt.style.use('dark_background')
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        
        # Create sample chart
        self.create_sample_chart()
    
    def create_sample_chart(self):
        """Create a sample luxury styled chart"""
        if not self.figure:
            return
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Sample data
        categories = ['Pizza', 'Drinks', 'Salads', 'Desserts']
        values = [45, 30, 15, 10]
        
        # Create bar chart with luxury colors
        bars = ax.bar(categories, values, color=['#c6a659', '#10b981', '#f59e0b', '#ef4444'])
        
        # Styling
        ax.set_facecolor('#1e293b')
        self.figure.patch.set_facecolor('#0f172a')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#c6a659')
        ax.spines['left'].set_color('#c6a659')
        ax.tick_params(colors='#94a3b8')
        ax.xaxis.label.set_color('#f1f5f9')
        ax.yaxis.label.set_color('#f1f5f9')
        
        self.canvas.draw()


class DashboardWidget(QWidget):
    """Main dashboard widget with luxury styling"""
    
    def __init__(self, sound_manager: Optional[SoundManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sound_manager = sound_manager
        self.setup_ui()
        self.setup_connections()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Ramo Pub Dashboard")
        title_label.setFont(FontManager().get_playfair_font(24))
        title_label.setObjectName("gold-accent")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Clock
        self.clock_label = QLabel()
        self.clock_label.setFont(FontManager().get_mono_font(16))
        self.clock_label.setObjectName("gold-accent")
        header_layout.addWidget(self.clock_label)
        
        layout.addLayout(header_layout)
        
        # Stats Cards
        stats_layout = QHBoxLayout()
        
        self.revenue_card = StatCard("Bugünkü Gəlir", "2,450.50 ₼")
        self.revenue_card.setObjectName("stat-card")
        stats_layout.addWidget(self.revenue_card)
        
        self.tables_card = StatCard("Aktiv Masalar", "12")
        self.tables_card.setObjectName("stat-card")
        stats_layout.addWidget(self.tables_card)
        
        self.orders_card = StatCard("Gözləyən Sifariş", "8")
        self.orders_card.setObjectName("stat-card")
        stats_layout.addWidget(self.orders_card)
        
        self.staff_card = StatCard("İşçi Heyəti", "15")
        self.staff_card.setObjectName("stat-card")
        stats_layout.addWidget(self.staff_card)
        
        layout.addLayout(stats_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tables section
        tables_widget = QWidget()
        tables_layout = QVBoxLayout(tables_widget)
        
        tables_title = QLabel("Masalar")
        tables_title.setFont(FontManager().get_playfair_font(18))
        tables_title.setObjectName("gold-accent")
        tables_layout.addWidget(tables_title)
        
        # Tables grid
        tables_grid = QScrollArea()
        tables_grid.setWidgetResizable(True)
        tables_grid_widget = QWidget()
        tables_grid_layout = QHBoxLayout(tables_grid_widget)
        
        # Sample table cards
        self.table_cards = []
        sample_tables = [
            (1, "1", "available", 0.0),
            (2, "2", "occupied", 45.50),
            (3, "3", "available", 0.0),
            (4, "4", "occupied", 78.00),
            (5, "5", "reserved", 0.0),
            (6, "6", "available", 0.0),
        ]
        
        for table_id, number, status, amount in sample_tables:
            card = TableCard(table_id, number, status, amount)
            self.table_cards.append(card)
            tables_grid_layout.addWidget(card)
        
        tables_grid_layout.addStretch()
        tables_grid.setWidget(tables_grid_widget)
        tables_layout.addWidget(tables_grid)
        
        splitter.addWidget(tables_widget)
        
        # Charts section
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        
        charts_title = QLabel("Statistika")
        charts_title.setFont(FontManager().get_playfair_font(18))
        charts_title.setObjectName("gold-accent")
        charts_layout.addWidget(charts_title)
        
        self.chart_widget = ChartWidget()
        charts_layout.addWidget(self.chart_widget)
        
        splitter.addWidget(charts_widget)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        # Recent orders
        orders_title = QLabel("Son Sifarişlər")
        orders_title.setFont(FontManager().get_playfair_font(18))
        orders_title.setObjectName("gold-acent")
        layout.addWidget(orders_title)
        
        self.orders_list = QListWidget()
        self.orders_list.setObjectName("order-list")
        layout.addWidget(self.orders_list)
        
        layout.addStretch()
    
    def setup_connections(self):
        """Setup signal connections"""
        # Update clock every second
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        # Update stats every 5 seconds
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(5000)
    
    def update_clock(self):
        """Update the clock display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.setText(current_time)
    
    def update_stats(self):
        """Update statistics with animation"""
        import random
        
        # Simulate revenue changes
        current_revenue = float(self.revenue_card.value_label.text().replace(" ₼", "").replace(",", ""))
        new_revenue = current_revenue + random.uniform(-50, 200)
        self.revenue_card.update_value(f"{new_revenue:,.2f} ₼")
        
        # Simulate order changes
        current_orders = int(self.orders_card.value_label.text())
        new_orders = max(0, current_orders + random.randint(-2, 3))
        self.orders_card.update_value(str(new_orders))
    
    def load_data(self):
        """Load initial data"""
        # Add sample orders
        sample_orders = [
            {"id": 1, "customer": "Əli Hüseynov", "items": ["Pizza", "Kola"], "total": 45.50, "status": "ready"},
            {"id": 2, "customer": "Nigar Əliyeva", "items": ["Salad", "Su"], "total": 18.00, "status": "pending"},
            {"id": 3, "customer": "Kamal Qasımov", "items": ["Burger", "Bira"], "total": 28.00, "status": "ready"},
        ]
        
        for order_data in sample_orders:
            order_item = QListWidgetItem(f"Order #{order_data['id']} - {order_data['customer']} - {order_data['total']:.2f} ₼")
            order_item.setData(Qt.ItemDataRole.UserRole, order_data)
            order_item.setProperty("status", order_data['status'])
            self.orders_list.addItem(order_item)


class LuxuryMainWindow(QMainWindow):
    """Main window with luxury styling and functionality"""
    
    def __init__(self):
        super().__init__()
        self.font_manager = FontManager()
        self.sound_manager = SoundManager()
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.apply_theme()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Ramo Pub - Luxury Management")
        self.setMinimumSize(1200, 800)
        
        # Create central widget
        self.dashboard = DashboardWidget(self.sound_manager)
        self.setCentralWidget(self.dashboard)
    
    def setup_menu_bar(self):
        """Setup the menu bar with luxury styling"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Fayl")
        
        new_action = file_menu.addAction("Yeni")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(lambda: self.sound_manager.play_click())
        
        open_action = file_menu.addAction("Aç")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(lambda: self.sound_manager.play_click())
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Çıx")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # View menu
        view_menu = menubar.addMenu("Görünüş")
        
        dashboard_action = view_menu.addAction("İdarə Paneli")
        dashboard_action.setShortcut("Ctrl+D")
        dashboard_action.triggered.connect(lambda: self.sound_manager.play_click())
        
        tables_action = view_menu.addAction("Masalar")
        tables_action.setShortcut("Ctrl+T")
        tables_action.triggered.connect(lambda: self.sound_manager.play_click())
        
        menu_action = view_menu.addAction("Menyu")
        menu_action.setShortcut("Ctrl+M")
        menu_action.triggered.connect(lambda: self.sound_manager.play_click())
        
        # Settings menu
        settings_menu = menubar.addMenu("Qurğular")
        
        sound_toggle_action = settings_menu.addAction("Səs Effektləri")
        sound_toggle_action.setCheckable(True)
        sound_toggle_action.setChecked(self.sound_manager.enabled)
        sound_toggle_action.triggered.connect(self.toggle_sounds)
        
        # Help menu
        help_menu = menubar.addMenu("Yardım")
        
        about_action = help_menu.addAction("Haqqında")
        about_action.triggered.connect(self.show_about)
        about_action.triggered.connect(lambda: self.sound_manager.play_click())
    
    def toggle_sounds(self):
        """Toggle sound effects on/off"""
        enabled = self.sound_manager.toggle_enabled()
        print(f"Sound effects {'enabled' if enabled else 'disabled'}")
        # Update status bar indicator
        if hasattr(self, 'sound_status_label'):
            self.sound_status_label.setText("🔊" if enabled else "🔇")
    
    def setup_status_bar(self):
        """Setup the status bar"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Add permanent widgets
        self.user_label = QLabel("İstifadəçi: Admin")
        status_bar.addPermanentWidget(self.user_label)
        
        self.connection_label = QLabel("Bağlantı: Qoşuldu")
        status_bar.addPermanentWidget(self.connection_label)
        
        # Sound status indicator
        self.sound_status_label = QLabel("🔊" if self.sound_manager.enabled else "🔇")
        status_bar.addPermanentWidget(self.sound_status_label)
    
    def apply_theme(self):
        """Apply the luxury theme"""
        # Load the QSS stylesheet
        theme_path = os.path.join(os.path.dirname(__file__), "luxury_theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        else:
            print(f"Warning: Theme file not found at {theme_path}")
            # Apply inline fallback theme
            self.apply_fallback_theme()
    
    def apply_fallback_theme(self):
        """Apply fallback theme if QSS file is not found"""
        fallback_theme = """
        QMainWindow {
            background-color: #020617;
            color: #f1f5f9;
        }
        QWidget {
            background-color: rgba(15, 23, 42, 180);
            border: 1px solid rgba(198, 166, 89, 50);
            border-radius: 12px;
            color: #f1f5f9;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c6a659, stop:1 #a68a4b);
            color: #020617;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px 20px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d4af37, stop:1 #b8941f);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        """
        self.setStyleSheet(fallback_theme)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect dashboard signals
        pass
    
    def show_about(self):
        """Show about dialog"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("Haqqında")
        about_dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(about_dialog)
        
        title = QLabel("Ramo Pub Luxury Management")
        title.setFont(self.font_manager.get_playfair_font(20))
        title.setObjectName("gold-accent")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        description = QLabel("Premium restaurant management system with luxury design")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Sound toggle in about dialog
        sound_checkbox = QCheckBox("Səs Effektləri Aktiv")
        sound_checkbox.setChecked(self.sound_manager.enabled)
        sound_checkbox.toggled.connect(self.sound_manager.toggle_enabled)
        layout.addWidget(sound_checkbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(about_dialog.accept)
        buttons.accepted.connect(lambda: self.sound_manager.play_success())  # Success sound on close
        layout.addWidget(buttons)
        
        about_dialog.exec()


class ThemeManager:
    """Manages theme switching and updates"""
    
    def __init__(self, app: QApplication):
        self.app = app
        self.current_theme = "luxury"
        self.font_manager = FontManager()
    
    def apply_theme(self, theme_name: str = "luxury"):
        """Apply a specific theme"""
        if theme_name == "luxury":
            self.apply_luxury_theme()
        elif theme_name == "light":
            self.apply_light_theme()
        else:
            print(f"Unknown theme: {theme_name}")
    
    def apply_luxury_theme(self):
        """Apply the luxury theme"""
        theme_path = os.path.join(os.path.dirname(__file__), "luxury_theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                self.app.setStyleSheet(f.read())
        else:
            print("Luxury theme file not found")
    
    def apply_light_theme(self):
        """Apply a light theme for comparison"""
        light_theme = """
        QMainWindow {
            background-color: #ffffff;
            color: #1f2937;
        }
        QWidget {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            color: #1f2937;
        }
        QPushButton {
            background-color: #3b82f6;
            color: #ffffff;
            border-radius: 6px;
            padding: 8px 16px;
        }
        """
        self.app.setStyleSheet(light_theme)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Ramo Pub")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Ramo Pub")
    
    # Set application icon if available
    if os.path.exists("icon.png"):
        app.setWindowIcon(QIcon("icon.png"))
    
    # Create theme manager
    theme_manager = ThemeManager(app)
    theme_manager.apply_theme("luxury")
    
    # Create and show main window
    window = LuxuryMainWindow()
    window.show()
    
    # Start the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
