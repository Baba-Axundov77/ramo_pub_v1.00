# desktop/views/tables_view.py — Masa İdarəetməsi UI
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QDialog, QLineEdit, QSpinBox, QComboBox,
    QMessageBox, QSizePolicy, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QMimeData, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QDrag, QPixmap

from config import TABLE_STATUS


class TableCard(QFrame):
    """Tıklanabilən masa kartı."""
    clicked = pyqtSignal(object)  # Table obj

    STATUS_COLORS = {
        "available": ("#1a3a1a", "#2ECC71", "Boş"),
        "occupied": ("#3a1a1a", "#E74C3C", "Dolu"),
        "reserved": ("#2a2a1a", "#F39C12", "Rezerv"),
        "cleaning": ("#1a2a3a", "#3498DB", "Təmizlənir"),
        "payment_pending": ("#4a2a1a", "#F39C12", "Ödeme Bekleniyor"),
    }

    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.setFixedSize(140, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self.refresh(table)

        # Animation setup
        self.animation = QPropertyAnimation(self, b"sheetColor")
        self.animation.setDuration(1000)
        self.animation.setLoopCount(3)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Drop shadow effect
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setXOffset(0)
        self.shadow_effect.setYOffset(5)
        self.shadow_effect.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.shadow_effect)

        # Initially hide shadow
        self.shadow_effect.setEnabled(False)

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.num_lbl = QLabel()
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_lbl.setFont(QFont("Georgia", 26, QFont.Weight.Bold))
        v.addWidget(self.num_lbl)

        from desktop.views.widgets.image_picker import RoundedImageLabel
        self.image_lbl = RoundedImageLabel(
            None, width=92, height=56, radius=10,
            placeholder_icon="🪑", placeholder_text=""
        )
        self.image_lbl.setVisible(False)
        v.addWidget(self.image_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        self.name_lbl = QLabel()
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setFont(QFont("Segoe UI", 9))
        v.addWidget(self.name_lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.1);")
        v.addWidget(sep)

        # Order summary labels
        self.order_summary_lbl = QLabel()
        self.order_summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.order_summary_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.order_summary_lbl.setStyleSheet("color: rgba(255,255,255,0.8);")
        v.addWidget(self.order_summary_lbl)

        self.time_lbl = QLabel()
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_lbl.setFont(QFont("Segoe UI", 7))
        self.time_lbl.setStyleSheet("color: rgba(255,255,255,0.6);")
        v.addWidget(self.time_lbl)

        self.status_lbl = QLabel()
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        v.addWidget(self.status_lbl)

        self.cap_lbl = QLabel()
        self.cap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cap_lbl.setFont(QFont("Segoe UI", 8))
        self.cap_lbl.setStyleSheet("color: rgba(255,255,255,0.5);")
        v.addWidget(self.cap_lbl)

    def refresh(self, table):
        self.table = table
        # Handle enum status properly
        if hasattr(table.status, 'value'):
            status = table.status.value
        else:
            status = str(table.status)

        # Store last status for change detection
        self.last_status = status

        print(f"TableCard refresh: table {table.number}, status={status}")

        bg, accent, label = self.STATUS_COLORS.get(status, ("#252535", "#8080A0", status))
        self.setStyleSheet(f"""
            TableCard {{
                background: {bg};
                border: 2px solid {accent};
                border-radius: 12px;
            }}
            TableCard:hover {{
                border: 2px solid white;
                background: {bg}CC;
            }}
        """)
        self.num_lbl.setText(str(table.number))
        self.num_lbl.setStyleSheet(f"color: {accent};")

        image_path = getattr(table, "image_path", None)
        if image_path:
            self.image_lbl.set_image(image_path)
            self.image_lbl.setVisible(True)
            self.num_lbl.setStyleSheet(f"color: {accent}; font-size: 18px;")
        else:
            self.image_lbl.setVisible(False)
            self.num_lbl.setStyleSheet(f"color: {accent};")

        self.name_lbl.setText(getattr(table, "name", f"Masa {table.number}"))
        self.name_lbl.setStyleSheet("color: rgba(255,255,255,0.7);")
        self.status_lbl.setText(label)

        # Update order summary for occupied tables
        if status == "occupied":
            self._load_order_summary()
        else:
            self.order_summary_lbl.setText("")
            self.time_lbl.setText("")

        self.cap_lbl.setText(str(getattr(table, "capacity", 4)))
        self._update_capacity_color(status)

    def _load_order_summary(self):
        """Load order summary for occupied table"""
        try:
            # Get parent TablesView to access database
            parent_view = self.parent()
            while parent_view and not hasattr(parent_view, 'db'):
                parent_view = parent_view.parent()

            if parent_view and hasattr(parent_view, 'db'):
                from database.models import Order
                from datetime import datetime, timezone

                db = parent_view.db
                active_orders = db.query(Order).filter(
                    Order.table_id == self.table.id,
                    Order.status.in_(['new', 'preparing', 'ready', 'served'])
                ).all()

                if active_orders:
                    # Calculate total amount
                    total_amount = sum(order.total or 0 for order in active_orders)

                    # Calculate time since first order
                    first_order = min(active_orders, key=lambda x: x.created_at)
                    # Handle timezone-aware and naive datetimes
                    now = datetime.now(timezone.utc) if first_order.created_at.tzinfo else datetime.now()
                    time_diff = now - first_order.created_at
                    minutes = int(time_diff.total_seconds() / 60)

                    # Update labels
                    self.order_summary_lbl.setText(f"₺{total_amount:.2f}")
                    if minutes < 60:
                        self.time_lbl.setText(f"{minutes} dəqiqədir")
                    else:
                        hours = minutes // 60
                        mins = minutes % 60
                        self.time_lbl.setText(f"{hours}s {mins}dəq")
                else:
                    self.order_summary_lbl.setText("")
                    self.time_lbl.setText("")
        except Exception as e:
            print(f"Error loading order summary: {e}")
            self.order_summary_lbl.setText("")
            self.time_lbl.setText("")

    def _update_capacity_color(self, status):
        """Update capacity label color based on status"""
        if status == "occupied":
            self.cap_lbl.setStyleSheet("color: rgba(255,255,255,0.7);")
        else:
            self.cap_lbl.setStyleSheet("color: rgba(255,255,255,0.5);")

    def start_payment_animation(self):
        """Start blinking animation for payment pending"""
        if hasattr(self, 'animation'):
            bg, accent, _ = self.STATUS_COLORS.get("payment_pending", ("#4a2a1a", "#F39C12", ""))
            normal_color = f"border: 2px solid {accent};"
            blink_color = f"border: 2px solid #FFD700;"

            self.animation.setKeyValues([
                (0.0, normal_color),
                (0.5, blink_color),
                (1.0, normal_color)
            ])
            self.animation.start()

    def stop_payment_animation(self):
        """Stop payment animation"""
        if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.State.Running:
            self.animation.stop()

    # Property for animation support
    def get_sheet_color(self):
        """Getter for sheetColor property used in QPropertyAnimation"""
        return self.styleSheet()

    def set_sheet_color(self, style):
        """Setter for sheetColor property used in QPropertyAnimation"""
        self.setStyleSheet(style)

    sheetColor = pyqtProperty(str, get_sheet_color, set_sheet_color)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Start drag for occupied tables
            if hasattr(self.table, 'status') and hasattr(self.table.status, 'value'):
                if self.table.status.value == "occupied":
                    self._start_drag(event)
                else:
                    self.clicked.emit(self.table)
            else:
                self.clicked.emit(self.table)

    def _start_drag(self, event):
        """Start drag operation for occupied table"""
        drag = QDrag(self)
        mime_data = QMimeData()

        # Set table data
        mime_data.setText(f"table_{self.table.id}_{self.table.number}")
        drag.setMimeData(mime_data)

        # Create drag pixmap
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())

        # Execute drag
        drop_action = drag.exec(Qt.DropAction.MoveAction)

        if drop_action == Qt.DropAction.MoveAction:
            print(f"Table {self.table.number} moved")

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag and hover effects"""
        if hasattr(self.table, 'status') and hasattr(self.table.status, 'value'):
            if self.table.status.value == "occupied":
                # Show drag cursor
                self.setCursor(Qt.CursorShape.DragMoveCursor)
            else:
                # Show hand cursor and enable shadow for hover
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.shadow_effect.setEnabled(True)
                self.shadow_effect.setBlurRadius(20)
                self.shadow_effect.setYOffset(8)

    def mouseReleaseEvent(self, event):
        """Reset cursor and shadow after drag"""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shadow_effect.setEnabled(False)

    def enterEvent(self, event):
        """Handle mouse enter - show shadow effect"""
        if hasattr(self.table, 'status') and hasattr(self.table.status, 'value'):
            if self.table.status.value != "occupied":
                self.shadow_effect.setEnabled(True)
                # Animate shadow appearance
                self.shadow_effect.setBlurRadius(20)
                self.shadow_effect.setYOffset(8)

    def leaveEvent(self, event):
        """Handle mouse leave - hide shadow effect"""
        self.shadow_effect.setEnabled(False)


class TableActionDialog(QDialog):
    """Masa üzərində əməliyyat dialoqu."""

    def __init__(self, table, active_order, auth, parent=None):
        super().__init__(parent)
        self.table = table
        self.active_order = active_order
        self.auth = auth
        self.chosen_action = None

        self.setWindowTitle(f"Masa #{table.number}")
        self.setModal(True)
        self.setFixedWidth(320)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        # Başlıq
        title = QLabel(f"🪑  Masa #{self.table.number}  —  {self.table.name}")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #E8A045;")
        v.addWidget(title)

        status_val = self.table.status.value
        colors = {"available": "#2ECC71", "occupied": "#E74C3C",
                  "reserved": "#F39C12", "cleaning": "#3498DB"}
        status_lbl = QLabel(f"Status: {TABLE_STATUS.get(status_val, status_val)}")
        status_lbl.setStyleSheet(f"color: {colors.get(status_val, '#fff')}; font-size:11px;")
        v.addWidget(status_lbl)

        if self.active_order:
            order_lbl = QLabel(f"📋 Aktiv sifariş: #{self.active_order.id}  |  {self.active_order.total:.2f} ₼")
            order_lbl.setStyleSheet("color: #F39C12; font-size: 11px; padding: 6px; "
                                    "background: rgba(243,156,18,0.1); border-radius:6px;")
            v.addWidget(order_lbl)

        sep = QFrame();
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2E2E4E;");
        v.addWidget(sep)

        # Əməliyyat düymələri
        actions = []
        status = self.table.status.value

        if status == "available":
            actions.append(("📋  Yeni Sifariş", "new_order", "#2ECC71"))
            actions.append(("📅  Rezerv et", "reserve", "#F39C12"))
        elif status == "occupied":
            actions.append(("📋  Sifarişə bax", "view_order", "#3498DB"))
            actions.append(("💳  Ödəniş al", "payment", "#E8A045"))
            actions.append(("🔀  Masa köçür", "move", "#9B59B6"))
        elif status == "reserved":
            actions.append(("✅  Müştəri gəldi", "occupy", "#2ECC71"))
            actions.append(("❌  Rezervi ləğv et", "cancel_reserve", "#E74C3C"))
        elif status == "cleaning":
            actions.append(("✅  Təmizlik bitti", "set_available", "#2ECC71"))

        actions.append(("🧹  Təmizlənir", "set_cleaning", "#3498DB"))

        for label, action, color in actions:
            btn = QPushButton(label)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.05);
                    color: {color};
                    border: 1px solid {color}60;
                    border-radius: 8px;
                    text-align: left;
                    padding: 0 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {color}20;
                    border: 1px solid {color};
                }}
            """)
            btn.clicked.connect(lambda _, a=action: self._choose(a))
            v.addWidget(btn)

        # Admin üçün tənzimləmə
        if self.auth.is_admin():
            sep2 = QFrame();
            sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet("background:#2E2E4E;");
            v.addWidget(sep2)
            edit_btn = QPushButton("⚙️  Masanı redaktə et")
            edit_btn.setFixedHeight(36)
            edit_btn.setObjectName("secondaryBtn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self._choose("edit"))
            v.addWidget(edit_btn)

        cancel_btn = QPushButton("Bağla")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton{background:transparent;color:#606080;"
                                 "border:1px solid #606080;border-radius:8px;}"
                                 "QPushButton:hover{color:#F0EAD6;border-color:#F0EAD6;}")
        cancel_btn.clicked.connect(self.reject)
        v.addWidget(cancel_btn)

    def _choose(self, action):
        self.chosen_action = action
        self.accept()


class AddTableDialog(QDialog):
    """Yeni masa əlavə et / mövcud masanı redaktə et — şəkil dəstəyi ilə."""

    def __init__(self, table=None, parent=None):
        super().__init__(parent)
        self.table = table
        self.setWindowTitle("Masa əlavə et" if not table else "Masanı redaktə et")
        self.setModal(True)
        self.setFixedWidth(420)
        self._build()
        if table:
            self._fill(table)

    def _build(self):
        from desktop.views.widgets.image_picker import ImagePickerWidget, TABLE_IMGS
        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(20, 20, 20, 20)

        def lbl(text):
            l = QLabel(text)
            l.setObjectName("loginLabel")
            return l

        # Şəkil seçici — yuxarıda mərkəzdə
        img_lbl = lbl("MASA ŞƏKLİ")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(img_lbl)

        self.img_picker = ImagePickerWidget(
            dest_dir=TABLE_IMGS,
            image_path=self.table.image_path if self.table else None,
            prefix=f"table_{self.table.id if self.table else 'new'}",
            preview_w=220,
            preview_h=140,
            placeholder_icon="🪑",
            placeholder_text="Masa şəkli yoxdur",
        )
        v.addWidget(self.img_picker, 0, Qt.AlignmentFlag.AlignHCenter)

        sep = QFrame();
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2E2E4E; margin: 4px 0;")
        v.addWidget(sep)

        # Form sahələri
        row1 = QHBoxLayout();
        row1.setSpacing(10)
        n1 = QVBoxLayout()
        n1.addWidget(lbl("MASA NÖMRƏSİ"))
        self.num_spin = QSpinBox()
        self.num_spin.setRange(1, 999)
        self.num_spin.setFixedHeight(38)
        n1.addWidget(self.num_spin)
        row1.addLayout(n1)

        n2 = QVBoxLayout()
        n2.addWidget(lbl("TUTUMLULUQ (nəfər)"))
        self.cap_spin = QSpinBox()
        self.cap_spin.setRange(1, 30)
        self.cap_spin.setValue(4)
        self.cap_spin.setFixedHeight(38)
        n2.addWidget(self.cap_spin)
        row1.addLayout(n2)
        v.addLayout(row1)

        v.addWidget(lbl("AD (İstəyə bağlı)"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("VIP 1, Bağ Masası...")
        self.name_input.setFixedHeight(38)
        v.addWidget(self.name_input)

        v.addWidget(lbl("MƏRTƏBƏ"))
        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(1, 10)
        self.floor_spin.setFixedHeight(38)
        v.addWidget(self.floor_spin)

        row = QHBoxLayout()
        save_btn = QPushButton("💾  Yadda saxla")
        save_btn.setFixedHeight(42)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42)
        cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        row.addWidget(save_btn)
        row.addWidget(cancel)
        v.addLayout(row)

    def _fill(self, table):
        self.num_spin.setValue(table.number)
        self.name_input.setText(table.name or "")
        self.cap_spin.setValue(table.capacity)
        self.floor_spin.setValue(table.floor or 1)
        if table.image_path:
            self.img_picker.set_image_path(table.image_path)

    def get_data(self):
        return {
            "number": self.num_spin.value(),
            "name": self.name_input.text().strip() or None,
            "capacity": self.cap_spin.value(),
            "floor": self.floor_spin.value(),
            "image_path": self.img_picker.get_image_path(),
        }


class TablesView(QWidget):
    """
    Masa İdarəetməsi — əsas görünüş.
    Siqnallar:
        open_order(table)   — yeni sifariş aç
        view_order(order)   — mövcud sifarişi göstər
        open_payment(order) — ödəniş ekranına keç
    """
    open_order = pyqtSignal(object)
    view_order = pyqtSignal(object)
    open_payment = pyqtSignal(object)

    def __init__(self, db, table_service, auth_service, api_client=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.svc = table_service
        self.auth = auth_service
        self.api_client = api_client  # Add API client for real-time updates
        self.parent_window = parent  # Store parent reference
        self.table_cards = {}  # Use table_cards as required for proper caching
        self.cols = 6  # Grid column count as class attribute

        self._build_ui()
        self._build_table_grid()  # Build table grid only once
        self._refresh()

        # Enable drop events
        self.setAcceptDrops(True)

        # Hər 30 san. avtomatik yenilə
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(30000)

    def _build_table_grid(self):
        """Build table grid only once during initialization"""
        # Get initial tables from database
        tables = self.svc.get_all(self.db)
        
        print(f"Building initial table grid with {len(tables)} tables")
        
        # Create table cards for all initial tables
        for i, table in enumerate(tables):
            card = TableCard(table, self)
            card.clicked.connect(self._on_table_click)
            self.table_cards[table.id] = card
            
            # Add to grid
            row, col = i // self.cols, i % self.cols
            self.grid.addWidget(card, row, col)
            print(f"Created table {table.id} at position ({row}, {col})")
        
        # Update statistics
        stats = self.svc.get_stats(self.db)
        self.stat_labels["total"].setText(f"🪑  Cəmi: {stats['total']}")
        self.stat_labels["available"].setText(f"✅  Boş: {stats['available']}")
        self.stat_labels["occupied"].setText(f"🔴  Dolu: {stats['occupied']}")
        self.stat_labels["reserved"].setText(f"📅  Rezerv: {stats['reserved']}")
        
        print(f"Initial table grid built with {len(self.table_cards)} tables")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        # Statistika badges
        self.stat_labels = {}
        for key, color, icon in [
            ("total", "#8080A0", "🪑"),
            ("available", "#2ECC71", "✅"),
            ("occupied", "#E74C3C", "🔴"),
            ("reserved", "#F39C12", "📅"),
        ]:
            badge = QLabel()
            badge.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255,255,255,0.05);
                    border: 1px solid {color}60;
                    color: {color};
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
            self.stat_labels[key] = badge
            toolbar.addWidget(badge)

        toolbar.addStretch()

        # Refresh düyməsi
        ref_btn = QPushButton("🔄  Yenilə")
        ref_btn.setFixedHeight(36)
        ref_btn.setObjectName("secondaryBtn")
        ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.clicked.connect(self._refresh)
        toolbar.addWidget(ref_btn)

        if self.auth.is_admin():
            add_btn = QPushButton("➕  Masa əlavə et")
            add_btn.setFixedHeight(36)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_table)
            toolbar.addWidget(add_btn)

        root.addLayout(toolbar)

        # Mərtəbə seçimi
        floor_row = QHBoxLayout()
        self.floor_btns = {}
        for floor, label in [(0, "Hamısı"), (1, "1-ci Mərtəbə"), (2, "2-ci Mərtəbə")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(floor == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #8080A0;
                    border: 1px solid #3A3A5A; border-radius: 6px; padding: 0 16px; }
                QPushButton:checked { background: #E8A045; color: #0D0D0D;
                    border-color: #E8A045; font-weight: bold; }
                QPushButton:hover:!checked { border-color: #E8A045; color: #E8A045; }
            """)
            btn.clicked.connect(lambda _, f=floor: self._filter_floor(f))
            self.floor_btns[floor] = btn
            floor_row.addWidget(btn)
        floor_row.addStretch()
        root.addLayout(floor_row)

        # ── Masa Grid ─────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(4, 4, 4, 4)

        scroll.setWidget(self.grid_widget)
        root.addWidget(scroll)

        # ── Rəng açıqlaması ───────────────────────────────────────────────────
        legend = QHBoxLayout()
        legend.addStretch()
        for color, label in [("#2ECC71", "Boş"), ("#E74C3C", "Dolu"),
                             ("#F39C12", "Rezerv"), ("#3498DB", "Təmizlənir")]:
            dot = QLabel(f"●  {label}")
            dot.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addSpacing(12)
        root.addLayout(legend)

    # ── Məlumat yükləmə ───────────────────────────────────────────────────────

    def set_api_client(self, api_client):
        """Set API client after MainWindow has it"""
        self.api_client = api_client
        self.parent_window = api_client  # Store reference

    def _refresh(self):
        # Force database refresh for now since API authentication has issues
        self._refresh_from_db()

        # TODO: Fix API authentication and re-enable API refresh
        # Try API first, fallback to database
        # if self.api_client and hasattr(self.api_client, 'access_token') and self.api_client.access_token:
        #     self._refresh_from_api()
        # else:
        #     # If API client is None or no token, try to get it from parent window
        #     if self.parent_window and hasattr(self.parent_window, 'api_client') and self.parent_window.api_client:
        #         self.api_client = self.parent_window.api_client
        #         if hasattr(self.api_client, 'access_token') and self.api_client.access_token:
        #             self._refresh_from_api()
        #             return
        #     # Fallback to database
        #     self._refresh_from_db()

    def _refresh_from_api(self):
        """Refresh tables data from API with TokenManager integration"""
        try:
            import requests
            import json
            from modules.auth.token_manager import token_manager

            # Use TokenManager for better token handling
            if self.api_client and hasattr(self.api_client, 'access_token') and self.api_client.access_token:
                # Validate token with TokenManager
                if token_manager.is_token_valid(self.api_client.access_token):
                    headers = {'Authorization': f'Bearer {self.api_client.access_token}'}
                    response = requests.get('http://127.0.0.1:5000/api/v2/tables/list', headers=headers, timeout=5)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if data.get('success'):
                                tables_data = data.get('data', [])
                                self._update_ui_from_api_data(tables_data)
                                print("Tables refreshed from API")
                            else:
                                print(f"API error: {data.get('message')}")
                                self._refresh_from_db()  # Fallback
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            print(f"Response text: {response.text[:200]}")
                            self._refresh_from_db()  # Fallback
                    else:
                        print(f"API request failed: {response.status_code}")
                        if response.status_code == 401:
                            print("Token expired, attempting refresh")
                            # Try to refresh token
                            if self.api_client.refresh_access_token():
                                print("Token refreshed, retrying API call")
                                self._refresh_from_api()  # Retry with new token
                                return
                        self._refresh_from_db()  # Fallback
                else:
                    print("Token invalid, falling back to database")
                    self._refresh_from_db()
            else:
                print("No API token available, falling back to database")
                self._refresh_from_db()
        except Exception as e:
            print(f"API refresh error: {e}")
            self._refresh_from_db()  # Fallback

    def _refresh_from_db(self):
        """Refresh tables data from database with smart update strategy"""
        tables = self.svc.get_all(self.db)
        stats = self.svc.get_stats(self.db)

        print(f"Tables from DB: {len(tables)}")
        print(f"Stats: {stats}")

        # Statistika
        self.stat_labels["total"].setText(f"🪑  Cəmi: {stats['total']}")
        self.stat_labels["available"].setText(f"✅  Boş: {stats['available']}")
        self.stat_labels["occupied"].setText(f"🔴  Dolu: {stats['occupied']}")
        self.stat_labels["reserved"].setText(f"📅  Rezerv: {stats['reserved']}")

        # Smart update strategy - only update changed tables
        self._smart_update_tables(tables)

    def _smart_update_tables(self, tables):
        """Smart update - only refresh tables that actually changed"""
        import time
        start_time = time.time()

        # Create a dictionary of current tables for fast lookup and validation
        current_tables = {table.id: table for table in tables}
        valid_table_ids = set(current_tables.keys())

        # Remove orphan table widgets BEFORE updating
        db_ids = {t.id for t in tables}
        for table_id in list(self.table_cards.keys()):
            if table_id not in db_ids:
                widget = self.table_cards.pop(table_id)
                self.grid.removeWidget(widget)
                widget.deleteLater()
                print(f"Removed orphan table {table_id} from UI")

        # Update existing cards and find new tables
        added_table_ids = valid_table_ids - set(self.table_cards.keys())

        updated_count = 0
        skipped_count = 0

        # Add cards for new tables only
        for table_id in added_table_ids:
            table = current_tables[table_id]
            card = TableCard(table, self)
            card.clicked.connect(self._on_table_click)
            self.table_cards[table_id] = card

            # Find empty position in grid
            position = self._find_empty_grid_position()
            if position:
                row, col = position
                self.grid.addWidget(card, row, col)
                print(f"Added new table {table_id} at position ({row}, {col})")

        # Update existing tables only if their data changed and they exist in DB
        for table_id, table in current_tables.items():
            if table_id in self.table_cards:
                card = self.table_cards[table_id]
                if self._table_data_changed(table, card):
                    print(f"Updating table {table.number} - data changed")
                    card.refresh(table)
                    updated_count += 1
                else:
                    # No change - skip update for performance
                    skipped_count += 1

        end_time = time.time()
        duration = (end_time - start_time) * 1000  # Convert to milliseconds

        print(f"Smart update completed in {duration:.2f}ms - Updated: {updated_count}, Skipped: {skipped_count}")

        # Performance warning for large datasets
        if len(tables) > 50 and duration > 100:
            print(f"⚠️  Performance warning: {len(tables)} tables took {duration:.2f}ms")

    def _table_data_changed(self, table, card):
        """Check if table data actually changed"""
        try:
            # Check if status changed
            if hasattr(table.status, 'value'):
                current_status = table.status.value
            else:
                current_status = str(table.status)

            # Get previous status from card (we'd need to store this)
            # For now, always refresh occupied tables as they might have order changes
            if current_status == "occupied":
                return True  # Always refresh occupied tables for order summary

            # For other tables, check if basic data changed
            if hasattr(card, 'last_status') and card.last_status != current_status:
                return True

            return False
        except Exception as e:
            print(f"Error checking table data change: {e}")
            return True  # Default to refresh on error

    def _find_empty_grid_position(self):
        """Find an empty position in the grid"""
        max_rows = 20  # Reasonable maximum

        for row in range(max_rows):
            for col in range(self.cols):
                item_at_position = self.grid.itemAtPosition(row, col)
                if item_at_position is None:
                    return (row, col)

        return None  # Grid is full

    def _update_ui_from_api_data(self, tables_data):
        """Update UI with API data"""
        # Convert API data to table objects
        from database.models import Table
        tables = []
        for table_data in tables_data:
            table = Table()
            table.id = table_data.get('id')
            table.number = table_data.get('number')
            table.status = table_data.get('status')
            table.capacity = table_data.get('capacity')
            tables.append(table)

        # Update stats
        stats = {
            'total': len(tables),
            'available': len([t for t in tables if t.status == 'available']),
            'occupied': len([t for t in tables if t.status == 'occupied']),
            'reserved': len([t for t in tables if t.status == 'reserved'])
        }

        # Update UI
        self.stat_labels["total"].setText(f"🪑  Cəmi: {stats['total']}")
        self.stat_labels["available"].setText(f"✅  Boş: {stats['available']}")
        self.stat_labels["occupied"].setText(f"🔴  Dolu: {stats['occupied']}")
        self.stat_labels["reserved"].setText(f"📅  Rezerv: {stats['reserved']}")

        # Update cards
        for table in tables:
            if table.id in self.table_cards:
                self.table_cards[table.id].refresh(table)

    # Drag and Drop handlers
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("table_"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("table_"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop event - move table to new position"""
        mime_data = event.mimeData()
        if mime_data.hasText() and mime_data.text().startswith("table_"):
            # Parse table data
            parts = mime_data.text().split("_")
            if len(parts) >= 3:
                old_table_id = int(parts[1])
                old_table_number = int(parts[2])

                # Find which table card was dropped on
                widget = self.childAt(event.position().toPoint())
                if widget and isinstance(widget, TableCard):
                    new_table_id = widget.table.id
                    new_table_number = widget.table.number

                    # Only allow moving to available tables
                    if hasattr(widget.table.status, 'value') and widget.table.status.value == "available":
                        self._show_move_confirmation(old_table_id, old_table_number, new_table_id, new_table_number)
                    else:
                        QMessageBox.warning(self, "Masa Taşıma", "Sadece boş masalara taşıyabilirsiniz!")

        event.acceptProposedAction()

    def _show_move_confirmation(self, old_table_id, old_table_number, new_table_id, new_table_number):
        """Show confirmation dialog for table move with validation"""
        # Validate table IDs before proceeding
        if old_table_id not in self.table_cards or new_table_id not in self.table_cards:
            QMessageBox.warning(self, "Hata", "Masa ID'ləri etibarsızdir!")
            return
        
        reply = QMessageBox.question(
            self,
            "Masa Taşıma Onayı",
            f"Masa {old_table_number} -> Masa {new_table_number}\n\n"
            f"Bu masadaki aktif siparişi taşımak istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Move order using service
                success = self.svc.move_order(old_table_id, new_table_id)
                if success:
                    QMessageBox.information(self, "Başarılı",
                                            f"Masa {old_table_number} -> Masa {new_table_number} taşındı!")
                    self._refresh()  # Refresh tables
                else:
                    QMessageBox.warning(self, "Hata", "Masa taşınamadı!")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Masa taşıma sırasında hata: {str(e)}")

    def _filter_floor(self, floor: int):
        for f, btn in self.floor_btns.items():
            btn.setChecked(f == floor)
        for table_id, card in self.table_cards.items():
            if floor == 0:
                card.show()
            else:
                # Check table floor attribute if exists
                table_floor = getattr(card.table, 'floor', 1)
                if table_floor == floor:
                    card.show()
                else:
                    card.hide()

    # ── Masa tıklama ──────────────────────────────────────────────────────────

    def _on_table_click(self, table):
        active_order = self.svc.get_active_order(self.db, table.id)
        dlg = TableActionDialog(table, active_order, self.auth, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        action = dlg.chosen_action

        if action == "new_order":
            self.open_order.emit(table)
        elif action == "view_order" and active_order:
            self.view_order.emit(active_order)
        elif action == "payment" and active_order:
            self.open_payment.emit(active_order)
        elif action == "occupy":
            self.svc.set_status(self.db, table.id, "occupied")
            self._refresh()
        elif action == "reserve":
            self.svc.set_status(self.db, table.id, "reserved")
            self._refresh()
        elif action == "cancel_reserve":
            self.svc.set_status(self.db, table.id, "available")
            self._refresh()
        elif action == "set_available":
            self.svc.set_status(self.db, table.id, "available")
            self._refresh()
        elif action == "set_cleaning":
            self.svc.set_status(self.db, table.id, "cleaning")
            self._refresh()
        elif action == "edit":
            self._edit_table(table)
        elif action == "move":
            QMessageBox.information(self, "Masa köçürülməsi",
                                    "Bu funksiya sifariş modulunda mövcuddur.")

    def _add_table(self):
        dlg = AddTableDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok, result = self.svc.create(self.db, **data)
            if ok:
                self._refresh()
            else:
                QMessageBox.warning(self, "Xəta", str(result))

    def _edit_table(self, table):
        dlg = AddTableDialog(table, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok, result = self.svc.update(self.db, table.id, **data)
            if ok:
                self._refresh()
            else:
                QMessageBox.warning(self, "Xəta", str(result))
