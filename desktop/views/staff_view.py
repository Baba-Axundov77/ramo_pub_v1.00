# desktop/views/staff_view.py — İşçi İdarəsi UI
from __future__ import annotations

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget,
    QDateEdit, QTimeEdit, QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QColor
from config import ROLES


class StaffDialog(QDialog):

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("İşçi əlavə et" if not user else "İşçini redaktə et")
        self.setModal(True); self.setFixedWidth(360)
        self._build()
        if user: self._fill(user)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10); v.setContentsMargins(20, 20, 20, 20)

        def lbl(t):
            l = QLabel(t); l.setObjectName("loginLabel"); return l

        v.addWidget(lbl("TAM AD"))
        self.name_input = QLineEdit(); self.name_input.setFixedHeight(38)
        v.addWidget(self.name_input)

        v.addWidget(lbl("İSTİFADƏÇİ ADI"))
        self.username_input = QLineEdit(); self.username_input.setFixedHeight(38)
        v.addWidget(self.username_input)

        v.addWidget(lbl("ŞİFRƏ" + (" (boş = dəyişmə)" if self.user else "")))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedHeight(38)
        if not self.user:
            self.pass_input.setPlaceholderText("Şifrə daxil edin")
        v.addWidget(self.pass_input)

        v.addWidget(lbl("ROL"))
        self.role_combo = QComboBox(); self.role_combo.setFixedHeight(38)
        for role_key, role_name in ROLES.items():
            self.role_combo.addItem(role_name, role_key)
        v.addWidget(self.role_combo)

        v.addWidget(lbl("TELEFON"))
        self.phone_input = QLineEdit(); self.phone_input.setFixedHeight(38)
        self.phone_input.setPlaceholderText("+994...")
        v.addWidget(self.phone_input)

        if self.user:
            self.active_chk = QCheckBox("Aktiv")
            self.active_chk.setChecked(True)
            v.addWidget(self.active_chk)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        save = QPushButton("💾  Yadda saxla")
        save.setFixedHeight(42); save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42); cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor); cancel.clicked.connect(self.reject)
        btn_row.addWidget(save); btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def _fill(self, user):
        self.name_input.setText(user.full_name)
        self.username_input.setText(user.username)
        self.username_input.setReadOnly(True)
        for i in range(self.role_combo.count()):
            if self.role_combo.itemData(i) == user.role.value:
                self.role_combo.setCurrentIndex(i); break
        self.phone_input.setText(user.phone or "")
        if hasattr(self, "active_chk"):
            self.active_chk.setChecked(user.is_active)

    def get_data(self) -> dict:
        data: dict = {
            "full_name": self.name_input.text().strip(),
            "username":  self.username_input.text().strip(),
            "role":      self.role_combo.currentData(),
            "phone":     self.phone_input.text().strip(),
        }
        pw = self.pass_input.text()
        if pw: data["password"] = pw
        if hasattr(self, "active_chk"):
            data["is_active"] = self.active_chk.isChecked()
        return data


class ShiftDialog(QDialog):

    def __init__(self, users, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Növbə əlavə et")
        self.setModal(True); self.setFixedWidth(340)
        self.users = users
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10); v.setContentsMargins(20, 20, 20, 20)

        def lbl(t):
            l = QLabel(t); l.setObjectName("loginLabel"); return l

        v.addWidget(lbl("İŞÇİ"))
        self.user_combo = QComboBox(); self.user_combo.setFixedHeight(38)
        for u in self.users:
            self.user_combo.addItem(f"{u.full_name} ({ROLES.get(u.role.value,'')})", u.id)
        v.addWidget(self.user_combo)

        v.addWidget(lbl("TARİX"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedHeight(38)
        v.addWidget(self.date_edit)

        row = QHBoxLayout(); row.setSpacing(8)
        s = QVBoxLayout()
        s.addWidget(lbl("BAŞLANĞIC"))
        self.start_time = QTimeEdit(QTime(9, 0))
        self.start_time.setFixedHeight(38)
        s.addWidget(self.start_time)
        row.addLayout(s)

        e = QVBoxLayout()
        e.addWidget(lbl("BİTİŞ"))
        self.end_time = QTimeEdit(QTime(21, 0))
        self.end_time.setFixedHeight(38)
        e.addWidget(self.end_time)
        row.addLayout(e)
        v.addLayout(row)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        save = QPushButton("💾  Əlavə et")
        save.setFixedHeight(40); save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv")
        cancel.setFixedHeight(40); cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor); cancel.clicked.connect(self.reject)
        btn_row.addWidget(save); btn_row.addWidget(cancel)
        v.addLayout(btn_row)

    def get_data(self) -> dict:
        qd  = self.date_edit.date()
        qt1 = self.start_time.time()
        qt2 = self.end_time.time()
        return {
            "user_id":    self.user_combo.currentData(),
            "shift_date": date(qd.year(), qd.month(), qd.day()),
            "start":      f"{qt1.hour():02d}:{qt1.minute():02d}",
            "end":        f"{qt2.hour():02d}:{qt2.minute():02d}",
        }


class StaffView(QWidget):

    def __init__(self, db, staff_service, auth_service, parent=None):
        super().__init__(parent)
        self.db   = db
        self.svc  = staff_service
        self.auth = auth_service
        self._build_ui()
        self._load_staff()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0D0D0D; }
            QTabBar::tab { background: #141420; color: #8080A0; padding: 10px 20px;
                border: none; font-size: 12px; }
            QTabBar::tab:selected { background: #1C1C2E; color: #E8A045;
                border-bottom: 2px solid #E8A045; font-weight: bold; }
        """)

        # ── İşçilər Tab ──────────────────────────────────────────────────────
        staff_tab = QWidget()
        staff_v   = QVBoxLayout(staff_tab)
        staff_v.setContentsMargins(20, 14, 20, 14)
        staff_v.setSpacing(12)

        toolbar = QHBoxLayout()
        self.staff_count_lbl = QLabel("👥  Cəmi: 0")
        self.staff_count_lbl.setStyleSheet("color:#8080A0;font-size:12px;")
        toolbar.addWidget(self.staff_count_lbl)
        toolbar.addStretch()

        if self.auth.is_admin():
            add_btn = QPushButton("➕  İşçi əlavə et")
            add_btn.setFixedHeight(36); add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._add_staff)
            toolbar.addWidget(add_btn)
        staff_v.addLayout(toolbar)

        self.staff_table = self._make_table(
            ["Ad", "İstifadəçi Adı", "Rol", "Telefon", "Status", "Əməliyyat"],
            [5]
        )
        staff_v.addWidget(self.staff_table)
        tabs.addTab(staff_tab, "👥  İşçilər")

        # ── Növbələr Tab ──────────────────────────────────────────────────────
        shift_tab = QWidget()
        shift_v   = QVBoxLayout(shift_tab)
        shift_v.setContentsMargins(20, 14, 20, 14)
        shift_v.setSpacing(12)

        shift_toolbar = QHBoxLayout()
        self.shift_filter = QDateEdit()
        self.shift_filter.setCalendarPopup(True)
        self.shift_filter.setDate(QDate.currentDate())
        self.shift_filter.setFixedHeight(36)
        self.shift_filter.dateChanged.connect(self._load_shifts)
        shift_toolbar.addWidget(QLabel("📅  Tarix:"))
        shift_toolbar.addWidget(self.shift_filter)
        shift_toolbar.addStretch()

        add_shift_btn = QPushButton("➕  Növbə əlavə et")
        add_shift_btn.setFixedHeight(36); add_shift_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_shift_btn.clicked.connect(self._add_shift)
        shift_toolbar.addWidget(add_shift_btn)
        shift_v.addLayout(shift_toolbar)

        self.shift_table = self._make_table(
            ["İşçi", "Rol", "Tarix", "Başlanğıc", "Bitiş", "Müddət", "Əməliyyat"],
            [6]
        )
        shift_v.addWidget(self.shift_table)
        tabs.addTab(shift_tab, "📅  Növbələr")

        root.addWidget(tabs)

    def _make_table(self, headers: list[str], action_cols: list[int]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in action_cols:
            t.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            t.setColumnWidth(col, 130)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget {
                background:#0D0D0D; border:1px solid #2E2E4E;
                border-radius:10px; gridline-color:#1E1E2E;
                font-size:12px; color:#F0EAD6;
            }
            QTableWidget::item { padding:6px 10px; }
            QTableWidget::item:alternate { background:#141420; }
            QHeaderView::section {
                background:#1C1C2E; color:#8080A0; border:none;
                padding:8px 10px; font-size:11px; font-weight:bold;
            }
        """)
        return t

    # ── İşçi Yüklə ───────────────────────────────────────────────────────────

    def _load_staff(self):
        staff = self.svc.get_all_staff(self.db)
        self.staff_count_lbl.setText(f"👥  Cəmi: {len(staff)} işçi")
        self.staff_table.setRowCount(len(staff))
        role_colors = {"admin":"#E8A045","waiter":"#2ECC71","cashier":"#3498DB"}

        for row, user in enumerate(staff):
            self.staff_table.setRowHeight(row, 44)
            role_color = role_colors.get(user.role.value, "#8080A0")
            vals = [
                user.full_name,
                user.username,
                ROLES.get(user.role.value, user.role.value),
                user.phone or "—",
                "✅ Aktiv" if user.is_active else "❌ Deaktiv",
            ]
            for col, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setData(Qt.ItemDataRole.UserRole, user)
                if col == 2:
                    cell.setForeground(QColor(role_color))
                    cell.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                elif col == 4:
                    cell.setForeground(QColor("#2ECC71" if user.is_active else "#E74C3C"))
                self.staff_table.setItem(row, col, cell)

            btn_w = QWidget()
            btn_h = QHBoxLayout(btn_w); btn_h.setContentsMargins(4,2,4,2); btn_h.setSpacing(4)
            if self.auth.is_admin():
                edit_btn = QPushButton("✏️ Redaktə")
                edit_btn.setFixedSize(70, 30); edit_btn.setObjectName("secondaryBtn")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.clicked.connect(lambda _, u=user: self._edit_staff(u))
                btn_h.addWidget(edit_btn)

                if user.id != self.auth.current_user.id:
                    deact_btn = QPushButton("🚫" if user.is_active else "✅")
                    deact_btn.setFixedSize(34, 30)
                    deact_btn.setObjectName("dangerBtn" if user.is_active else "secondaryBtn")
                    deact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    deact_btn.clicked.connect(lambda _, u=user: self._toggle_active(u))
                    btn_h.addWidget(deact_btn)
            btn_h.addStretch()
            self.staff_table.setCellWidget(row, 5, btn_w)

    def _load_shifts(self):
        qd = self.shift_filter.date()
        target = date(qd.year(), qd.month(), qd.day())
        shifts = self.svc.get_shifts(self.db, target_date=target)
        self.shift_table.setRowCount(len(shifts))

        for row, shift in enumerate(shifts):
            self.shift_table.setRowHeight(row, 42)
            user = shift.user
            start = shift.start_time.strftime("%H:%M") if shift.start_time else "—"
            end   = shift.end_time.strftime("%H:%M")   if shift.end_time   else "—"

            if shift.start_time and shift.end_time:
                from datetime import datetime as _dt
                dur_min = int((_dt.combine(target, shift.end_time) -
                               _dt.combine(target, shift.start_time)).total_seconds() / 60)
                dur = f"{dur_min // 60}s {dur_min % 60}d"
            else:
                dur = "—"

            vals = [
                user.full_name if user else "?",
                ROLES.get(user.role.value, "") if user else "?",
                shift.date.strftime("%d.%m.%Y"),
                start, end, dur,
            ]
            for col, val in enumerate(vals):
                self.shift_table.setItem(row, col, QTableWidgetItem(val))

            del_btn = QPushButton("🗑 Sil")
            del_btn.setFixedSize(60, 30); del_btn.setObjectName("dangerBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, s=shift: self._delete_shift(s))
            btn_w = QWidget(); btn_h = QHBoxLayout(btn_w)
            btn_h.setContentsMargins(4,2,4,2); btn_h.addWidget(del_btn); btn_h.addStretch()
            self.shift_table.setCellWidget(row, 6, btn_w)

    # ── Əməliyyatlar ──────────────────────────────────────────────────────────

    def _add_staff(self):
        dlg = StaffDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data.get("password"):
                QMessageBox.warning(self, "Xəta", "Yeni işçi üçün şifrə tələb olunur.")
                return
            ok, result = self.svc.create_staff(
                self.db, data["username"], data["full_name"],
                data["password"], data["role"], data.get("phone","")
            )
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            else:
                self._load_staff()

    def _edit_staff(self, user):
        dlg = StaffDialog(user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            data.pop("username", None)
            self.svc.update_staff(self.db, user.id, **data)
            self._load_staff()

    def _toggle_active(self, user):
        if user.is_active:
            reply = QMessageBox.question(
                self, "Deaktiv et",
                f"{user.full_name} deaktiv edilsin?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes: return
        self.svc.update_staff(self.db, user.id, is_active=not user.is_active)
        self._load_staff()

    def _add_shift(self):
        staff = self.svc.get_all_staff(self.db)
        dlg   = ShiftDialog(staff, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok, result = self.svc.add_shift(self.db, **data)
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
            else:
                self._load_shifts()

    def _delete_shift(self, shift):
        reply = QMessageBox.question(
            self, "Sil", "Bu növbə silinsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.svc.delete_shift(self.db, shift.id)
            self._load_shifts()
