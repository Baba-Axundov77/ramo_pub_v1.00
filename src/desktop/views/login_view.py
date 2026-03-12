# desktop/views/login_view.py — Professional Giriş Ekranı
import os
import sys
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QApplication,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush, QLinearGradient

logger = logging.getLogger(__name__)


class AnimatedButton(QPushButton):
    """Animasiyalı düymə."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class LoginView(QWidget):
    """
    Ramo Pub & TeaHouse — Giriş Ekranı
    Siqnallar:
        login_success(user_obj) — uğurlu giriş
        exit_app()              — çıxış
    """
    login_success = pyqtSignal(object)
    exit_app      = pyqtSignal()

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.login_attempts = 0
        self.max_attempts   = 5

        self.setObjectName("loginWidget")
        self._build_ui()
        self._connect_signals()

    # ── UI Qurulumu ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Tam ekran layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Mərkəz aligner
        center_h = QHBoxLayout()
        center_h.addStretch()

        # ── Login Kartı ──────────────────────────────────────────────────────
        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(400)
        self.card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # Kölgə effekti
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(0)

        # ── Logo & Başlıq ────────────────────────────────────────────────────
        logo_area = QVBoxLayout()
        logo_area.setSpacing(4)
        logo_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo emoji (real layihədə şəkil olacaq)
        logo_lbl = QLabel("🍺")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setFont(QFont("Segoe UI Emoji", 42))
        logo_area.addWidget(logo_lbl)

        title = QLabel("Ramo")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_area.addWidget(title)

        subtitle = QLabel("PUB & TEAHOUSE")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_area.addWidget(subtitle)

        card_layout.addLayout(logo_area)
        card_layout.addSpacing(32)

        # ── Form ─────────────────────────────────────────────────────────────
        form = QVBoxLayout()
        form.setSpacing(8)

        # İstifadəçi adı
        user_lbl = QLabel("İSTİFADƏÇİ ADI")
        user_lbl.setObjectName("loginLabel")
        form.addWidget(user_lbl)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("istifadəçi adını daxil edin")
        self.username_input.setFixedHeight(44)
        form.addWidget(self.username_input)

        form.addSpacing(12)

        # Şifrə
        pass_lbl = QLabel("ŞİFRƏ")
        pass_lbl.setObjectName("loginLabel")
        form.addWidget(pass_lbl)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("şifrəni daxil edin")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(44)
        pass_row.addWidget(self.password_input)

        self.show_pass_btn = QPushButton("👁")
        self.show_pass_btn.setObjectName("secondaryBtn")
        self.show_pass_btn.setFixedSize(44, 44)
        self.show_pass_btn.setCheckable(True)
        self.show_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Düzgün border-radius
        self.show_pass_btn.setStyleSheet("""
            QPushButton { border-radius: 0 8px 8px 0; padding: 0; font-size: 16px; }
        """)
        pass_row.addWidget(self.show_pass_btn)
        form.addLayout(pass_row)

        card_layout.addLayout(form)
        card_layout.addSpacing(6)

        # ── Xəta Mesajı ──────────────────────────────────────────────────────
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(20)

        # ── Giriş Düyməsi ────────────────────────────────────────────────────
        self.login_btn = AnimatedButton("  Daxil Ol  →")
        self.login_btn.setFixedHeight(48)
        self.login_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        card_layout.addWidget(self.login_btn)

        card_layout.addSpacing(16)

        # ── Alt Məlumat ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: #2E2E4E; margin: 0 20px;")
        divider.setFixedHeight(1)
        card_layout.addWidget(divider)
        card_layout.addSpacing(16)

        bottom = QHBoxLayout()
        version_lbl = QLabel("v1.0.0")
        version_lbl.setStyleSheet("color: #4A4A6A; font-size: 10px;")

        exit_btn = QPushButton("Çıxış")
        exit_btn.setObjectName("secondaryBtn")
        exit_btn.setFixedSize(70, 30)
        exit_btn.setFont(QFont("Segoe UI", 10))
        exit_btn.clicked.connect(self.exit_app.emit)

        bottom.addWidget(version_lbl)
        bottom.addStretch()
        bottom.addWidget(exit_btn)
        card_layout.addLayout(bottom)

        # ── Layout birləşdirmə ────────────────────────────────────────────────
        center_h.addWidget(self.card, 0, Qt.AlignmentFlag.AlignVCenter)
        center_h.addStretch()

        outer.addStretch()
        outer.addLayout(center_h)
        outer.addStretch()

        # Mərkəzə qoyulan copyright
        copy_lbl = QLabel("© 2024 Ramo Pub & TeaHouse")
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_lbl.setStyleSheet("color: #3A3A5A; font-size: 10px; padding: 10px;")
        outer.addWidget(copy_lbl)

    # ── Siqnallar ─────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.login_btn.clicked.connect(self._do_login)
        self.username_input.returnPressed.connect(self._do_login)
        self.password_input.returnPressed.connect(self._do_login)
        self.show_pass_btn.toggled.connect(self._toggle_password)

    # ── Giriş Məntiqi ─────────────────────────────────────────────────────────

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error("İstifadəçi adı və şifrə doldurulmalıdır.")
            return

        if self.login_attempts >= self.max_attempts:
            self._show_error("Çox sayda yanlış cəhd. Bir müddət gözləyin.")
            self.login_btn.setEnabled(False)
            QTimer.singleShot(30000, lambda: self.login_btn.setEnabled(True))
            return

        # Girişi yoxla
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Yoxlanılır...")
        QApplication.processEvents()

        login_response = self.api_client.login(username, password)
        success = login_response.get('success', False)
        result = login_response

        self.login_btn.setEnabled(True)
        self.login_btn.setText("  Daxil Ol  →")

        if success:
            self.login_attempts = 0
            self.error_label.hide()
            # API client returns dict with 'user' key
            user_data = result.get('user') if isinstance(result, dict) else result
            self.login_success.emit(user_data)
        else:
            self.login_attempts += 1
            remaining = self.max_attempts - self.login_attempts
            # API client returns dict with 'message' key
            msg = result.get('message') if isinstance(result, dict) else result
            if remaining <= 2:
                msg += f" ({remaining} cəhd qaldı)"
            self._show_error(msg)
            self._shake_card()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
        QTimer.singleShot(5000, self.error_label.hide)

    def _shake_card(self):
        """Kart silkələmə animasiyası."""
        from PyQt6.QtCore import QPoint
        pos = self.card.pos()
        anim = QPropertyAnimation(self.card, b"pos")
        anim.setDuration(300)
        anim.setKeyValueAt(0.0, pos)
        anim.setKeyValueAt(0.1, QPoint(pos.x() - 8, pos.y()))
        anim.setKeyValueAt(0.2, QPoint(pos.x() + 8, pos.y()))
        anim.setKeyValueAt(0.3, QPoint(pos.x() - 6, pos.y()))
        anim.setKeyValueAt(0.4, QPoint(pos.x() + 6, pos.y()))
        anim.setKeyValueAt(1.0, pos)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        anim.start()
        self._shake_anim = anim  # GC-dan qorumaq ucun

    def _toggle_password(self, checked: bool):
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pass_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pass_btn.setText("👁")

    def clear_fields(self):
        """Formu təmizlə."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self.username_input.setFocus()
