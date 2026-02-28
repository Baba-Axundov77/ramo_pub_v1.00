# desktop/views/menu_view.py — Menyu İdarəsi UI
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout, QDialog, QLineEdit,
    QDoubleSpinBox, QTextEdit, QComboBox, QCheckBox,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class MenuItemCard(QFrame):
    """Menyu məhsul kartı — şəkil dəstəyi ilə."""
    edit_clicked   = pyqtSignal(object)
    toggle_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedHeight(90)
        self._build()
        self.refresh(item)

    def _build(self):
        from desktop.views.widgets.image_picker import RoundedImageLabel
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 8, 14, 8)
        h.setSpacing(12)

        # Şəkil thumbnail
        self.thumb = RoundedImageLabel(
            None, width=64, height=64, radius=8,
            placeholder_icon="🍽️", placeholder_text=""
        )
        h.addWidget(self.thumb)

        info_v = QVBoxLayout()
        self.name_lbl = QLabel()
        self.name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.desc_lbl = QLabel()
        self.desc_lbl.setFont(QFont("Segoe UI", 9))
        self.desc_lbl.setStyleSheet("color: #8080A0;")
        self.price_lbl = QLabel()
        self.price_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        info_v.addWidget(self.name_lbl)
        info_v.addWidget(self.desc_lbl)
        info_v.addWidget(self.price_lbl)
        h.addLayout(info_v)
        h.addStretch()

        btn_v = QVBoxLayout()
        btn_v.setSpacing(4)
        self.avail_btn = QPushButton()
        self.avail_btn.setFixedSize(84, 26)
        self.avail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avail_btn.clicked.connect(lambda: self.toggle_clicked.emit(self.item))
        btn_v.addWidget(self.avail_btn)

        edit_btn = QPushButton("✏️ Redaktə")
        edit_btn.setFixedSize(84, 26)
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.item))
        btn_v.addWidget(edit_btn)

        del_btn = QPushButton("🗑 Sil")
        del_btn.setFixedSize(84, 26)
        del_btn.setObjectName("dangerBtn")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.item))
        btn_v.addWidget(del_btn)
        h.addLayout(btn_v)

    def refresh(self, item):
        self.item = item
        available = item.is_available
        self.setStyleSheet(f"""
            MenuItemCard {{
                background: {'#1C2A1C' if available else '#2A1C1C'};
                border: 1px solid {'#2ECC7160' if available else '#E74C3C60'};
                border-radius: 10px;
            }}
        """)
        # Thumbnail yenilə
        self.thumb.set_image(getattr(item, 'image_path', None))

        self.name_lbl.setText(item.name)
        self.name_lbl.setStyleSheet(f"color: {'#F0EAD6' if available else '#808080'};")
        desc = item.description or ""
        self.desc_lbl.setText(desc[:45] + "…" if len(desc) > 45 else desc)
        self.price_lbl.setText(f"{item.price:.2f} ₼")
        self.price_lbl.setStyleSheet("color: #E8A045;")
        self.avail_btn.setText("✅ Aktiv" if available else "❌ Deaktiv")
        self.avail_btn.setStyleSheet(
            f"QPushButton{{background:{'#2ECC7130' if available else '#E74C3C30'};"
            f"color:{'#2ECC71' if available else '#E74C3C'};"
            f"border:1px solid {'#2ECC7160' if available else '#E74C3C60'};"
            f"border-radius:6px;font-size:10px;}}"
        )


class ItemDialog(QDialog):
    """Məhsul əlavə et / redaktə et — şəkil dəstəyi ilə."""

    def __init__(self, categories, item=None, parent=None):
        super().__init__(parent)
        self.categories = categories
        self.item = item
        self.setWindowTitle("Məhsul əlavə et" if not item else "Məhsulu redaktə et")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._build()
        if item:
            self._fill(item)

    def _build(self):
        from desktop.views.widgets.image_picker import ImagePickerWidget, MENU_IMGS
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # ── Sol — Form ────────────────────────────────────────────────────────
        form_v = QVBoxLayout()
        form_v.setSpacing(8)

        def lbl(t):
            l = QLabel(t); l.setObjectName("loginLabel"); return l

        form_v.addWidget(lbl("KATEQORİYA"))
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(38)
        for cat in self.categories:
            self.cat_combo.addItem(f"{cat.icon}  {cat.name}", cat.id)
        form_v.addWidget(self.cat_combo)

        form_v.addWidget(lbl("MƏHSUL ADI"))
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(38)
        form_v.addWidget(self.name_input)

        form_v.addWidget(lbl("TƏSVİR (İstəyə bağlı)"))
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(56)
        form_v.addWidget(self.desc_input)

        price_row = QHBoxLayout(); price_row.setSpacing(8)
        pl = QVBoxLayout()
        pl.addWidget(lbl("QİYMƏT (₼)"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999)
        self.price_spin.setDecimals(2)
        self.price_spin.setFixedHeight(38)
        pl.addWidget(self.price_spin)
        price_row.addLayout(pl)

        cl = QVBoxLayout()
        cl.addWidget(lbl("MAYA DƏYƏRİ (₼)"))
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 9999)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setFixedHeight(38)
        cl.addWidget(self.cost_spin)
        price_row.addLayout(cl)
        form_v.addLayout(price_row)

        self.avail_chk = QCheckBox("✅  Aktiv / Mövcud")
        self.avail_chk.setChecked(True)
        form_v.addWidget(self.avail_chk)
        form_v.addStretch()
        main_row.addLayout(form_v, 3)

        # ── Sağ — Şəkil ───────────────────────────────────────────────────────
        img_v = QVBoxLayout()
        img_v.setAlignment(Qt.AlignmentFlag.AlignTop)
        img_lbl = lbl("MƏHSUL ŞƏKLİ")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_v.addWidget(img_lbl)

        prefix = f"menu_{self.item.id}" if self.item else "menu_new"
        self.img_picker = ImagePickerWidget(
            dest_dir=MENU_IMGS,
            image_path=self.item.image_path if self.item else None,
            prefix=prefix,
            preview_w=190,
            preview_h=155,
            placeholder_icon="🍽️",
            placeholder_text="Məhsul şəkli yoxdur",
        )
        img_v.addWidget(self.img_picker)
        img_v.addStretch()
        main_row.addLayout(img_v, 2)

        root.addLayout(main_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2E2E4E;")
        root.addWidget(sep)

        row = QHBoxLayout(); row.setSpacing(8)
        save = QPushButton("💾  Yadda saxla")
        save.setFixedHeight(42)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Ləğv et")
        cancel.setFixedHeight(42)
        cancel.setObjectName("secondaryBtn")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        row.addWidget(save); row.addWidget(cancel)
        root.addLayout(row)

    def _fill(self, item):
        for i in range(self.cat_combo.count()):
            if self.cat_combo.itemData(i) == item.category_id:
                self.cat_combo.setCurrentIndex(i)
                break
        self.name_input.setText(item.name)
        self.desc_input.setPlainText(item.description or "")
        self.price_spin.setValue(item.price)
        self.cost_spin.setValue(item.cost_price or 0)
        self.avail_chk.setChecked(item.is_available)
        if item.image_path:
            self.img_picker.set_image_path(item.image_path)

    def get_data(self):
        return {
            "category_id":  self.cat_combo.currentData(),
            "name":         self.name_input.text().strip(),
            "description":  self.desc_input.toPlainText().strip() or None,
            "price":        self.price_spin.value(),
            "cost_price":   self.cost_spin.value(),
            "is_available": self.avail_chk.isChecked(),
            "image_path":   self.img_picker.get_image_path(),
        }


class MenuView(QWidget):
    """Menyu İdarəsi — əsas görünüş."""

    def __init__(self, db, menu_service, auth_service, parent=None):
        super().__init__(parent)
        self.db   = db
        self.svc  = menu_service
        self.auth = auth_service
        self.item_cards = {}
        self.current_cat_id = None

        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #2E2E4E; width: 1px; }")

        # ── Sol — Kateqoriyalar ───────────────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(220)
        left.setStyleSheet("background: #141420; border-right: 1px solid #2E2E4E;")
        left_v = QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(0)

        cat_header = QLabel("  KATEQORİYALAR")
        cat_header.setFixedHeight(44)
        cat_header.setStyleSheet("color: #8080A0; font-size: 11px; font-weight: bold; "
                                  "letter-spacing: 1px; background: #0D0D18; "
                                  "border-bottom: 1px solid #2E2E4E;")
        left_v.addWidget(cat_header)

        self.cat_list = QListWidget()
        self.cat_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; padding: 4px; }
            QListWidget::item { color: #B0A899; padding: 10px 14px; border-radius: 8px;
                                margin: 2px 4px; }
            QListWidget::item:selected { background: #1C1C2E; color: #E8A045; }
            QListWidget::item:hover:!selected { background: #1C1C2E; color: #F0EAD6; }
        """)
        self.cat_list.currentRowChanged.connect(self._on_category_change)
        left_v.addWidget(self.cat_list)

        if self.auth.is_admin():
            add_cat_btn = QPushButton("➕  Kateqoriya əlavə et")
            add_cat_btn.setFixedHeight(40)
            add_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_cat_btn.setStyleSheet("margin: 8px;")
            add_cat_btn.clicked.connect(self._add_category)
            left_v.addWidget(add_cat_btn)

        splitter.addWidget(left)

        # ── Sağ — Məhsullar ───────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: #0D0D0D;")
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(20, 16, 20, 16)
        right_v.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Məhsul axtar...")
        self.search_input.setFixedHeight(38)
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self._search)
        toolbar.addWidget(self.search_input)
        toolbar.addStretch()

        self.item_count_lbl = QLabel()
        self.item_count_lbl.setStyleSheet("color: #8080A0; font-size: 11px;")
        toolbar.addWidget(self.item_count_lbl)

        if self.auth.is_admin():
            add_item_btn = QPushButton("➕  Məhsul əlavə et")
            add_item_btn.setFixedHeight(36)
            add_item_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_item_btn.clicked.connect(self._add_item)
            toolbar.addWidget(add_item_btn)

        right_v.addLayout(toolbar)

        # Məhsul siyahısı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.items_widget = QWidget()
        self.items_widget.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.items_widget)
        self.items_layout.setSpacing(8)
        self.items_layout.setContentsMargins(0, 0, 8, 0)
        self.items_layout.addStretch()

        scroll.setWidget(self.items_widget)
        right_v.addWidget(scroll)
        splitter.addWidget(right)
        splitter.setSizes([220, 780])
        root.addWidget(splitter)

    # ── Kateqoriya ────────────────────────────────────────────────────────────

    def _load_categories(self):
        cats = self.svc.get_categories(self.db)
        self.cat_list.clear()
        # "Hamısı" seçimi
        all_item = QListWidgetItem("🍽️  Bütün məhsullar")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.cat_list.addItem(all_item)

        for cat in cats:
            item = QListWidgetItem(f"{cat.icon}  {cat.name}")
            item.setData(Qt.ItemDataRole.UserRole, cat.id)
            self.cat_list.addItem(item)
        self.cat_list.setCurrentRow(0)

    def _on_category_change(self, row):
        item = self.cat_list.item(row)
        if item:
            self.current_cat_id = item.data(Qt.ItemDataRole.UserRole)
            self._load_items()

    def _add_category(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Yeni Kateqoriya", "Kateqoriya adı:")
        if ok and name.strip():
            self.svc.create_category(self.db, name.strip())
            self._load_categories()

    # ── Məhsul ───────────────────────────────────────────────────────────────

    def _load_items(self, query: str = ""):
        # Köhnə kartları sil
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.item_cards.clear()

        if query:
            items = self.svc.search(self.db, query)
        else:
            items = self.svc.get_items(self.db, self.current_cat_id)

        self.item_count_lbl.setText(f"{len(items)} məhsul")

        if not items:
            empty = QLabel("Bu kateqoriyada məhsul yoxdur.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #4A4A6A; font-size: 13px; padding: 40px;")
            self.items_layout.insertWidget(0, empty)
            return

        for item in items:
            card = MenuItemCard(item)
            card.edit_clicked.connect(self._edit_item)
            card.toggle_clicked.connect(self._toggle_item)
            card.delete_clicked.connect(self._delete_item)
            self.item_cards[item.id] = card
            self.items_layout.insertWidget(self.items_layout.count() - 1, card)

    def _search(self, query: str):
        self._load_items(query)

    def _add_item(self):
        cats = self.svc.get_categories(self.db)
        dlg = ItemDialog(cats, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Xəta", "Məhsul adı boş ola bilməz.")
                return
            self.svc.create_item(self.db, **data)
            self._load_items()

    def _edit_item(self, item):
        cats = self.svc.get_categories(self.db)
        dlg = ItemDialog(cats, item, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.svc.update_item(self.db, item.id, **data)
            self._load_items()

    def _toggle_item(self, item):
        self.svc.toggle_available(self.db, item.id)
        self._load_items()

    def _delete_item(self, item):
        reply = QMessageBox.question(
            self, "Silmə təsdiqi",
            f"'{item.name}' məhsulunu silmək istəyirsiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.svc.delete_item(self.db, item.id)
            self._load_items()
