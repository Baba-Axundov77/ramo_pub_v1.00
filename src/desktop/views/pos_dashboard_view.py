from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class POSDashboardView(QWidget):
    """Kassa səhifəsi: ödənilməmiş sifarişlər və gündəlik satış xülasəsi."""

    def __init__(self, db, order_service, pos_service, open_payment_cb, parent=None):
        super().__init__(parent)
        self.db = db
        self.order_svc = order_service
        self.pos_svc = pos_service
        self.open_payment_cb = open_payment_cb
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("💳 Kassa")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color:#E8A045;")
        root.addWidget(title)

        self.summary = QLabel("Bugünkü satış: 0.00 ₼ | Ödənilmiş: 0")
        self.summary.setStyleSheet("color:#B0A899;")
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sifariş", "Masa", "Status", "Cəmi", "Aç"]) 
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        refresh_btn = QPushButton("🔄 Yenilə")
        refresh_btn.clicked.connect(self.refresh)
        root.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def refresh(self):
        active = self.order_svc.get_active_orders(self.db)
        summary = self.order_svc.get_today_summary(self.db)
        self.summary.setText(
            f"Bugünkü satış: {summary['total_revenue']:.2f} ₼ | Ödənilmiş: {summary['paid_orders']}"
        )

        self.table.setRowCount(0)
        for order in active:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"#{order.id}"))
            self.table.setItem(row, 1, QTableWidgetItem(str(order.table.number if order.table else "—")))
            self.table.setItem(row, 2, QTableWidgetItem(order.status.value))
            self.table.setItem(row, 3, QTableWidgetItem(f"{float(order.total or 0):.2f} ₼"))

            btn = QPushButton("Ödəniş pəncərəsi")
            btn.clicked.connect(lambda _, o=order: self._open_payment(o))
            self.table.setCellWidget(row, 4, btn)

    def _open_payment(self, order):
        if order.status.value in {"paid", "cancelled"}:
            QMessageBox.information(self, "Məlumat", "Bu sifariş artıq tamamlanıb.")
            return
        self.open_payment_cb(order)
        self.refresh()
