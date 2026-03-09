# desktop/views/reservation_view.py — Rezervasiya İdarəsi UI
from __future__ import annotations

from datetime import date, time, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QLineEdit, QSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDateEdit, QTimeEdit, QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QColor


class ReservationDialog(QDialog):

    def __init__(self, tables, reservation=None, parent=None):
        super().__init__(parent)
        self.tables      = tables
        self.reservation = reservation
        self.setWindowTitle("Rezervasiya əlavə et" if not reservation else "Rezervasiyanı redaktə et")
        self.setModal(True)
        self.setFixedWidth(400)
        self._build()
        if reservation:
            self._fill(reservation)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10); v.setContentsMargins(20, 20, 20, 20)

        def lbl(t):
            l = QLabel(t); l.setObjectName("loginLabel"); return l

        v.addWidget(lbl("MÜŞTƏRİ ADI"))
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(38)
        self.name_input.setPlaceholderText("Ad Soyad")
        v.addWidget(self.name_input)

        v.addWidget(lbl("TELEFON"))
        self.phone_input = QLineEdit()
        self.phone_input.setFixedHeight(38)
        self.phone_input.setPlaceholderText("+994 XX XXX XX XX")
        v.addWidget(self.phone_input)

        row1 = QHBoxLayout(); row1.setSpacing(8)
        d = QVBoxLayout()
        d.addWidget(lbl("TARİX"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedHeight(38)
        d.addWidget(self.date_edit)
        row1.addLayout(d)

        t = QVBoxLayout()
        t.addWidget(lbl("SAAT"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(19, 0))
        self.time_edit.setFixedHeight(38)
        t.addWidget(self.time_edit)
        row1.addLayout(t)
        v.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(8)
        g = QVBoxLayout()
        g.addWidget(lbl("QONAQ SAYI"))
        self.guest_spin = QSpinBox()
        self.guest_spin.setRange(1, 30)
        self.guest_spin.setValue(2)
        self.guest_spin.setFixedHeight(38)
        g.addWidget(self.guest_spin)
        row2.addLayout(g)

        tb = QVBoxLayout()
        tb.addWidget(lbl("MASA"))
        self.table_combo = QComboBox()
        self.table_combo.setFixedHeight(38)
        for t in self.tables:
            self.table_combo.addItem(f"Masa {t.number} — {t.name} ({t.capacity} nəfər)", t.id)
        row2.addLayout(tb)
        row2.addWidget(self.table_combo)
        v.addLayout(row2)

        v.addWidget(lbl("QEYD (İstəyə bağlı)"))
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(56)
        v.addWidget(self.notes_input)

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

    def _fill(self, r):
        self.name_input.setText(r.customer_name)
        self.phone_input.setText(r.customer_phone or "")
        self.date_edit.setDate(QDate(r.date.year, r.date.month, r.date.day))
        self.time_edit.setTime(QTime(r.time.hour, r.time.minute))
        self.guest_spin.setValue(r.guest_count)
        self.notes_input.setPlainText(r.notes or "")
        for i in range(self.table_combo.count()):
            if self.table_combo.itemData(i) == r.table_id:
                self.table_combo.setCurrentIndex(i)
                break

    def get_data(self) -> dict:
        qdate = self.date_edit.date()
        qtime = self.time_edit.time()
        return {
            "table_id":       self.table_combo.currentData(),
            "customer_name":  self.name_input.text().strip(),
            "customer_phone": self.phone_input.text().strip(),
            "res_date":       date(qdate.year(), qdate.month(), qdate.day()),
            "res_time":       time(qtime.hour(), qtime.minute()),
            "guest_count":    self.guest_spin.value(),
            "notes":          self.notes_input.toPlainText().strip(),
        }


class ReservationView(QWidget):

    def __init__(self, db, reservation_service, table_service, auth_service, parent=None):
        super().__init__(parent)
        self.db       = db
        self.svc      = reservation_service
        self.table_svc = table_service
        self.auth     = auth_service
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        # Toolbar
        toolbar = QHBoxLayout(); toolbar.setSpacing(10)

        self.filter_combo = QComboBox()
        self.filter_combo.setFixedHeight(36)
        self.filter_combo.addItems(["📅  Bu gün", "📆  Bütün gələcək", "🗂️  Hamısı"])
        self.filter_combo.currentIndexChanged.connect(self._load)
        toolbar.addWidget(self.filter_combo)

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setFixedHeight(36)
        self.date_filter.dateChanged.connect(self._load)
        toolbar.addWidget(self.date_filter)

        # Bugün stat
        self.today_lbl = self._badge("📅  Bu gün: 0", "#3498DB")
        self.total_lbl = self._badge("📆  Cəmi: 0", "#8080A0")
        toolbar.addWidget(self.today_lbl)
        toolbar.addWidget(self.total_lbl)
        toolbar.addStretch()

        add_btn = QPushButton("➕  Rezervasiya et")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_reservation)
        toolbar.addWidget(add_btn)
        root.addLayout(toolbar)

        # Cədvəl
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Müştəri", "Telefon", "Tarix", "Saat",
            "Masa", "Qonaq", "Qeyd", "Əməliyyat"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D0D0D; border: 1px solid #2E2E4E;
                border-radius: 10px; gridline-color: #1E1E2E;
                font-size: 12px; color: #F0EAD6;
            }
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:alternate { background: #141420; }
            QHeaderView::section {
                background: #1C1C2E; color: #8080A0; border: none;
                padding: 8px 10px; font-size: 11px; font-weight: bold;
            }
        """)
        root.addWidget(self.table)

    def _badge(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            QLabel {{background:rgba(255,255,255,0.04);
                border:1px solid {color}50;color:{color};
                border-radius:8px;padding:6px 12px;
                font-size:11px;font-weight:bold;}}
        """)
        return lbl

    def _load(self):
        idx   = self.filter_combo.currentIndex()
        today = date.today()

        if idx == 0:
            reservations = self.svc.get_today(self.db)
        elif idx == 1:
            reservations = self.svc.get_all(self.db, upcoming_only=True)
        else:
            reservations = self.svc.get_all(self.db)

        today_count = len(self.svc.get_today(self.db))
        self.today_lbl.setText(f"📅  Bu gün: {today_count}")
        self.total_lbl.setText(f"📆  Cəmi: {len(reservations)}")

        self.table.setRowCount(len(reservations))
        for row, r in enumerate(reservations):
            self.table.setRowHeight(row, 42)
            is_today = r.date == today
            is_past  = r.date < today

            vals = [
                r.customer_name,
                r.customer_phone or "—",
                r.date.strftime("%d.%m.%Y"),
                r.time.strftime("%H:%M"),
                f"Masa {r.table.number}" if r.table else "—",
                f"👥 {r.guest_count}",
                (r.notes or "")[:30],
            ]
            for col, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setData(Qt.ItemDataRole.UserRole, r)
                if is_today:
                    cell.setForeground(QColor("#F39C12"))
                elif is_past:
                    cell.setForeground(QColor("#6A6A8A"))
                self.table.setItem(row, col, cell)

            # Əməliyyatlar
            btn_w = QWidget()
            btn_h = QHBoxLayout(btn_w)
            btn_h.setContentsMargins(4, 2, 4, 2); btn_h.setSpacing(4)

            cancel_btn = QPushButton("❌ Ləğv")
            cancel_btn.setFixedSize(60, 30)
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_btn.setObjectName("dangerBtn")
            cancel_btn.clicked.connect(lambda _, res=r: self._cancel(res))
            btn_h.addWidget(cancel_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(32, 30)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setObjectName("secondaryBtn")
            edit_btn.clicked.connect(lambda _, res=r: self._edit(res))
            btn_h.addWidget(edit_btn)
            btn_h.addStretch()

            self.table.setCellWidget(row, 7, btn_w)

    def _add_reservation(self):
        tables = self.table_svc.get_all(self.db)
        dlg    = ReservationDialog(tables, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["customer_name"]:
                QMessageBox.warning(self, "Xəta", "Müştəri adı boş ola bilməz.")
                return
            ok, result = self.svc.create(self.db, **data)
            if not ok:
                QMessageBox.warning(self, "Rezervasiya Xətası", str(result))
            else:
                self._load()

    def _edit(self, reservation):
        tables = self.table_svc.get_all(self.db)
        dlg    = ReservationDialog(tables, reservation, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok, result = self.svc.create(self.db, **data)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            else:
                self.svc.cancel(self.db, reservation.id)
                self._load()

    def _cancel(self, reservation):
        reply = QMessageBox.question(
            self, "Ləğv et",
            f"{reservation.customer_name} — {reservation.date.strftime('%d.%m.%Y')} "
            f"rezervasiyası ləğv edilsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.svc.cancel(self.db, reservation.id)
            self._load()
