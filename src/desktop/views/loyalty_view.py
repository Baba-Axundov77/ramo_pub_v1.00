# desktop/views/loyalty_view.py
# Python 3.10 uyğun
"""Loyallıq Sistemi & Müştəri İdarəsi UI."""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QLineEdit, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QComboBox, QDateEdit, QCheckBox,
    QScrollArea, QAbstractItemView, QTextEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from src.core.modules.loyalty.loyalty_service import get_tier, TIERS, MIN_REDEEM


# ── Müştəri Dialoqu ───────────────────────────────────────────────────────────

class CustomerDialog(QDialog):
    def __init__(self, customer=None, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Müştəri əlavə et" if not customer else "Müştərini redaktə et")
        self.setModal(True)
        self.setFixedWidth(380)
        self._build()
        if customer:
            self._fill(customer)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        def lbl(t: str) -> QLabel:
            ll = QLabel(t)
            ll.setObjectName("loginLabel")
            return ll

        v.addWidget(lbl("TAM AD *"))
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(38)
        self.name_input.setPlaceholderText("Ad Soyad")
        v.addWidget(self.name_input)

        v.addWidget(lbl("TELEFON *"))
        self.phone_input = QLineEdit()
        self.phone_input.setFixedHeight(38)
        self.phone_input.setPlaceholderText("+994 XX XXX XX XX")
        v.addWidget(self.phone_input)

        v.addWidget(lbl("EMAIL (İstəyə bağlı)"))
        self.email_input = QLineEdit()
        self.email_input.setFixedHeight(38)
        self.email_input.setPlaceholderText("ornek@mail.com")
        v.addWidget(self.email_input)

        v.addWidget(lbl("AD GÜNÜ (İstəyə bağlı)"))
        self.bday_edit = QDateEdit()
        self.bday_edit.setCalendarPopup(True)
        self.bday_edit.setDate(QDate.currentDate())
        self.bday_edit.setFixedHeight(38)
        self.bday_chk = QCheckBox("Ad günü məlumatı əlavə et")
        self.bday_chk.toggled.connect(self.bday_edit.setEnabled)
        self.bday_edit.setEnabled(False)
        v.addWidget(self.bday_chk)
        v.addWidget(self.bday_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save = QPushButton("💾  Yadda saxla")
        save.setFixedHeight(42)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42)
        cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(save)
        btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def _fill(self, c) -> None:
        self.name_input.setText(c.full_name)
        self.phone_input.setText(c.phone or "")
        self.email_input.setText(c.email or "")
        if c.birthday:
            self.bday_chk.setChecked(True)
            self.bday_edit.setDate(QDate(c.birthday.year,
                                         c.birthday.month, c.birthday.day))

    def get_data(self) -> dict:
        bd = None
        if self.bday_chk.isChecked():
            qd = self.bday_edit.date()
            bd = date(qd.year(), qd.month(), qd.day())
        return {
            "full_name": self.name_input.text().strip(),
            "phone":     self.phone_input.text().strip(),
            "email":     self.email_input.text().strip(),
            "birthday":  bd,
        }


# ── Endirim Kodu Dialoqu ──────────────────────────────────────────────────────

class DiscountDialog(QDialog):
    def __init__(self, discount=None, parent=None):
        super().__init__(parent)
        self.discount = discount
        self.setWindowTitle("Endirim kodu yarat" if not discount else "Endirimi redaktə et")
        self.setModal(True)
        self.setFixedWidth(400)
        self._build()
        if discount:
            self._fill(discount)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        def lbl(t: str) -> QLabel:
            ll = QLabel(t)
            ll.setObjectName("loginLabel")
            return ll

        v.addWidget(lbl("KUPON KODU *"))
        self.code_input = QLineEdit()
        self.code_input.setFixedHeight(38)
        self.code_input.setPlaceholderText("SUMMER20, VIP50...")
        self.code_input.textChanged.connect(
            lambda t: self.code_input.setText(t.upper())
        )
        v.addWidget(self.code_input)

        v.addWidget(lbl("TƏSVİR"))
        self.desc_input = QLineEdit()
        self.desc_input.setFixedHeight(38)
        v.addWidget(self.desc_input)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        tl = QVBoxLayout()
        tl.addWidget(lbl("NÖV"))
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(38)
        self.type_combo.addItem("% Faizli endirim", "percent")
        self.type_combo.addItem("₼ Sabit məbləğ",   "fixed")
        tl.addWidget(self.type_combo)
        row1.addLayout(tl)

        vl = QVBoxLayout()
        vl.addWidget(lbl("DƏYƏR"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0.01, 9999)
        self.value_spin.setDecimals(2)
        self.value_spin.setFixedHeight(38)
        vl.addWidget(self.value_spin)
        row1.addLayout(vl)
        v.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        ml = QVBoxLayout()
        ml.addWidget(lbl("MİN. SİFARİŞ (₼)"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 9999)
        self.min_spin.setDecimals(2)
        self.min_spin.setFixedHeight(38)
        ml.addWidget(self.min_spin)
        row2.addLayout(ml)

        ul = QVBoxLayout()
        ul.addWidget(lbl("LIMIT (0=sonsuz)"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 99999)
        self.limit_spin.setFixedHeight(38)
        ul.addWidget(self.limit_spin)
        row2.addLayout(ul)
        v.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        fl = QVBoxLayout()
        fl.addWidget(lbl("BAŞLANĞIC TARİXİ"))
        self.from_edit = QDateEdit()
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDate(QDate.currentDate())
        self.from_edit.setFixedHeight(38)
        fl.addWidget(self.from_edit)
        row3.addLayout(fl)

        el = QVBoxLayout()
        el.addWidget(lbl("BİTİŞ TARİXİ"))
        self.until_edit = QDateEdit()
        self.until_edit.setCalendarPopup(True)
        self.until_edit.setDate(QDate.currentDate().addDays(30))
        self.until_edit.setFixedHeight(38)
        el.addWidget(self.until_edit)
        row3.addLayout(el)
        v.addLayout(row3)

        self.no_expiry_chk = QCheckBox("Son tarix yoxdur")
        self.no_expiry_chk.toggled.connect(self.until_edit.setDisabled)
        v.addWidget(self.no_expiry_chk)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save = QPushButton("💾  Yarat")
        save.setFixedHeight(42)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42)
        cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(save)
        btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def _fill(self, d) -> None:
        self.code_input.setText(d.code)
        self.code_input.setReadOnly(True)
        self.desc_input.setText(d.description or "")
        idx = 0 if d.type == "percent" else 1
        self.type_combo.setCurrentIndex(idx)
        self.value_spin.setValue(d.value)
        self.min_spin.setValue(d.min_order)
        self.limit_spin.setValue(d.usage_limit)
        if d.valid_from:
            self.from_edit.setDate(QDate(
                d.valid_from.year, d.valid_from.month, d.valid_from.day
            ))
        if d.valid_until:
            self.until_edit.setDate(QDate(
                d.valid_until.year, d.valid_until.month, d.valid_until.day
            ))
        else:
            self.no_expiry_chk.setChecked(True)

    def get_data(self) -> dict:
        qf = self.from_edit.date()
        qu = self.until_edit.date()
        return {
            "code":         self.code_input.text().strip().upper(),
            "description":  self.desc_input.text().strip(),
            "disc_type":    self.type_combo.currentData(),
            "value":        self.value_spin.value(),
            "min_order":    self.min_spin.value(),
            "usage_limit":  self.limit_spin.value(),
            "valid_from":   date(qf.year(), qf.month(), qf.day()),
            "valid_until":  None if self.no_expiry_chk.isChecked()
                            else date(qu.year(), qu.month(), qu.day()),
        }


# ── Xal Tənzimləmə Dialoqu ────────────────────────────────────────────────────

class PointsAdjustDialog(QDialog):
    def __init__(self, customer, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"Xal tənzimlə — {customer.full_name}")
        self.setModal(True)
        self.setFixedWidth(300)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(20, 20, 20, 20)

        cur = QLabel(f"Cari xal: {self.customer.points} ⭐")
        cur.setStyleSheet("color:#E8A045; font-size:14px; font-weight:bold;")
        v.addWidget(cur)

        lbl = QLabel("DƏYƏR (mənfi = azalt)")
        lbl.setObjectName("loginLabel")
        v.addWidget(lbl)

        self.delta_spin = QSpinBox()
        self.delta_spin.setRange(-99999, 99999)
        self.delta_spin.setValue(0)
        self.delta_spin.setFixedHeight(42)
        self.delta_spin.setSuffix("  xal")
        v.addWidget(self.delta_spin)

        lbl2 = QLabel("SƏBƏB")
        lbl2.setObjectName("loginLabel")
        v.addWidget(lbl2)
        self.reason_input = QLineEdit()
        self.reason_input.setFixedHeight(38)
        self.reason_input.setPlaceholderText("İxtiyari qeyd...")
        v.addWidget(self.reason_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        ok_btn = QPushButton("✅  Tətbiq et")
        ok_btn.setFixedHeight(40)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv")
        cancel.setFixedHeight(40)
        cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel)
        v.addLayout(btn_row)


# ── Müştəri Kartı (xülasə paneli) ────────────────────────────────────────────

class CustomerCard(QFrame):
    """Sağ paneldə seçilmiş müştərinin detalları."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet("""
            CustomerCard {
                background: #141420;
                border-left: 1px solid #2E2E4E;
            }
        """)
        self._build()
        self.clear()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(10)

        self.tier_lbl = QLabel()
        self.tier_lbl.setFont(QFont("Georgia", 32))
        self.tier_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.tier_lbl)

        self.name_lbl = QLabel()
        self.name_lbl.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setStyleSheet("color: #E8A045;")
        self.name_lbl.setWordWrap(True)
        v.addWidget(self.name_lbl)

        self.tier_name_lbl = QLabel()
        self.tier_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tier_name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        v.addWidget(self.tier_name_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #2E2E4E;")
        v.addWidget(sep)

        for attr, label, color in [
            ("points_lbl",   "⭐ Xallar",       "#E8A045"),
            ("spent_lbl",    "💰 Xərclənmiş",   "#2ECC71"),
            ("orders_lbl",   "📋 Sifarişlər",   "#3498DB"),
            ("redeem_lbl",   "🎁 Endirim dəyəri","#9B59B6"),
            ("phone_lbl",    "📱 Telefon",       "#8080A0"),
        ]:
            row = QHBoxLayout()
            key_l = QLabel(label)
            key_l.setStyleSheet("color: #6A6A8A; font-size: 11px;")
            val_l = QLabel("—")
            val_l.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            val_l.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(key_l)
            row.addWidget(val_l)
            v.addLayout(row)
            setattr(self, attr, val_l)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: #2E2E4E;")
        v.addWidget(sep2)

        # Növbəti səviyyə progress
        self.next_lbl = QLabel()
        self.next_lbl.setStyleSheet("color: #6A6A8A; font-size: 10px;")
        self.next_lbl.setWordWrap(True)
        v.addWidget(self.next_lbl)

        v.addStretch()

        self.empty_lbl = QLabel("Siyahıdan müştəri seçin")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #4A4A6A; font-size: 12px;")
        v.addWidget(self.empty_lbl)

    def clear(self):
        self.tier_lbl.setText("👤")
        self.name_lbl.setText("")
        self.tier_name_lbl.setText("")
        for attr in ("points_lbl","spent_lbl","orders_lbl","redeem_lbl","phone_lbl"):
            getattr(self, attr).setText("—")
        self.next_lbl.setText("")
        self.empty_lbl.setVisible(True)

    def update_customer(self, stats: dict):
        self.empty_lbl.setVisible(False)
        c    = stats["customer"]
        tier = stats["tier"]

        self.tier_lbl.setText(tier["icon"])
        self.name_lbl.setText(c.full_name)
        color_map = {"bronze":"#CD7F32","silver":"#C0C0C0","gold":"#FFD700","vip":"#9B59B6"}
        tier_key = next(
            (k for k, v in TIERS.items() if v["label"] == tier["label"]),
            "bronze"
        )
        color = color_map.get(tier_key, "#E8A045")
        self.tier_name_lbl.setText(tier["label"])
        self.tier_name_lbl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")

        self.points_lbl.setText(f"{stats['points']:,} xal")
        self.spent_lbl.setText(f"{stats['total_spent']:.2f} ₼")
        self.orders_lbl.setText(str(stats["total_orders"]))
        self.redeem_lbl.setText(f"{stats['redeem_value']:.2f} ₼")
        self.phone_lbl.setText(c.phone or "—")

        nxt = stats["next_tier_pts"]
        if nxt > 0:
            self.next_lbl.setText(f"Növbəti səviyyə üçün {nxt} xal lazımdır")
        else:
            self.next_lbl.setText("🏆 Ən yüksək səviyyəsiniz!")


# ── Əsas Görünüş ─────────────────────────────────────────────────────────────

class LoyaltyView(QWidget):
    """Loyallıq & Müştəri İdarəsi — əsas pəncərə."""

    def __init__(self, db, loyalty_service, auth_service, parent=None):
        super().__init__(parent)
        self.db   = db
        self.svc  = loyalty_service
        self.auth = auth_service
        self._build_ui()
        self._load_customers()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sol / Orta — Tab-lar ──────────────────────────────────────────────
        tabs_widget = QWidget()
        tabs_v = QVBoxLayout(tabs_widget)
        tabs_v.setContentsMargins(0, 0, 0, 0)
        tabs_v.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0D0D0D; }
            QTabBar::tab {
                background: #141420; color: #8080A0;
                padding: 10px 20px; border: none; font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #1C1C2E; color: #E8A045;
                border-bottom: 2px solid #E8A045; font-weight: bold;
            }
        """)
        tabs.addTab(self._build_customers_tab(), "👥  Müştərilər")
        tabs.addTab(self._build_discounts_tab(), "🏷️  Endirim Kodları")
        tabs.currentChanged.connect(lambda i: self._load_discounts() if i == 1 else None)
        tabs_v.addWidget(tabs)
        self.tabs = tabs

        root.addWidget(tabs_widget)

        # ── Sağ — Müştəri Detalı ─────────────────────────────────────────────
        self.customer_card = CustomerCard()
        root.addWidget(self.customer_card)

    # ── Müştərilər Tab ────────────────────────────────────────────────────────

    def _build_customers_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14)
        v.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Ad və ya telefon ilə axtar...")
        self.search_input.setFixedHeight(38)
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self._load_customers)
        toolbar.addWidget(self.search_input)

        for attr, text, color in [
            ("total_cust_lbl", "👥  Cəmi: 0",  "#8080A0"),
            ("vip_lbl",        "💎  VIP: 0",   "#9B59B6"),
            ("points_sum_lbl", "⭐  Xal: 0",   "#E8A045"),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255,255,255,0.04);
                    border: 1px solid {color}50; color: {color};
                    border-radius: 8px; padding: 6px 12px;
                    font-size: 11px; font-weight: bold;
                }}
            """)
            setattr(self, attr, lbl)
            toolbar.addWidget(lbl)

        toolbar.addStretch()

        add_btn = QPushButton("➕  Müştəri əlavə et")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_customer)
        toolbar.addWidget(add_btn)
        v.addLayout(toolbar)

        # Cədvəl
        self.cust_table = QTableWidget()
        self.cust_table.setColumnCount(7)
        self.cust_table.setHorizontalHeaderLabels([
            "Ad", "Telefon", "Xallar", "Səviyyə",
            "Xərclənmiş", "Üzv oldu", "Əməliyyat"
        ])
        self.cust_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.cust_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Fixed
        )
        self.cust_table.setColumnWidth(6, 160)
        self.cust_table.verticalHeader().setVisible(False)
        self.cust_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.cust_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.cust_table.setAlternatingRowColors(True)
        self.cust_table.itemClicked.connect(self._on_customer_click)
        self.cust_table.setStyleSheet(self._table_style())
        v.addWidget(self.cust_table)
        return w

    # ── Endirim Kodları Tab ────────────────────────────────────────────────────

    def _build_discounts_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14)
        v.setSpacing(12)

        toolbar = QHBoxLayout()

        self.disc_active_chk = QCheckBox("Yalnız aktiv kodlar")
        self.disc_active_chk.setStyleSheet("color: #8080A0;")
        self.disc_active_chk.toggled.connect(self._load_discounts)
        toolbar.addWidget(self.disc_active_chk)
        toolbar.addStretch()

        add_disc_btn = QPushButton("➕  Endirim kodu yarat")
        add_disc_btn.setFixedHeight(36)
        add_disc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_disc_btn.clicked.connect(self._add_discount)
        toolbar.addWidget(add_disc_btn)
        v.addLayout(toolbar)

        self.disc_table = QTableWidget()
        self.disc_table.setColumnCount(8)
        self.disc_table.setHorizontalHeaderLabels([
            "Kod", "Növ", "Dəyər", "Min. Sifariş",
            "İstifadə", "Son Tarix", "Status", "Əməliyyat"
        ])
        self.disc_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.disc_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.Fixed
        )
        self.disc_table.setColumnWidth(7, 140)
        self.disc_table.verticalHeader().setVisible(False)
        self.disc_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.disc_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.disc_table.setAlternatingRowColors(True)
        self.disc_table.setStyleSheet(self._table_style())
        v.addWidget(self.disc_table)
        return w

    # ── Cədvəl Yüklə ─────────────────────────────────────────────────────────

    def _load_customers(self):
        query     = self.search_input.text().strip()
        customers = self.svc.get_all_customers(self.db, search=query)
        summary   = self.svc.get_summary(self.db)

        self.total_cust_lbl.setText(f"👥  Cəmi: {summary['total']}")
        self.vip_lbl.setText(f"💎  VIP: {summary['vip_count']}")
        self.points_sum_lbl.setText(f"⭐  Xal: {summary['total_points']:,}")

        tier_colors = {
            "Bürünc": "#CD7F32",
            "Gümüş":  "#C0C0C0",
            "Qızıl":  "#FFD700",
            "VIP":    "#9B59B6",
        }

        self.cust_table.setRowCount(len(customers))
        for row, c in enumerate(customers):
            self.cust_table.setRowHeight(row, 44)
            tier  = get_tier(c.points)
            color = tier_colors.get(tier["label"], "#8080A0")
            since = c.created_at.strftime("%d.%m.%Y") if c.created_at else "—"

            vals = [
                c.full_name,
                c.phone or "—",
                f"{c.points:,} ⭐",
                f"{tier['icon']} {tier['label']}",
                f"{c.total_spent:.2f} ₼",
                since,
            ]
            for col, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setData(Qt.ItemDataRole.UserRole, c)
                if col == 2:
                    cell.setForeground(QColor("#E8A045"))
                    cell.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                elif col == 3:
                    cell.setForeground(QColor(color))
                    cell.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.cust_table.setItem(row, col, cell)

            btn_w = QWidget()
            btn_h = QHBoxLayout(btn_w)
            btn_h.setContentsMargins(4, 2, 4, 2)
            btn_h.setSpacing(4)

            pts_btn = QPushButton("⭐ Xal")
            pts_btn.setFixedSize(58, 30)
            pts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pts_btn.setStyleSheet(
                "QPushButton{background:#2A2A1C;color:#E8A045;"
                "border:1px solid #E8A04560;border-radius:6px;font-size:10px;}"
                "QPushButton:hover{background:#E8A04520;}"
            )
            pts_btn.clicked.connect(lambda _, cust=c: self._adjust_points(cust))
            btn_h.addWidget(pts_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setObjectName("secondaryBtn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, cust=c: self._edit_customer(cust))
            btn_h.addWidget(edit_btn)

            if self.auth.is_admin():
                del_btn = QPushButton("🗑")
                del_btn.setFixedSize(30, 30)
                del_btn.setObjectName("dangerBtn")
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(lambda _, cust=c: self._delete_customer(cust))
                btn_h.addWidget(del_btn)

            btn_h.addStretch()
            self.cust_table.setCellWidget(row, 6, btn_w)

    def _load_discounts(self):
        active_only  = self.disc_active_chk.isChecked()
        discounts    = self.svc.get_all_discounts(self.db, active_only=active_only)

        self.disc_table.setRowCount(len(discounts))
        for row, d in enumerate(discounts):
            self.disc_table.setRowHeight(row, 44)

            if d.type == "percent":
                value_str = f"%{d.value:.0f}"
            else:
                value_str = f"{d.value:.2f} ₼"

            if d.valid_until:
                until_str = d.valid_until.strftime("%d.%m.%Y")
                is_expired = d.valid_until < date.today()
            else:
                until_str  = "Sonsuz"
                is_expired = False

            limit_str = f"{d.used_count}/{d.usage_limit}" if d.usage_limit else str(d.used_count)

            vals = [
                d.code,
                "Faizli" if d.type == "percent" else "Sabit",
                value_str,
                f"{d.min_order:.2f} ₼" if d.min_order else "—",
                limit_str,
                until_str,
                "✅ Aktiv" if d.is_active and not is_expired else "❌ Deaktiv",
            ]
            for col, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setData(Qt.ItemDataRole.UserRole, d)
                if col == 0:
                    cell.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
                    cell.setForeground(QColor("#E8A045"))
                elif col == 6:
                    color = "#2ECC71" if (d.is_active and not is_expired) else "#E74C3C"
                    cell.setForeground(QColor(color))
                self.disc_table.setItem(row, col, cell)

            btn_w = QWidget()
            btn_h = QHBoxLayout(btn_w)
            btn_h.setContentsMargins(4, 2, 4, 2)
            btn_h.setSpacing(4)

            toggle_btn = QPushButton("✅" if not d.is_active else "❌")
            toggle_btn.setFixedSize(30, 30)
            toggle_btn.setObjectName("secondaryBtn")
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.setToolTip("Aktiv/Deaktiv et")
            toggle_btn.clicked.connect(lambda _, disc=d: self._toggle_discount(disc))
            btn_h.addWidget(toggle_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setObjectName("secondaryBtn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, disc=d: self._edit_discount(disc))
            btn_h.addWidget(edit_btn)

            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(30, 30)
            del_btn.setObjectName("dangerBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, disc=d: self._delete_discount(disc))
            btn_h.addWidget(del_btn)

            btn_h.addStretch()
            self.disc_table.setCellWidget(row, 7, btn_w)

    # ── Müştəri Əməliyyatları ─────────────────────────────────────────────────

    def _on_customer_click(self, item):
        customer = item.data(Qt.ItemDataRole.UserRole)
        if customer:
            stats = self.svc.get_customer_stats(self.db, customer.id)
            self.customer_card.update_customer(stats)

    def _add_customer(self):
        dlg = CustomerDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["full_name"] or not data["phone"]:
                QMessageBox.warning(self, "Xəta", "Ad və telefon mütləqdir.")
                return
            ok, result = self.svc.create_customer(self.db, **data)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            else:
                self._load_customers()

    def _edit_customer(self, customer):
        dlg = CustomerDialog(customer, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.svc.update_customer(self.db, customer.id, **data)
            self._load_customers()

    def _delete_customer(self, customer):
        reply = QMessageBox.question(
            self, "Silmə", f"'{customer.full_name}' silinsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = self.svc.delete_customer(self.db, customer.id)
            if not ok:
                QMessageBox.warning(self, "Xəta", msg)
            else:
                self.customer_card.clear()
                self._load_customers()

    def _adjust_points(self, customer):
        dlg = PointsAdjustDialog(customer, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            delta  = dlg.delta_spin.value()
            reason = dlg.reason_input.text()
            ok, msg = self.svc.adjust_points(self.db, customer.id, delta, reason)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(msg))
            else:
                QMessageBox.information(self, "Uğurlu", str(msg))
                self._load_customers()

    # ── Endirim Əməliyyatları ──────────────────────────────────────────────────

    def _add_discount(self):
        dlg = DiscountDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["code"]:
                QMessageBox.warning(self, "Xəta", "Kod boş ola bilməz.")
                return
            ok, result = self.svc.create_discount(self.db, **data)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            else:
                self._load_discounts()

    def _edit_discount(self, discount):
        dlg = DiscountDialog(discount, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            data.pop("code", None)
            self.svc.update_discount(self.db, discount.id,
                description=data["description"],
                type=data["disc_type"],
                value=data["value"],
                min_order=data["min_order"],
                usage_limit=data["usage_limit"],
                valid_from=data["valid_from"],
                valid_until=data["valid_until"],
            )
            self._load_discounts()

    def _toggle_discount(self, discount):
        self.svc.toggle_discount(self.db, discount.id)
        self._load_discounts()

    def _delete_discount(self, discount):
        reply = QMessageBox.question(
            self, "Sil", f"'{discount.code}' kodu silinsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.svc.delete_discount(self.db, discount.id)
            self._load_discounts()

    @staticmethod
    def _table_style() -> str:
        return """
            QTableWidget {
                background: #0D0D0D; border: 1px solid #2E2E4E;
                border-radius: 10px; gridline-color: #1E1E2E;
                font-size: 12px; color: #F0EAD6;
            }
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:selected { background: #E8A04530; }
            QTableWidget::item:alternate { background: #141420; }
            QHeaderView::section {
                background: #1C1C2E; color: #8080A0; border: none;
                padding: 8px 10px; font-size: 11px; font-weight: bold;
            }
        """
