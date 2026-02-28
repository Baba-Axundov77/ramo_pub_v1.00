from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QFont


class SettingsView(QWidget):
    """Sadə tənzimləmə səhifəsi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("⚙️ Tənzimləmələr")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color:#E8A045;")
        root.addWidget(title)

        info = QFrame()
        info.setStyleSheet("background:#1C1C2E; border:1px solid #2E2E4E; border-radius:10px;")
        iv = QVBoxLayout(info)
        iv.addWidget(QLabel("• Tema dəyişimi yuxarı sağ düymə ilə idarə olunur."))
        iv.addWidget(QLabel("• Kassa modulu ayrıca səhifədə aktivdir."))
        iv.addWidget(QLabel("• Verilənlər bazası bağlantısı .env / DATABASE_URL ilə tənzimlənir."))
        root.addWidget(info)
        root.addStretch()
