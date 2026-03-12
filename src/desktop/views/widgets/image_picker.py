# desktop/views/widgets/image_picker.py
# Python 3.11+ uyÄŸun â€” ÅŸÉ™kil seÃ§mÉ™ vÉ™ gÃ¶stÉ™rmÉ™ widgeti
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont


# â”€â”€ SabitlÉ™r â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ASSETS_DIR  = Path(__file__).parent.parent.parent.parent / "assets"
MENU_IMGS   = ASSETS_DIR / "menu_images"
TABLE_IMGS  = ASSETS_DIR / "table_images"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

for d in (MENU_IMGS, TABLE_IMGS):
    d.mkdir(parents=True, exist_ok=True)


def _copy_image(src: str, dest_dir: Path, prefix: str = "") -> str:
    """ÅÉ™kili dest_dir-É™ kopyala, nisbi yolu qaytar."""
    src_path = Path(src)
    if src_path.suffix.lower() not in ALLOWED_EXT:
        raise ValueError(f"DÉ™stÉ™klÉ™nmÉ™yÉ™n format: {src_path.suffix}")
    dest_name = f"{prefix}_{src_path.name}" if prefix else src_path.name
    dest_path = dest_dir / dest_name
    shutil.copy2(src_path, dest_path)
    return str(dest_path)


def _make_pixmap(
    image_path: Optional[str],
    width: int,
    height: int,
    placeholder_icon: str = "ğŸ–¼ï¸",
    placeholder_text: str = "ÅÉ™kil yoxdur",
) -> QPixmap:
    """
    ÅÉ™kil faylÄ±ndan QPixmap yarat.
    Fayl yoxdursa â€” placeholder icon Ã§É™k.
    """
    pix = QPixmap(width, height)
    pix.fill(Qt.GlobalColor.transparent)

    if image_path and Path(image_path).exists():
        loaded = QPixmap(image_path)
        if not loaded.isNull():
            scaled = loaded.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # MÉ™rkÉ™zdÉ™n kÉ™s
            x = (scaled.width()  - width)  // 2
            y = (scaled.height() - height) // 2
            pix = scaled.copy(x, y, width, height)
            return pix

    # Placeholder Ã§É™k
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillRect(pix.rect(), QColor("#1C1C2E"))
    painter.setPen(QColor("#4A4A6A"))
    painter.setFont(QFont("Segoe UI Emoji", max(12, width // 5)))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, placeholder_icon)
    painter.setFont(QFont("Segoe UI", max(8, width // 12)))
    painter.setPen(QColor("#6A6A8A"))
    from PyQt6.QtCore import QRect
    painter.drawText(
        QRect(0, height * 2 // 3, width, height // 3),
        Qt.AlignmentFlag.AlignCenter,
        placeholder_text,
    )
    painter.end()
    return pix


class RoundedImageLabel(QLabel):
    """
    Yuvarlaq kÃ¼nclÃ¼ ÅŸÉ™kil label.
    image_path: fayl yolu (None â†’ placeholder)
    """
    def __init__(
        self,
        image_path: Optional[str] = None,
        width: int  = 120,
        height: int = 90,
        radius: int = 12,
        placeholder_icon: str = "ğŸ–¼ï¸",
        placeholder_text: str = "ÅÉ™kil yoxdur",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._w     = width
        self._h     = height
        self._r     = radius
        self._ph_icon = placeholder_icon
        self._ph_text = placeholder_text
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_image(image_path)

    def set_image(self, image_path: Optional[str]) -> None:
        self._path = image_path
        pix = _make_pixmap(
            image_path, self._w, self._h,
            self._ph_icon, self._ph_text
        )
        # Yuvarlaq kÃ¼nclÉ™ri mask et
        rounded = QPixmap(self._w, self._h)
        rounded.fill(Qt.GlobalColor.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        from PyQt6.QtCore import QRectF
        path.addRoundedRect(QRectF(0, 0, self._w, self._h), self._r, self._r)
        p.setClipPath(path)
        p.drawPixmap(0, 0, pix)
        p.end()
        self.setPixmap(rounded)


class ImagePickerWidget(QWidget):
    """
    ÅÉ™kil seÃ§ / sil / gÃ¶stÉ™r widgeti.

    Siqnallar:
        image_changed(str)  â€” yeni ÅŸÉ™kil yolu (boÅŸ string = silindi)
    """
    image_changed = pyqtSignal(str)

    def __init__(
        self,
        dest_dir: Path,
        image_path: Optional[str] = None,
        prefix: str = "",
        preview_w: int = 220,
        preview_h: int = 160,
        placeholder_icon: str = "ğŸ“·",
        placeholder_text: str = "ÅÉ™kil seÃ§in",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._dest_dir = dest_dir
        self._prefix   = prefix
        self._current  = image_path

        self._preview_w = preview_w
        self._preview_h = preview_h
        self._ph_icon   = placeholder_icon
        self._ph_text   = placeholder_text

        self._build()
        self._refresh_preview()

    # â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Preview Ã§É™rÃ§ivÉ™si
        frame = QFrame()
        frame.setFixedSize(self._preview_w, self._preview_h)
        frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #3A3A5A;
                border-radius: 12px;
                background: #141420;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.preview = RoundedImageLabel(
            self._current,
            self._preview_w - 4,
            self._preview_h - 4,
            radius=10,
            placeholder_icon=self._ph_icon,
            placeholder_text=self._ph_text,
        )
        frame_layout.addWidget(self.preview)
        root.addWidget(frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # DÃ¼ymÉ™lÉ™r
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.select_btn = QPushButton("ğŸ“‚  ÅÉ™kil seÃ§")
        self.select_btn.setFixedHeight(32)
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background: #252535; color: #E8A045;
                border: 1px solid #E8A04560; border-radius: 8px;
                font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #E8A04520; border-color: #E8A045; }
        """)
        self.select_btn.clicked.connect(self._pick_file)
        btn_row.addWidget(self.select_btn)

        self.clear_btn = QPushButton("ğŸ—‘ Sil")
        self.clear_btn.setFixedSize(68, 32)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #2A1C1C; color: #E74C3C;
                border: 1px solid #E74C3C60; border-radius: 8px; font-size: 11px;
            }
            QPushButton:hover { background: #E74C3C20; border-color: #E74C3C; }
            QPushButton:disabled { opacity: 0.3; }
        """)
        self.clear_btn.clicked.connect(self._clear_image)
        btn_row.addWidget(self.clear_btn)

        root.addLayout(btn_row)

        # Fayl adÄ±
        self.file_label = QLabel("ÅÉ™kil seÃ§ilmÉ™yib")
        self.file_label.setStyleSheet("color: #6A6A8A; font-size: 10px;")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setWordWrap(True)
        root.addWidget(self.file_label)

    # â”€â”€ MÉ™ntiqi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "ÅÉ™kil seÃ§",
            str(Path.home()),
            "ÅÉ™kil fayllarÄ± (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if not path:
            return
        try:
            dest = _copy_image(path, self._dest_dir, self._prefix)
            self._current = dest
            self._refresh_preview()
            self.image_changed.emit(dest)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "XÉ™ta", f"ÅÉ™kil kopyalana bilmÉ™di:\n{e}")

    def _clear_image(self) -> None:
        self._current = None
        self._refresh_preview()
        self.image_changed.emit("")

    def _refresh_preview(self) -> None:
        self.preview.set_image(self._current)
        self.clear_btn.setEnabled(bool(self._current))
        if self._current:
            self.file_label.setText(Path(self._current).name)
            self.file_label.setStyleSheet("color: #8080A0; font-size: 10px;")
        else:
            self.file_label.setText("ÅÉ™kil seÃ§ilmÉ™yib")
            self.file_label.setStyleSheet("color: #6A6A8A; font-size: 10px;")

    # â”€â”€ Xarici API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_image_path(self) -> Optional[str]:
        return self._current

    def set_image_path(self, path: Optional[str]) -> None:
        self._current = path
        self._refresh_preview()
