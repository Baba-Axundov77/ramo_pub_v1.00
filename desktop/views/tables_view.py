# desktop/views/tables_view.py — Masa İdarəetməsi UI
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QDialog, QLineEdit, QSpinBox, QComboBox,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from config import TABLE_STATUS


class TableCard(QFrame):
    """Tıklanabilən masa kartı."""
    clicked = pyqtSignal(object)  # Table obj

    STATUS_COLORS = {
        "available": ("#1a3a1a", "#2ECC71", "Boş"),
        "occupied":  ("#3a1a1a", "#E74C3C", "Dolu"),
        "reserved":  ("#2a2a1a", "#F39C12", "Rezerv"),
        "cleaning":  ("#1a2a3a", "#3498DB", "Təmizlənir"),
    }

    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.setFixedSize(140, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()
        self.refresh(table)

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.num_lbl = QLabel()
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_lbl.setFont(QFont("Georgia", 26, QFont.Weight.Bold))
        v.addWidget(self.num_lbl)

        self.name_lbl = QLabel()
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setFont(QFont("Segoe UI", 9))
        v.addWidget(self.name_lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.1);")
        v.addWidget(sep)

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
        status = table.status.value
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

        # Şəkil varsa, adı göstər; yoxdursa emoji
        if getattr(table, "image_path", None):
            from desktop.views.widgets.image_picker import RoundedImageLabel
            # Şəkli num_lbl yerinə qoy (sadəcə rəng dəyişdir)
            self.num_lbl.setStyleSheet(f"color: {accent}; font-size: 20px;")

        self.name_lbl.setText(table.name or "")
        self.name_lbl.setStyleSheet("color: rgba(255,255,255,0.7);")
        self.status_lbl.setText(label)
        self.status_lbl.setStyleSheet(f"color: {accent};")
        self.cap_lbl.setText(f"👥 {table.capacity} nəfər")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.table)


class TableActionDialog(QDialog):
    """Masa üzərində əməliyyat dialoqu."""

    def __init__(self, table, active_order, auth, parent=None):
        super().__init__(parent)
        self.table        = table
        self.active_order = active_order
        self.auth         = auth
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
        status_lbl.setStyleSheet(f"color: {colors.get(status_val,'#fff')}; font-size:11px;")
        v.addWidget(status_lbl)

        if self.active_order:
            order_lbl = QLabel(f"📋 Aktiv sifariş: #{self.active_order.id}  |  {self.active_order.total:.2f} ₼")
            order_lbl.setStyleSheet("color: #F39C12; font-size: 11px; padding: 6px; "
                                    "background: rgba(243,156,18,0.1); border-radius:6px;")
            v.addWidget(order_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2E2E4E;"); v.addWidget(sep)

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
            sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet("background:#2E2E4E;"); v.addWidget(sep2)
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

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2E2E4E; margin: 4px 0;")
        v.addWidget(sep)

        # Form sahələri
        row1 = QHBoxLayout(); row1.setSpacing(10)
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
            "number":     self.num_spin.value(),
            "name":       self.name_input.text().strip() or None,
            "capacity":   self.cap_spin.value(),
            "floor":      self.floor_spin.value(),
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
    open_order   = pyqtSignal(object)
    view_order   = pyqtSignal(object)
    open_payment = pyqtSignal(object)

    def __init__(self, db, table_service, auth_service, parent=None):
        super().__init__(parent)
        self.db      = db
        self.svc     = table_service
        self.auth    = auth_service
        self.cards   = {}

        self._build_ui()
        self._refresh()

        # Hər 30 san. avtomatik yenilə
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(30000)

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
            ("total",     "#8080A0", "🪑"),
            ("available", "#2ECC71", "✅"),
            ("occupied",  "#E74C3C", "🔴"),
            ("reserved",  "#F39C12", "📅"),
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
        for color, label in [("#2ECC71","Boş"), ("#E74C3C","Dolu"),
                              ("#F39C12","Rezerv"), ("#3498DB","Təmizlənir")]:
            dot = QLabel(f"●  {label}")
            dot.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addSpacing(12)
        root.addLayout(legend)

    # ── Məlumat yükləmə ───────────────────────────────────────────────────────

    def _refresh(self):
        tables = self.svc.get_all(self.db)
        stats  = self.svc.get_stats(self.db)

        # Statistika
        self.stat_labels["total"].setText(f"🪑  Cəmi: {stats['total']}")
        self.stat_labels["available"].setText(f"✅  Boş: {stats['available']}")
        self.stat_labels["occupied"].setText(f"🔴  Dolu: {stats['occupied']}")
        self.stat_labels["reserved"].setText(f"📅  Rezerv: {stats['reserved']}")

        # Mövcud kartları yenilə
        for table in tables:
            if table.id in self.cards:
                self.cards[table.id].refresh(table)

        # Yeni masa varsa kartları yenidən çək
        if len(tables) != len(self.cards):
            self._rebuild_grid(tables)

    def _rebuild_grid(self, tables):
        # Mövcud grid-i təmizlə
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        cols = 6
        for i, table in enumerate(tables):
            card = TableCard(table)
            card.clicked.connect(self._on_table_click)
            self.cards[table.id] = card
            self.grid.addWidget(card, i // cols, i % cols)

        # Boş hücrə doldur
        remaining = cols - (len(tables) % cols)
        if remaining < cols:
            for j in range(remaining):
                spacer = QWidget()
                spacer.setFixedSize(140, 130)
                self.grid.addWidget(spacer, len(tables) // cols,
                                    len(tables) % cols + j)

    def _filter_floor(self, floor: int):
        for f, btn in self.floor_btns.items():
            btn.setChecked(f == floor)
        for table_id, card in self.cards.items():
            if floor == 0:
                card.show()
            else:
                card.setVisible(card.table.floor == floor)

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
