from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QMessageBox,
)

from database.models import OrderStatus


class KitchenOrderCard(QFrame):
    def __init__(self, order, kitchen_service, db, on_changed, parent=None):
        super().__init__(parent)
        self.order = order
        self.kitchen_service = kitchen_service
        self.db = db
        self.on_changed = on_changed
        self.setStyleSheet("background:#1C1C2E;border:1px solid #2E2E4E;border-radius:12px;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        table_name = "-"
        if self.order.table:
            table_name = self.order.table.name or f"Masa {self.order.table.number}"

        title = QLabel(f"#{self.order.id} — {table_name}")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color:#E8A045;")
        layout.addWidget(title)

        created = self.order.created_at.strftime("%H:%M") if self.order.created_at else ""
        status = self.order.status.value
        meta = QLabel(f"Status: {status} | Vaxt: {created}")
        meta.setStyleSheet("color:#B0A899;font-size:11px;")
        layout.addWidget(meta)

        for item in self.order.items:
            row = QHBoxLayout()
            name = item.menu_item.name if item.menu_item else "?"
            left = QLabel(f"• {name} x{item.quantity}")
            left.setStyleSheet("color:#F0EAD6;")
            row.addWidget(left)
            row.addStretch()
            st = QLabel(item.status.value)
            st.setStyleSheet(f"color:{self._status_color(item.status)};font-weight:bold;")
            row.addWidget(st)
            layout.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        preparing_btn = QPushButton("Hazırlanır")
        preparing_btn.clicked.connect(self._set_preparing)
        btns.addWidget(preparing_btn)

        ready_btn = QPushButton("Sifariş Hazır")
        ready_btn.setStyleSheet("background:#2ECC71;color:#0D0D0D;font-weight:bold;")
        ready_btn.clicked.connect(self._set_ready)
        btns.addWidget(ready_btn)
        layout.addLayout(btns)

        for item in self.order.items:
            if item.status in (OrderStatus.ready, OrderStatus.cancelled):
                continue
            item_btn = QPushButton(f"{item.menu_item.name if item.menu_item else '?'} hazır")
            item_btn.setStyleSheet("background:#2E2E4E;color:#F0EAD6;")
            item_btn.clicked.connect(lambda _, item_id=item.id: self._set_item_ready(item_id))
            layout.addWidget(item_btn)

    @staticmethod
    def _status_color(status: OrderStatus) -> str:
        if status == OrderStatus.ready:
            return "#2ECC71"
        if status == OrderStatus.preparing:
            return "#F39C12"
        return "#95A5A6"

    def _set_preparing(self):
        ok, result = self.kitchen_service.mark_preparing(self.db, self.order.id)
        if not ok:
            QMessageBox.warning(self, "Xəta", str(result))
            return
        self.on_changed()

    def _set_ready(self):
        ok, result = self.kitchen_service.mark_ready(self.db, self.order.id)
        if not ok:
            QMessageBox.warning(self, "Xəta", str(result))
            return
        self.on_changed()

    def _set_item_ready(self, item_id: int):
        ok, result = self.kitchen_service.bump_item_ready(self.db, item_id)
        if not ok:
            QMessageBox.warning(self, "Xəta", str(result))
            return
        self.on_changed()


class KitchenView(QWidget):
    def __init__(self, db, kitchen_service, parent=None):
        super().__init__(parent)
        self.db = db
        self.kitchen_service = kitchen_service
        self._build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        head = QLabel("🍳 Mətbəx Queue (KDS)")
        head.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        head.setStyleSheet("color:#E8A045;")
        root.addWidget(head)

        sub = QLabel("Canlı yenilənmə: hər 10 saniyə.")
        sub.setStyleSheet("color:#8080A0;")
        root.addWidget(sub)

        self.refresh_btn = QPushButton("🔄 Yenilə")
        self.refresh_btn.setFixedWidth(140)
        self.refresh_btn.clicked.connect(self.refresh)
        root.addWidget(self.refresh_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        queue = self.kitchen_service.get_queue(self.db)
        if not queue:
            empty = QFrame()
            empty.setStyleSheet("background:#1C1C2E;border:1px solid #2E2E4E;border-radius:12px;")
            empty_l = QVBoxLayout(empty)
            lbl = QLabel("Növbədə aktiv sifariş yoxdur.")
            lbl.setStyleSheet("color:#B0A899;padding:10px;")
            empty_l.addWidget(lbl)
            self.cards_layout.addWidget(empty)
            self.cards_layout.addStretch()
            return

        for order in queue:
            self.cards_layout.addWidget(KitchenOrderCard(order, self.kitchen_service, self.db, self.refresh))
        self.cards_layout.addStretch()
