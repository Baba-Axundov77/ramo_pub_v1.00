# desktop/views/pos_view.py — Kassa & Ödəniş Ekranı
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QDialog,
    QButtonGroup, QScrollArea, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import PAYMENT_METHODS


class PaymentView(QDialog):
    """
    Tam ödəniş dialoqu.
    Siqnallar: payment_done(payment_obj)
    """
    payment_done = pyqtSignal(object)

    METHOD_ICONS = {"cash": "💵", "card": "💳", "online": "📱"}

    def __init__(self, order, db, pos_service, auth_service, parent=None):
        super().__init__(parent)
        self.order   = order
        self.db      = db
        self.svc     = pos_service
        self.auth    = auth_service
        self.selected_method  = "cash"
        self.discount_amount  = order.discount_amount or 0.0

        self.setWindowTitle(f"Ödəniş — Sifariş #{order.id}")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._build()
        self._update_totals()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Başlıq ────────────────────────────────────────────────────────────
        title = QLabel(f"💳  Ödəniş  —  {self.order.table.name if self.order.table else ''}")
        title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #E8A045;")
        root.addWidget(title)

        order_info = QLabel(f"Sifariş #{self.order.id}  |  "
                            f"Ofisiant: {self.order.waiter.full_name if self.order.waiter else '?'}")
        order_info.setStyleSheet("color: #8080A0; font-size: 11px;")
        root.addWidget(order_info)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2E2E4E;"); root.addWidget(sep)

        # ── Sifariş xülasəsi ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFixedHeight(160)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:1px solid #2E2E4E;border-radius:8px;"
                             "background:#141420;}")
        items_w = QWidget()
        items_v = QVBoxLayout(items_w)
        items_v.setContentsMargins(12, 8, 12, 8)
        items_v.setSpacing(4)

        from src.core.database.models import OrderStatus
        for oi in self.order.items:
            if oi.status == OrderStatus.cancelled:
                continue
            row = QHBoxLayout()
            name = QLabel(f"{oi.menu_item.name if oi.menu_item else '?'}  ×{oi.quantity}")
            name.setStyleSheet("color: #B0A899; font-size: 11px;")
            price = QLabel(f"{oi.subtotal:.2f} ₼")
            price.setStyleSheet("color: #F0EAD6; font-size: 11px;")
            price.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(name)
            row.addStretch()
            row.addWidget(price)
            items_v.addLayout(row)
        items_v.addStretch()
        scroll.setWidget(items_w)
        root.addWidget(scroll)

        # ── Endirim kodu ──────────────────────────────────────────────────────
        disc_lbl = QLabel("ENDİRİM KODU")
        disc_lbl.setObjectName("loginLabel")
        root.addWidget(disc_lbl)

        disc_row = QHBoxLayout()
        self.disc_input = QLineEdit()
        self.disc_input.setPlaceholderText("Kodu daxil edin (boş buraxın)")
        self.disc_input.setFixedHeight(38)
        disc_row.addWidget(self.disc_input)

        check_btn = QPushButton("Tətbiq et")
        check_btn.setFixedSize(90, 38)
        check_btn.setObjectName("secondaryBtn")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.clicked.connect(self._apply_discount)
        disc_row.addWidget(check_btn)
        root.addLayout(disc_row)

        self.disc_result_lbl = QLabel("")
        self.disc_result_lbl.setStyleSheet("font-size: 11px;")
        root.addWidget(self.disc_result_lbl)

        # ── Ödəniş üsulu ──────────────────────────────────────────────────────
        method_lbl = QLabel("ÖDƏNİŞ ÜSULU")
        method_lbl.setObjectName("loginLabel")
        root.addWidget(method_lbl)

        method_row = QHBoxLayout()
        method_row.setSpacing(8)
        self.method_group = QButtonGroup(self)

        for method, label in PAYMENT_METHODS.items():
            icon = self.METHOD_ICONS.get(method, "💰")
            btn  = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setChecked(method == "cash")
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("method", method)
            btn.setStyleSheet("""
                QPushButton{background:#1C1C2E;color:#8080A0;
                    border:1px solid #3A3A5A;border-radius:10px;
                    font-size:12px;}
                QPushButton:checked{background:#1C3A1C;color:#2ECC71;
                    border:2px solid #2ECC71;font-weight:bold;}
                QPushButton:hover:!checked{border-color:#E8A045;color:#E8A045;}
            """)
            btn.toggled.connect(lambda checked, m=method: self._set_method(m) if checked else None)
            self.method_group.addButton(btn)
            method_row.addWidget(btn)

        self.method_group.setExclusive(True)
        root.addLayout(method_row)

        sep2 = QFrame(); sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #2E2E4E;"); root.addWidget(sep2)

        # ── Cəm məlumatları ───────────────────────────────────────────────────
        totals = QVBoxLayout()
        totals.setSpacing(6)

        def total_row(label, value_lbl_name, color="#F0EAD6", big=False):
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 13 if big else 11,
                               QFont.Weight.Bold if big else QFont.Weight.Normal))
            lbl.setStyleSheet(f"color: {color};")
            val = QLabel("0.00 ₼")
            val.setFont(QFont("Georgia" if big else "Segoe UI",
                               15 if big else 11,
                               QFont.Weight.Bold))
            val.setStyleSheet(f"color: {color};")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            setattr(self, value_lbl_name, val)
            h.addWidget(lbl); h.addStretch(); h.addWidget(val)
            totals.addLayout(h)

        total_row("Ara cəm:",     "sub_lbl")
        total_row("Endirim:",     "disc_lbl2", "#2ECC71")
        total_row("CƏMİ:",        "final_lbl", "#E8A045", big=True)
        root.addLayout(totals)

        # ── Nağd ödəniş kalkulyatoru ──────────────────────────────────────────
        self.cash_frame = QFrame()
        self.cash_frame.setStyleSheet("background:#141420;border-radius:10px;"
                                       "border:1px solid #2E2E4E;")
        cash_v = QVBoxLayout(self.cash_frame)
        cash_v.setContentsMargins(14, 10, 14, 10)
        cash_v.setSpacing(6)

        cash_top = QHBoxLayout()
        cash_top.addWidget(QLabel("Verilən məbləğ (₼):"))
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("0.00")
        self.cash_input.setFixedHeight(36)
        self.cash_input.setMaximumWidth(120)
        self.cash_input.textChanged.connect(self._calc_change)
        cash_top.addStretch(); cash_top.addWidget(self.cash_input)
        cash_v.addLayout(cash_top)

        change_row = QHBoxLayout()
        change_row.addWidget(QLabel("Qaytarılacaq:"))
        self.change_lbl = QLabel("— ₼")
        self.change_lbl.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self.change_lbl.setStyleSheet("color: #2ECC71;")
        self.change_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        change_row.addStretch(); change_row.addWidget(self.change_lbl)
        cash_v.addLayout(change_row)
        root.addWidget(self.cash_frame)

        # ── Alt düymələr ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Ləğv et")
        cancel_btn.setFixedHeight(46)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("✅  Ödənişi Təsdiqlə")
        self.confirm_btn.setFixedHeight(46)
        self.confirm_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.clicked.connect(self._confirm_payment)
        btn_row.addWidget(self.confirm_btn)
        root.addLayout(btn_row)

    # ── Məntiqi ───────────────────────────────────────────────────────────────

    def _set_method(self, method: str):
        self.selected_method = method
        self.cash_frame.setVisible(method == "cash")

    def _apply_discount(self):
        code = self.disc_input.text().strip()
        if not code:
            return
        ok, result = self.svc.check_discount_code(
            self.db, code, self.order.subtotal
        )
        if ok:
            self.discount_amount = result["amount"]
            self.disc_result_lbl.setText(
                f"✅  {result['label']}  →  -{result['amount']:.2f} ₼"
            )
            self.disc_result_lbl.setStyleSheet("color: #2ECC71; font-size: 11px;")
        else:
            self.disc_result_lbl.setText(f"❌  {result}")
            self.disc_result_lbl.setStyleSheet("color: #E74C3C; font-size: 11px;")
            self.discount_amount = self.order.discount_amount or 0.0
        self._update_totals()

    def _update_totals(self):
        sub   = self.order.subtotal
        disc  = self.discount_amount
        final = max(0.0, sub - disc)

        self.sub_lbl.setText(f"{sub:.2f} ₼")
        self.disc_lbl2.setText(f"- {disc:.2f} ₼")
        self.final_lbl.setText(f"{final:.2f} ₼")
        self._calc_change()

    def _calc_change(self):
        try:
            given = float(self.cash_input.text() or 0)
            final = max(0.0, self.order.subtotal - self.discount_amount)
            change = given - final
            if change >= 0:
                self.change_lbl.setText(f"{change:.2f} ₼")
                self.change_lbl.setStyleSheet("color: #2ECC71; font-size: 14px; font-weight: bold;")
            else:
                self.change_lbl.setText(f"— ₼")
                self.change_lbl.setStyleSheet("color: #E74C3C; font-size: 14px;")
        except ValueError:
            self.change_lbl.setText("— ₼")

    def _confirm_payment(self):
        # Nağd ödənişdə məbləğ yetərlidirmi?
        if self.selected_method == "cash":
            try:
                given = float(self.cash_input.text() or 0)
                final = max(0.0, self.order.subtotal - self.discount_amount)
                if given < final:
                    QMessageBox.warning(self, "Xəta",
                        f"Verilən məbləğ ({given:.2f} ₼) cəmi məbləğdən "
                        f"({final:.2f} ₼) azdır.")
                    return
            except ValueError:
                pass

        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setText("İşlənir...")

        code = self.disc_input.text().strip() or None
        ok, result = self.svc.process_payment(
            db             = self.db,
            order_id       = self.order.id,
            method         = self.selected_method,
            cashier_id     = self.auth.current_user.id,
            discount_code  = code,
        )

        self.confirm_btn.setEnabled(True)
        self.confirm_btn.setText("✅  Ödənişi Təsdiqlə")

        if ok:
            self.payment_done.emit(result)
            self._show_receipt(result)
            self.accept()
        else:
            QMessageBox.warning(self, "Ödəniş Xətası", str(result))

    def _show_receipt(self, payment):
        """Tam çek dialoqu — önizləmə, PDF, çap."""
        try:
            from src.desktop.views.receipt_view import ReceiptDialog
            from src.core.modules.printer.printer_service import printer_service
            dlg = ReceiptDialog(payment, self.order, printer_service, parent=self)
            dlg.exec()
        except Exception:
            # Fallback: sadə mesaj
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Ödəniş Tamamlandı ✅")
            msg.setIcon(QMessageBox.Icon.Information)
            method_names = {"cash": "Nağd", "card": "Kart", "online": "Online"}
            text = (
                f"<b>Sifariş #{self.order.id}</b><br>"
                f"Masa: {self.order.table.name if self.order.table else '—'}<br><br>"
                f"Ara cəm:   <b>{payment.amount:.2f} ₼</b><br>"
                f"Endirim:   <b>- {payment.discount_amount:.2f} ₼</b><br>"
                f"<b>CƏMİ:  {payment.final_amount:.2f} ₼</b><br><br>"
                f"Ödəniş üsulu: "
                f"<b>{method_names.get(payment.method.value, '?')}</b><br><br>"
                f"✅ Ödəniş uğurla tamamlandı!"
            )
            msg.setText(text)
            msg.exec()
