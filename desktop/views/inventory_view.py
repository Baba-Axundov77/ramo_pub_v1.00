# desktop/views/inventory_view.py — Anbar & Stok İdarəsi UI
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QDialog, QLineEdit, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class InventoryDialog(QDialog):
    """Stok məhsulu əlavə et / redaktə et."""

    def __init__(self, item=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Stok əlavə et" if not item else "Stoku redaktə et")
        self.setModal(True)
        self.setFixedWidth(380)
        self._build()
        if item:
            self._fill(item)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10); v.setContentsMargins(20, 20, 20, 20)

        def lbl(t):
            l = QLabel(t); l.setObjectName("loginLabel"); return l

        v.addWidget(lbl("MƏHSUL ADI"))
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(38)
        v.addWidget(self.name_input)

        row1 = QHBoxLayout(); row1.setSpacing(8)
        u = QVBoxLayout()
        u.addWidget(lbl("ÖLÇÜ VАHİDİ"))
        self.unit_combo = QComboBox()
        self.unit_combo.setFixedHeight(38)
        self.unit_combo.addItems(["kq", "qr", "litr", "ml", "ədəd", "qutu", "paket"])
        self.unit_combo.setEditable(True)
        u.addWidget(self.unit_combo)
        row1.addLayout(u)

        s = QVBoxLayout()
        s.addWidget(lbl("MİQDAR"))
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0, 99999)
        self.qty_spin.setDecimals(2)
        self.qty_spin.setFixedHeight(38)
        s.addWidget(self.qty_spin)
        row1.addLayout(s)
        v.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(8)
        m = QVBoxLayout()
        m.addWidget(lbl("MİNİMUM XƏBƏRDARLIq"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 99999)
        self.min_spin.setDecimals(2)
        self.min_spin.setValue(5.0)
        self.min_spin.setFixedHeight(38)
        m.addWidget(self.min_spin)
        row2.addLayout(m)

        c = QVBoxLayout()
        c.addWidget(lbl("VAHID QİYMƏTİ (₼)"))
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 9999)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setFixedHeight(38)
        c.addWidget(self.cost_spin)
        row2.addLayout(c)
        v.addLayout(row2)

        v.addWidget(lbl("TƏDARÜKÇİ"))
        self.supplier_input = QLineEdit()
        self.supplier_input.setFixedHeight(38)
        self.supplier_input.setPlaceholderText("Şirkət adı...")
        v.addWidget(self.supplier_input)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        save = QPushButton("💾  Yadda saxla")
        save.setFixedHeight(42); save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42); cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(save); btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def _fill(self, item):
        self.name_input.setText(item.name)
        idx = self.unit_combo.findText(item.unit)
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        else:
            self.unit_combo.setEditText(item.unit)
        self.qty_spin.setValue(item.quantity)
        self.min_spin.setValue(item.min_quantity)
        self.cost_spin.setValue(item.cost_per_unit)
        self.supplier_input.setText(item.supplier or "")

    def get_data(self) -> dict:
        return {
            "name":          self.name_input.text().strip(),
            "unit":          self.unit_combo.currentText().strip(),
            "quantity":      self.qty_spin.value(),
            "min_quantity":  self.min_spin.value(),
            "cost_per_unit": self.cost_spin.value(),
            "supplier":      self.supplier_input.text().strip(),
        }


class StockAdjustDialog(QDialog):
    """Stok artır / azalt dialoqu."""

    def __init__(self, item, mode: str = "add", parent=None):
        super().__init__(parent)
        self.item = item
        self.mode = mode
        title = f"Stok artır — {item.name}" if mode == "add" else f"Stok azalt — {item.name}"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(300)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(12); v.setContentsMargins(20, 20, 20, 20)

        icon = "📦➕" if self.mode == "add" else "📦➖"
        title = QLabel(f"{icon}  {self.item.name}")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #E8A045;")
        v.addWidget(title)

        cur = QLabel(f"Cari miqdar: {self.item.quantity:.2f} {self.item.unit}")
        cur.setStyleSheet("color: #8080A0; font-size: 11px;")
        v.addWidget(cur)

        lbl = QLabel("MİQDAR")
        lbl.setObjectName("loginLabel")
        v.addWidget(lbl)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(1.0)
        self.amount_spin.setFixedHeight(42)
        self.amount_spin.setSuffix(f"  {self.item.unit}")
        v.addWidget(self.amount_spin)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        color = "#2ECC71" if self.mode == "add" else "#E74C3C"
        label = "➕ Artır" if self.mode == "add" else "➖ Azalt"
        confirm = QPushButton(label)
        confirm.setFixedHeight(40)
        confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm.setStyleSheet(f"QPushButton{{background:{color};color:#0D0D0D;"
                               f"border:none;border-radius:8px;font-weight:bold;}}"
                               f"QPushButton:hover{{opacity:0.8;}}")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv")
        cancel.setFixedHeight(40); cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(confirm); btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def get_amount(self) -> float:
        return self.amount_spin.value()


class InventoryView(QWidget):
    """Anbar & Stok İdarəsi — əsas görünüş."""

    def __init__(self, db, inventory_service, auth_service, parent=None):
        super().__init__(parent)
        self.db   = db
        self.svc  = inventory_service
        self.auth = auth_service
        self._build_ui()
        self._load()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout(); toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Məhsul axtar...")
        self.search_input.setFixedHeight(38)
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self._load)
        toolbar.addWidget(self.search_input)

        # Stat badge-lər
        self.total_lbl = self._badge("📦  Cəmi: 0", "#8080A0")
        self.low_lbl   = self._badge("⚠️  Az qalan: 0", "#E74C3C")
        self.value_lbl = self._badge("💰  Dəyər: 0.00 ₼", "#2ECC71")
        toolbar.addWidget(self.total_lbl)
        toolbar.addWidget(self.low_lbl)
        toolbar.addWidget(self.value_lbl)
        toolbar.addStretch()

        self.low_only_btn = QPushButton("⚠️  Yalnız az qalanlar")
        self.low_only_btn.setCheckable(True)
        self.low_only_btn.setFixedHeight(36)
        self.low_only_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.low_only_btn.setStyleSheet("""
            QPushButton{background:transparent;color:#E74C3C;
                border:1px solid #E74C3C60;border-radius:8px;padding:0 12px;}
            QPushButton:checked{background:#E74C3C;color:#fff;border-color:#E74C3C;}
            QPushButton:hover:!checked{background:#E74C3C20;}
        """)
        self.low_only_btn.toggled.connect(self._load)
        toolbar.addWidget(self.low_only_btn)

        if self.auth.is_admin():
            add_btn = QPushButton("➕  Stok əlavə et")
            add_btn.setFixedHeight(36)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_item)
            toolbar.addWidget(add_btn)
        root.addLayout(toolbar)

        # ── Cədvəl ────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Məhsul", "Vahid", "Miqdar", "Min.", "Status",
            "Vahid Qiyməti", "Cəmi Dəyər", "Əməliyyatlar"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 200)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D0D0D; border: 1px solid #2E2E4E; border-radius: 10px;
                gridline-color: #1E1E2E; font-size: 12px; color: #F0EAD6;
            }
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:selected { background: #E8A04530; color: #F0EAD6; }
            QTableWidget::item:alternate { background: #141420; }
            QHeaderView::section {
                background: #1C1C2E; color: #8080A0; border: none;
                padding: 8px 10px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;
            }
        """)
        root.addWidget(self.table)

    def _badge(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            QLabel {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {color}50;
                color: {color};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        return lbl

    # ── Məlumat ───────────────────────────────────────────────────────────────

    def _load(self):
        query    = self.search_input.text().strip().lower()
        low_only = self.low_only_btn.isChecked()
        items    = self.svc.get_all(self.db, low_stock_only=low_only)

        if query:
            items = [i for i in items if query in i.name.lower()]

        # Stat güncəllə
        all_items = self.svc.get_all(self.db)
        low_count = self.svc.get_low_stock_count(self.db)
        total_val = self.svc.get_total_value(self.db)
        self.total_lbl.setText(f"📦  Cəmi: {len(all_items)}")
        self.low_lbl.setText(f"⚠️  Az qalan: {low_count}")
        self.value_lbl.setText(f"💰  Dəyər: {total_val:.2f} ₼")

        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.table.setRowHeight(row, 44)
            is_low = item.quantity <= item.min_quantity

            # Sütunlar
            for col, val in enumerate([
                item.name,
                item.unit,
                f"{item.quantity:.2f}",
                f"{item.min_quantity:.2f}",
            ]):
                cell = QTableWidgetItem(val)
                cell.setData(Qt.ItemDataRole.UserRole, item)
                if col == 2 and is_low:
                    cell.setForeground(QColor("#E74C3C"))
                    cell.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.table.setItem(row, col, cell)

            # Status
            status_txt = "⚠️  Az qalıb" if is_low else "✅  Normal"
            status_cell = QTableWidgetItem(status_txt)
            status_cell.setForeground(QColor("#E74C3C" if is_low else "#2ECC71"))
            status_cell.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 4, status_cell)

            for col, val in enumerate([
                f"{item.cost_per_unit:.2f} ₼",
                f"{item.quantity * item.cost_per_unit:.2f} ₼",
            ], start=5):
                c = QTableWidgetItem(val)
                c.setData(Qt.ItemDataRole.UserRole, item)
                self.table.setItem(row, col, c)

            # Əməliyyatlar
            btn_widget = QWidget()
            btn_h = QHBoxLayout(btn_widget)
            btn_h.setContentsMargins(4, 2, 4, 2)
            btn_h.setSpacing(4)

            add_btn = QPushButton("➕")
            add_btn.setFixedSize(32, 30)
            add_btn.setToolTip("Stok artır")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.setStyleSheet("QPushButton{background:#1C3A1C;color:#2ECC71;"
                                   "border:1px solid #2ECC7160;border-radius:6px;}"
                                   "QPushButton:hover{background:#2ECC71;color:#000;}")
            add_btn.clicked.connect(lambda _, i=item: self._adjust(i, "add"))
            btn_h.addWidget(add_btn)

            rm_btn = QPushButton("➖")
            rm_btn.setFixedSize(32, 30)
            rm_btn.setToolTip("Stok azalt")
            rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rm_btn.setStyleSheet("QPushButton{background:#3A1C1C;color:#E74C3C;"
                                  "border:1px solid #E74C3C60;border-radius:6px;}"
                                  "QPushButton:hover{background:#E74C3C;color:#fff;}")
            rm_btn.clicked.connect(lambda _, i=item: self._adjust(i, "remove"))
            btn_h.addWidget(rm_btn)

            if self.auth.is_admin():
                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(32, 30)
                edit_btn.setToolTip("Redaktə et")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setObjectName("secondaryBtn")
                edit_btn.clicked.connect(lambda _, i=item: self._edit_item(i))
                btn_h.addWidget(edit_btn)

                del_btn = QPushButton("🗑")
                del_btn.setFixedSize(32, 30)
                del_btn.setToolTip("Sil")
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setObjectName("dangerBtn")
                del_btn.clicked.connect(lambda _, i=item: self._delete_item(i))
                btn_h.addWidget(del_btn)

            btn_h.addStretch()
            self.table.setCellWidget(row, 7, btn_widget)

    # ── Əməliyyatlar ──────────────────────────────────────────────────────────

    def _add_item(self):
        dlg = InventoryDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Xəta", "Ad boş ola bilməz.")
                return
            self.svc.create(self.db, **data)
            self._load()

    def _edit_item(self, item):
        dlg = InventoryDialog(item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.svc.update(self.db, item.id, **data)
            self._load()

    def _adjust(self, item, mode: str):
        dlg = StockAdjustDialog(item, mode, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            amount = dlg.get_amount()
            if mode == "add":
                ok, result = self.svc.add_stock(self.db, item.id, amount)
            else:
                ok, result = self.svc.remove_stock(self.db, item.id, amount)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            self._load()

    def _delete_item(self, item):
        reply = QMessageBox.question(
            self, "Silmə təsdiqi",
            f"'{item.name}' stokdan silinsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = self.svc.delete(self.db, item.id)
            if not ok:
                QMessageBox.warning(self, "Xəta", msg)
            self._load()
