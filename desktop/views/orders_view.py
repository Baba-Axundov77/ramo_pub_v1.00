# desktop/views/orders_view.py — Sifariş Ekranı
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QLineEdit,
    QSpinBox, QTextEdit, QMessageBox, QDialog,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class MenuItemButton(QPushButton):
    """Menyu məhsul düyməsi — sifarişə əlavə üçün."""
    add_item = pyqtSignal(object)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        avail_color = "#1C2A1C" if item.is_available else "#2A1C1C"
        border_color = "#2ECC7140" if item.is_available else "#E74C3C40"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {avail_color};
                border: 1px solid {border_color};
                border-radius: 10px;
                text-align: left;
                padding: 10px 14px;
                color: #F0EAD6;
            }}
            QPushButton:hover:enabled {{
                background: #1E3A1E;
                border-color: #E8A045;
            }}
            QPushButton:pressed {{ background: #253A25; }}
            QPushButton:disabled {{ opacity: 0.4; }}
        """)
        self.setEnabled(item.is_available)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        name = QLabel(item.name)
        name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        v.addWidget(name)
        price = QLabel(f"{item.price:.2f} ₼")
        price.setFont(QFont("Segoe UI", 10))
        price.setStyleSheet("color: #E8A045;")
        price.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        v.addWidget(price)

        self.clicked.connect(lambda: self.add_item.emit(self.item))


class OrderItemRow(QFrame):
    """Sifarişdəki bir qələm."""
    qty_changed  = pyqtSignal(int, int)   # order_item_id, new_qty
    remove_item  = pyqtSignal(int)        # order_item_id

    def __init__(self, oi, parent=None):
        super().__init__(parent)
        self.oi = oi
        self.setFixedHeight(52)
        self.setStyleSheet("background: #1C1C2E; border-radius: 8px;")
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 4, 8, 4)
        h.setSpacing(8)

        name = QLabel(self.oi.menu_item.name if self.oi.menu_item else "?")
        name.setFont(QFont("Segoe UI", 11))
        name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        h.addWidget(name)

        # Miqdar azalt
        minus = QPushButton("−")
        minus.setFixedSize(28, 28)
        minus.setCursor(Qt.CursorShape.PointingHandCursor)
        minus.setStyleSheet("QPushButton{background:#2E2E4E;color:#F0EAD6;"
                            "border-radius:6px;font-size:16px;font-weight:bold;}"
                            "QPushButton:hover{background:#E74C3C;}")
        minus.clicked.connect(lambda: self.qty_changed.emit(self.oi.id, self.oi.quantity - 1))
        h.addWidget(minus)

        self.qty_lbl = QLabel(str(self.oi.quantity))
        self.qty_lbl.setFixedWidth(28)
        self.qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        h.addWidget(self.qty_lbl)

        # Miqdar artır
        plus = QPushButton("+")
        plus.setFixedSize(28, 28)
        plus.setCursor(Qt.CursorShape.PointingHandCursor)
        plus.setStyleSheet("QPushButton{background:#2E2E4E;color:#F0EAD6;"
                           "border-radius:6px;font-size:16px;font-weight:bold;}"
                           "QPushButton:hover{background:#2ECC71;}")
        plus.clicked.connect(lambda: self.qty_changed.emit(self.oi.id, self.oi.quantity + 1))
        h.addWidget(plus)

        # Cəmi
        subtotal = QLabel(f"{self.oi.subtotal:.2f} ₼")
        subtotal.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        subtotal.setStyleSheet("color: #E8A045;")
        subtotal.setFixedWidth(70)
        subtotal.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(subtotal)

        # Sil
        del_btn = QPushButton("×")
        del_btn.setFixedSize(26, 26)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton{background:transparent;color:#606080;"
                              "border-radius:6px;font-size:16px;}"
                              "QPushButton:hover{color:#E74C3C;background:#E74C3C20;}")
        del_btn.clicked.connect(lambda: self.remove_item.emit(self.oi.id))
        h.addWidget(del_btn)


class OrdersView(QWidget):
    """
    Sifariş ekranı.
    Sol: menyu, Sağ: aktiv sifariş.
    Siqnallar: payment_requested(order)
    """
    payment_requested = pyqtSignal(object)

    def __init__(self, db, order_service, menu_service, auth_service, parent=None):
        super().__init__(parent)
        self.db       = db
        self.order_svc = order_service
        self.menu_svc  = menu_service
        self.auth      = auth_service
        self.current_order = None
        self.current_table = None

        self._build_ui()
        self._load_active_orders()

    def open_for_table(self, table, existing_order=None):
        """Masa üçün yeni sifariş ekranını aç."""
        self.current_table = table
        if existing_order:
            self.current_order = existing_order
        else:
            ok, result = self.order_svc.create_order(
                self.db, table.id, self.auth.current_user.id
            )
            if not ok:
                QMessageBox.warning(self, "Xəta", str(result))
                return
            self.current_order = result

        self.table_lbl.setText(f"🪑  {table.name}  —  Sifariş #{self.current_order.id}")
        self._load_menu()
        self._refresh_order()
        self._load_active_orders()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#2E2E4E;width:1px;}")

        # ── Sol Panel — Menyu ─────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background: #0D0D0D;")
        left_v = QVBoxLayout(left)
        left_v.setContentsMargins(16, 14, 8, 14)
        left_v.setSpacing(10)

        # Kateqoriya seçici
        self.cat_scroll = QScrollArea()
        self.cat_scroll.setFixedHeight(46)
        self.cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.cat_inner = QWidget()
        self.cat_inner.setStyleSheet("background:transparent;")
        self.cat_row   = QHBoxLayout(self.cat_inner)
        self.cat_row.setContentsMargins(0, 0, 0, 0)
        self.cat_row.setSpacing(6)
        self.cat_scroll.setWidget(self.cat_inner)
        self.cat_scroll.setWidgetResizable(True)
        left_v.addWidget(self.cat_scroll)
        self.cat_btns = {}

        # Axtarış
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Məhsul axtar...")
        self.search.setFixedHeight(36)
        self.search.textChanged.connect(self._search_menu)
        left_v.addWidget(self.search)

        # Məhsul grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.menu_grid_widget = QWidget()
        self.menu_grid_widget.setStyleSheet("background:transparent;")
        self.menu_grid = QGridLayout(self.menu_grid_widget)
        self.menu_grid.setSpacing(8)
        scroll.setWidget(self.menu_grid_widget)
        left_v.addWidget(scroll)
        splitter.addWidget(left)

        # ── Sağ Panel — Sifariş ───────────────────────────────────────────────
        right = QFrame()
        right.setFixedWidth(340)
        right.setStyleSheet("background:#141420; border-left:1px solid #2E2E4E;")
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        # Başlıq
        self.table_lbl = QLabel("Masa seçilməyib")
        self.table_lbl.setFixedHeight(50)
        self.table_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.table_lbl.setStyleSheet("color:#E8A045; padding:0 16px; "
                                      "background:#0D0D18; border-bottom:1px solid #2E2E4E;")
        right_v.addWidget(self.table_lbl)

        # Aktiv sifarişlər siyahısı (kiçik)
        active_lbl = QLabel("  AKTİV SİFARİŞLƏR")
        active_lbl.setFixedHeight(28)
        active_lbl.setStyleSheet("color:#8080A0;font-size:10px;font-weight:bold;"
                                  "letter-spacing:1px;background:#0D0D18;padding:0 16px;")
        right_v.addWidget(active_lbl)

        self.active_list = QListWidget()
        self.active_list.setFixedHeight(120)
        self.active_list.setStyleSheet("""
            QListWidget{background:#0D0D18;border:none;border-bottom:1px solid #2E2E4E;}
            QListWidget::item{color:#B0A899;padding:6px 14px;font-size:11px;}
            QListWidget::item:selected{background:#1C1C2E;color:#E8A045;}
            QListWidget::item:hover:!selected{background:#1A1A28;}
        """)
        self.active_list.itemClicked.connect(self._on_active_order_click)
        right_v.addWidget(self.active_list)

        # Sifariş qələmləri
        items_lbl = QLabel("  SİFARİŞ")
        items_lbl.setFixedHeight(32)
        items_lbl.setStyleSheet("color:#8080A0;font-size:10px;font-weight:bold;"
                                 "letter-spacing:1px;border-bottom:1px solid #2E2E4E;"
                                 "padding:0 16px;")
        right_v.addWidget(items_lbl)

        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.order_items_widget = QWidget()
        self.order_items_widget.setStyleSheet("background:transparent;")
        self.order_items_layout = QVBoxLayout(self.order_items_widget)
        self.order_items_layout.setSpacing(6)
        self.order_items_layout.setContentsMargins(10, 8, 10, 8)
        self.order_items_layout.addStretch()
        scroll2.setWidget(self.order_items_widget)
        right_v.addWidget(scroll2)

        # Cəm
        total_frame = QFrame()
        total_frame.setFixedHeight(130)
        total_frame.setStyleSheet("background:#0D0D18;border-top:1px solid #2E2E4E;")
        total_v = QVBoxLayout(total_frame)
        total_v.setContentsMargins(16, 12, 16, 12)
        total_v.setSpacing(4)

        sub_row = QHBoxLayout()
        sub_row.addWidget(QLabel("Ara cəm:"))
        self.subtotal_lbl = QLabel("0.00 ₼")
        self.subtotal_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        sub_row.addWidget(self.subtotal_lbl)
        total_v.addLayout(sub_row)

        disc_row = QHBoxLayout()
        disc_row.addWidget(QLabel("Endirim:"))
        self.discount_lbl = QLabel("0.00 ₼")
        self.discount_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.discount_lbl.setStyleSheet("color:#2ECC71;")
        disc_row.addWidget(self.discount_lbl)
        total_v.addLayout(disc_row)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2E2E4E;"); total_v.addWidget(sep)

        total_row = QHBoxLayout()
        tot_lbl = QLabel("CƏMİ:")
        tot_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        total_row.addWidget(tot_lbl)
        self.total_lbl = QLabel("0.00 ₼")
        self.total_lbl.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        self.total_lbl.setStyleSheet("color:#E8A045;")
        self.total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_row.addWidget(self.total_lbl)
        total_v.addLayout(total_row)

        right_v.addWidget(total_frame)

        # Düymələr
        btn_frame = QFrame()
        btn_frame.setFixedHeight(56)
        btn_frame.setStyleSheet("background:#0D0D18;")
        btn_h = QHBoxLayout(btn_frame)
        btn_h.setContentsMargins(10, 8, 10, 8)
        btn_h.setSpacing(8)

        cancel_btn = QPushButton("❌  Ləğv et")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._cancel_order)
        btn_h.addWidget(cancel_btn)

        self.pay_btn = QPushButton("💳  Ödəniş  →")
        self.pay_btn.setFixedHeight(38)
        self.pay_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.clicked.connect(self._request_payment)
        btn_h.addWidget(self.pay_btn)

        right_v.addWidget(btn_frame)
        splitter.addWidget(right)
        splitter.setSizes([760, 340])
        root.addWidget(splitter)

    # ── Menyu Yüklə ───────────────────────────────────────────────────────────

    def _load_menu(self, cat_id=None, query=""):
        # Kateqoriya düymələri
        while self.cat_row.count():
            item = self.cat_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.cat_btns.clear()

        cats = self.menu_svc.get_categories(self.db)
        all_btn = self._make_cat_btn("🍽️ Hamısı", None)
        self.cat_row.addWidget(all_btn)
        for cat in cats:
            b = self._make_cat_btn(f"{cat.icon} {cat.name}", cat.id)
            self.cat_row.addWidget(b)
        self.cat_row.addStretch()

        self._load_menu_items(cat_id, query)

    def _make_cat_btn(self, label, cat_id):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(cat_id is None)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton{background:transparent;color:#8080A0;border:1px solid #3A3A5A;
                border-radius:8px;padding:0 12px;font-size:11px;}
            QPushButton:checked{background:#E8A045;color:#0D0D0D;border-color:#E8A045;
                font-weight:bold;}
            QPushButton:hover:!checked{border-color:#E8A045;color:#E8A045;}
        """)
        btn.clicked.connect(lambda _, c=cat_id: self._filter_cat(c))
        self.cat_btns[cat_id] = btn
        return btn

    def _filter_cat(self, cat_id):
        for cid, btn in self.cat_btns.items():
            btn.setChecked(cid == cat_id)
        self._load_menu_items(cat_id)

    def _load_menu_items(self, cat_id=None, query=""):
        while self.menu_grid.count():
            item = self.menu_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if query:
            items = self.menu_svc.search(self.db, query)
        else:
            items = self.menu_svc.get_items(self.db, cat_id)

        cols = 3
        for i, item in enumerate(items):
            btn = MenuItemButton(item)
            btn.add_item.connect(self._add_to_order)
            self.menu_grid.addWidget(btn, i // cols, i % cols)

    def _search_menu(self, text):
        self._load_menu_items(query=text)

    # ── Sifariş Əməliyyatları ─────────────────────────────────────────────────

    def _add_to_order(self, menu_item):
        if not self.current_order:
            QMessageBox.warning(self, "Xəbərdarlıq",
                "Əvvəlcə masa seçib sifariş başladın.")
            return
        ok, result = self.order_svc.add_item(
            self.db, self.current_order.id, menu_item.id
        )
        if ok:
            self.current_order = result
            self._refresh_order()
        else:
            QMessageBox.warning(self, "Xəta", str(result))

    def _on_qty_change(self, oi_id, qty):
        ok, result = self.order_svc.update_item_qty(self.db, oi_id, qty)
        if ok:
            self.current_order = result
            self._refresh_order()

    def _on_remove_item(self, oi_id):
        ok, result = self.order_svc.remove_item(self.db, oi_id)
        if ok:
            self.current_order = result
            self._refresh_order()

    def _cancel_order(self):
        if not self.current_order:
            return
        reply = QMessageBox.question(
            self, "Sifarişi ləğv et",
            f"Sifariş #{self.current_order.id} ləğv edilsin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.order_svc.cancel_order(self.db, self.current_order.id)
            self.current_order = None
            self.current_table = None
            self.table_lbl.setText("Masa seçilməyib")
            self._refresh_order()
            self._load_active_orders()

    def _request_payment(self):
        if not self.current_order:
            return
        if not self.current_order.items:
            QMessageBox.warning(self, "Xəbərdarlıq", "Sifariş boşdur.")
            return
        self.payment_requested.emit(self.current_order)

    def _on_active_order_click(self, list_item):
        order = list_item.data(Qt.ItemDataRole.UserRole)
        if order:
            self.current_order = order
            self.current_table = order.table
            self.table_lbl.setText(
                f"🪑  {order.table.name if order.table else '?'}  —  Sifariş #{order.id}"
            )
            self._refresh_order()

    # ── Görünüşü Yenilə ───────────────────────────────────────────────────────

    def _refresh_order(self):
        # Qələmləri sil
        while self.order_items_layout.count() > 1:
            item = self.order_items_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not self.current_order or not self.current_order.items:
            empty = QLabel("Hələ heç bir məhsul əlavə edilməyib.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#4A4A6A; font-size:12px; padding:20px;")
            self.order_items_layout.insertWidget(0, empty)
            self.subtotal_lbl.setText("0.00 ₼")
            self.discount_lbl.setText("0.00 ₼")
            self.total_lbl.setText("0.00 ₼")
            return

        from database.models import OrderStatus
        active_items = [oi for oi in self.current_order.items
                        if oi.status != OrderStatus.cancelled]

        for oi in active_items:
            row = OrderItemRow(oi)
            row.qty_changed.connect(self._on_qty_change)
            row.remove_item.connect(self._on_remove_item)
            self.order_items_layout.insertWidget(
                self.order_items_layout.count() - 1, row
            )

        self.subtotal_lbl.setText(f"{self.current_order.subtotal:.2f} ₼")
        disc = self.current_order.discount_amount or 0
        self.discount_lbl.setText(f"- {disc:.2f} ₼")
        self.total_lbl.setText(f"{self.current_order.total:.2f} ₼")

    def _load_active_orders(self):
        self.active_list.clear()
        orders = self.order_svc.get_active_orders(self.db)
        for order in orders:
            table_name = order.table.name if order.table else "?"
            text = f"🪑 {table_name}  |  #{order.id}  |  {order.total:.2f} ₼"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, order)
            self.active_list.addItem(item)
