# desktop/views/receipt_view.py
# Python 3.10 uyğun
"""Çek önizləmə & çap dialoqu."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QMessageBox,
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ReceiptDialog(QDialog):
    """
    Ödəniş tamamlandıqdan sonra göstərilən çek dialoqu.
    Önizləmə + PDF / Printer / Mətn seçimi.
    """

    def __init__(
        self,
        payment,
        order,
        printer_service,
        parent=None
    ):
        super().__init__(parent)
        self.payment         = payment
        self.order           = order
        self.printer_service = printer_service

        self.setWindowTitle(f"Çek — Sifariş #{order.id}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(560)
        self._build()
        self._load_receipt()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Başlıq
        title_row = QHBoxLayout()
        icon = QLabel("🧾")
        icon.setFont(QFont("Segoe UI Emoji", 28))
        title_row.addWidget(icon)

        title_info = QVBoxLayout()
        t = QLabel(f"Çek — Sifariş #{self.order.id}")
        t.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        t.setStyleSheet("color: #E8A045;")
        title_info.addWidget(t)

        table_name  = self.order.table.name if self.order.table else "—"
        waiter_name = self.order.waiter.full_name if self.order.waiter else "—"
        sub = QLabel(f"Masa: {table_name}  |  Ofisiant: {waiter_name}")
        sub.setStyleSheet("color: #8080A0; font-size: 11px;")
        title_info.addWidget(sub)
        title_row.addLayout(title_info)
        title_row.addStretch()

        # Ödəniş xülasəsi
        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            "background: #1C1C2E; border: 1px solid #E8A04560; border-radius: 10px;"
        )
        sf_h = QHBoxLayout(summary_frame)
        sf_h.setContentsMargins(16, 10, 16, 10)
        sf_h.setSpacing(24)

        method_map = {"cash": "💵 Nağd", "card": "💳 Kart", "online": "📱 Online"}
        method_str = method_map.get(self.payment.method.value, "?")

        for label, value, color in [
            ("Məbləğ",   f"{self.payment.amount:.2f} ₼",        "#8080A0"),
            ("Endirim",  f"-{self.payment.discount_amount:.2f} ₼","#2ECC71"),
            ("CƏMİ",     f"{self.payment.final_amount:.2f} ₼",   "#E8A045"),
            ("Üsul",     method_str,                              "#3498DB"),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6A6A8A; font-size: 10px;")
            val = QLabel(value)
            val.setFont(QFont("Georgia" if label == "CƏMİ" else "Segoe UI",
                               13 if label == "CƏMİ" else 11,
                               QFont.Weight.Bold))
            val.setStyleSheet(f"color: {color};")
            col.addWidget(lbl)
            col.addWidget(val)
            sf_h.addLayout(col)

        sf_h.addStretch()
        title_row.addWidget(summary_frame)
        root.addLayout(title_row)

        # ── Çek önizləməsi ────────────────────────────────────────────────────
        preview_lbl = QLabel("ÇEK ÖNİZLƏMƏSİ")
        preview_lbl.setObjectName("loginLabel")
        root.addWidget(preview_lbl)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Courier New", 9))
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background: #0A0A14;
                color: #F0EAD6;
                border: 1px solid #2E2E4E;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.preview_text.setMinimumHeight(220)
        root.addWidget(self.preview_text)

        # ── Çap seçimləri ─────────────────────────────────────────────────────
        print_frame = QFrame()
        print_frame.setStyleSheet(
            "background: #141420; border: 1px solid #2E2E4E; border-radius: 10px;"
        )
        pf_v = QVBoxLayout(print_frame)
        pf_v.setContentsMargins(14, 10, 14, 10)
        pf_v.setSpacing(8)

        method_lbl = QLabel("ÇAP ÜSULU")
        method_lbl.setObjectName("loginLabel")
        pf_v.addWidget(method_lbl)

        method_row = QHBoxLayout()
        method_row.setSpacing(8)

        self.pdf_btn = QPushButton("📄  PDF Yarat")
        self.pdf_btn.setFixedHeight(40)
        self.pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background: #1C2A3A; color: #3498DB;
                border: 1px solid #3498DB60; border-radius: 8px;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #3498DB20; border-color: #3498DB; }
        """)
        self.pdf_btn.clicked.connect(self._print_pdf)
        method_row.addWidget(self.pdf_btn)

        self.txt_btn = QPushButton("📝  Mətni Saxla")
        self.txt_btn.setFixedHeight(40)
        self.txt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.txt_btn.setStyleSheet("""
            QPushButton {
                background: #1C3A1C; color: #2ECC71;
                border: 1px solid #2ECC7160; border-radius: 8px;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #2ECC7120; border-color: #2ECC71; }
        """)
        self.txt_btn.clicked.connect(self._save_text)
        method_row.addWidget(self.txt_btn)

        self.copy_btn = QPushButton("📋  Kopyala")
        self.copy_btn.setFixedHeight(40)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: #2A2A1C; color: #E8A045;
                border: 1px solid #E8A04560; border-radius: 8px;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #E8A04520; border-color: #E8A045; }
        """)
        self.copy_btn.clicked.connect(self._copy_text)
        method_row.addWidget(self.copy_btn)
        pf_v.addLayout(method_row)
        root.addWidget(print_frame)

        # ── Bağla düyməsi ─────────────────────────────────────────────────────
        close_btn = QPushButton("✅  Bağla")
        close_btn.setFixedHeight(44)
        close_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def _load_receipt(self):
        text = self.printer_service.get_receipt_text(self.payment, self.order)
        self.preview_text.setPlainText(text)

    def _print_pdf(self):
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.setText("⏳  Yaradılır...")
        ok, result = self.printer_service.print_to_pdf(self.payment, self.order)
        self.pdf_btn.setEnabled(True)
        self.pdf_btn.setText("📄  PDF Yarat")

        if ok:
            msg = QMessageBox(self)
            msg.setWindowTitle("PDF Hazır ✅")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(f"PDF çek yaradıldı:\n\n{result}")
            msg.exec()
        else:
            QMessageBox.warning(self, "PDF Xətası", result)

    def _save_text(self):
        ok, result = self.printer_service.save_receipt_text(self.payment, self.order)
        if ok:
            QMessageBox.information(self, "Saxlandı ✅",
                f"Çek mətni saxlandı:\n{result}")
        else:
            QMessageBox.warning(self, "Xəta", result)

    def _copy_text(self):
        text = self.preview_text.toPlainText()
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.copy_btn.setText("✅  Kopyalandı!")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(
            2000,
            lambda: self.copy_btn.setText("📋  Kopyala")
        )
