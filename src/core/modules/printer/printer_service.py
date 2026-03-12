# modules/printer/printer_service.py
# Python 3.10 uyğun
"""Çek çap xidməti — ESC/POS + PDF + Ekran çeki."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.core.database.models import Payment, Order


# ── SABİTLƏR ──────────────────────────────────────────────────────────────────
RECEIPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets", "receipts"
)
os.makedirs(RECEIPT_DIR, exist_ok=True)

BUSINESS_NAME    = "Ramo Pub & TeaHouse"
BUSINESS_ADDRESS = "Bakı, Azərbaycan"
BUSINESS_PHONE   = "+994 12 000 00 00"
BUSINESS_FOOTER  = "Gəldiniz üçün təşəkkür edirik! 🍺"
RECEIPT_WIDTH    = 42   # simvol eni (termal printer)


# ── YARDIMCI FUNKSİYALAR ──────────────────────────────────────────────────────

def _center(text: str, width: int = RECEIPT_WIDTH) -> str:
    return text.center(width)


def _line(char: str = "-", width: int = RECEIPT_WIDTH) -> str:
    return char * width


def _lr(left: str, right: str, width: int = RECEIPT_WIDTH) -> str:
    gap = width - len(left) - len(right)
    return left + " " * max(1, gap) + right


# ── ÇEK MƏTNİ GENERATORU ─────────────────────────────────────────────────────

def build_receipt_text(payment: Payment, order: Order) -> str:
    """
    Termal printer formatında çek mətni yarat.
    ASCII-uyğun, hər sətir RECEIPT_WIDTH simvol.
    """
    lines: List[str] = []

    # Başlıq
    lines.append(_line("="))
    lines.append(_center(BUSINESS_NAME))
    lines.append(_center(BUSINESS_ADDRESS))
    lines.append(_center(BUSINESS_PHONE))
    lines.append(_line("="))

    # Çek nömrəsi & tarix
    now = datetime.now()
    lines.append(_lr(f"Çek: #{payment.id}", now.strftime("%d.%m.%Y %H:%M")))

    table_name = order.table.name if order.table else "—"
    waiter_name = order.waiter.full_name if order.waiter else "—"
    lines.append(_lr(f"Masa: {table_name}", f"Ofis.: {waiter_name[:12]}"))
    lines.append(_line())

    # Sifariş qələmləri
    lines.append(_lr("Məhsul", "Qiym.  Cəm"))
    lines.append(_line("-"))

    from src.core.database.models import OrderStatus as OS
    for oi in order.items:
        if oi.status == OS.cancelled:
            continue
        name = (oi.menu_item.name if oi.menu_item else "?")[:22]
        price_str = f"{oi.unit_price:.2f}"
        sub_str   = f"{oi.subtotal:.2f} AZN"
        lines.append(name)
        lines.append(_lr(f"  x{oi.quantity}", f"{price_str}  {sub_str}"))

    lines.append(_line())

    # Cəmlər
    lines.append(_lr("Ara cəm:", f"{order.subtotal:.2f} AZN"))
    if payment.discount_amount and payment.discount_amount > 0:
        lines.append(_lr("Endirim:", f"-{payment.discount_amount:.2f} AZN"))
    lines.append(_line("-"))
    lines.append(_lr("CƏMİ:", f"{payment.final_amount:.2f} AZN"))

    method_map = {"cash": "Nağd", "card": "Kart", "online": "Online"}
    method_str = method_map.get(payment.method.value, "?")
    lines.append(_lr("Ödəniş üsulu:", method_str))
    lines.append(_line("="))

    # Alt
    lines.append(_center(BUSINESS_FOOTER))
    lines.append(_center("www.ramopub.az"))
    lines.append("")
    lines.append("")

    return "\n".join(lines)


# ── PRİNTER SERVİSİ ───────────────────────────────────────────────────────────

class PrinterService:

    def __init__(self):
        self._printer_available = False
        self._pdf_available     = self._check_pdf()

    def _check_pdf(self) -> bool:
        try:
            import reportlab  # noqa
            return True
        except ImportError:
            return False

    # ── PDF çek ───────────────────────────────────────────────────────────────

    def print_to_pdf(
        self, payment: Payment, order: Order
    ) -> tuple[bool, str]:
        """PDF çek yarat, faylı qaytar."""
        if not self._pdf_available:
            return False, "reportlab quraşdırılmayıb. Quraşdırmaq: pip install reportlab"

        try:
            from reportlab.lib.pagesizes import A7, portrait
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
            from reportlab.lib import colors

            filename = os.path.join(
                RECEIPT_DIR,
                f"receipt_{payment.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            )

            doc = SimpleDocTemplate(
                filename,
                pagesize=portrait((80*mm, 200*mm)),
                rightMargin=4*mm,
                leftMargin=4*mm,
                topMargin=4*mm,
                bottomMargin=4*mm,
            )

            mono = ParagraphStyle(
                "mono",
                fontName="Courier",
                fontSize=8,
                leading=11,
                textColor=colors.black,
            )
            bold_mono = ParagraphStyle(
                "bold_mono",
                fontName="Courier-Bold",
                fontSize=9,
                leading=12,
                textColor=colors.black,
            )
            center_mono = ParagraphStyle(
                "center_mono",
                fontName="Courier-Bold",
                fontSize=9,
                leading=12,
                alignment=1,
                textColor=colors.black,
            )

            story = []
            story.append(Paragraph(BUSINESS_NAME, center_mono))
            story.append(Paragraph(BUSINESS_ADDRESS, center_mono))
            story.append(Paragraph(BUSINESS_PHONE, center_mono))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black))

            now = datetime.now()
            story.append(Paragraph(
                f"Çek: #{payment.id}   {now.strftime('%d.%m.%Y %H:%M')}",
                mono
            ))
            table_name  = order.table.name if order.table else "—"
            waiter_name = order.waiter.full_name if order.waiter else "—"
            story.append(Paragraph(f"Masa: {table_name}", mono))
            story.append(Paragraph(f"Ofisiant: {waiter_name}", mono))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))

            from src.core.database.models import OrderStatus as OS
            for oi in order.items:
                if oi.status == OS.cancelled:
                    continue
                name = oi.menu_item.name if oi.menu_item else "?"
                story.append(Paragraph(name, mono))
                story.append(Paragraph(
                    f"  x{oi.quantity}  @{oi.unit_price:.2f}  = {oi.subtotal:.2f} AZN",
                    mono
                ))

            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(Paragraph(f"Ara cəm:  {order.subtotal:.2f} AZN", mono))
            if payment.discount_amount and payment.discount_amount > 0:
                story.append(Paragraph(
                    f"Endirim:  -{payment.discount_amount:.2f} AZN", mono
                ))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
            story.append(Paragraph(f"CƏMİ:  {payment.final_amount:.2f} AZN", bold_mono))

            method_map = {"cash": "Nağd", "card": "Kart", "online": "Online"}
            story.append(Paragraph(
                f"Ödəniş: {method_map.get(payment.method.value, '?')}", mono
            ))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
            story.append(Paragraph(BUSINESS_FOOTER, center_mono))

            doc.build(story)
            return True, filename

        except Exception as exc:
            return False, f"PDF xətası: {exc}"

    # ── ESC/POS Printer ───────────────────────────────────────────────────────

    def print_escpos(
        self,
        payment: Payment,
        order: Order,
        printer_path: str = "/dev/usb/lp0",
    ) -> tuple[bool, str]:
        """
        ESC/POS termal printer-ə göndər.
        Linux: /dev/usb/lp0
        Windows: COM3 veya USB port
        """
        try:
            from escpos.printer import Usb, Serial, File
            text = build_receipt_text(payment, order)
            # Sadə fayl yolu ilə göndər (Linux USB printer)
            with open(printer_path, "wb") as f:
                f.write(text.encode("utf-8", errors="replace"))
                f.write(b"\x1d\x56\x00")   # ESC/POS kəsmə əmri
            return True, "Çek printerə göndərildi."
        except ImportError:
            return False, "python-escpos quraşdırılmayıb."
        except Exception as exc:
            return False, f"Printer xətası: {exc}"

    # ── Mətni fayla yaz ───────────────────────────────────────────────────────

    def save_receipt_text(
        self, payment: Payment, order: Order
    ) -> tuple[bool, str]:
        """Çek mətnini .txt faylı kimi saxla."""
        try:
            filename = os.path.join(
                RECEIPT_DIR,
                f"receipt_{payment.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            text = build_receipt_text(payment, order)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            return True, filename
        except Exception as exc:
            return False, str(exc)

    # ── Əsas çap metodu ───────────────────────────────────────────────────────

    def print_receipt(
        self,
        payment: Payment,
        order: Order,
        method: str = "pdf",    # "pdf" | "escpos" | "text"
        printer_path: str = "/dev/usb/lp0",
    ) -> tuple[bool, str]:
        if method == "pdf":
            return self.print_to_pdf(payment, order)
        elif method == "escpos":
            return self.print_escpos(payment, order, printer_path)
        else:
            return self.save_receipt_text(payment, order)

    def get_receipt_text(self, payment: Payment, order: Order) -> str:
        """Çek mətnini qaytarır (ekranda göstərmək üçün)."""
        return build_receipt_text(payment, order)


printer_service = PrinterService()
