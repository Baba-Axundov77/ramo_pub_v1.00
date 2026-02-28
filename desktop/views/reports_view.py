# desktop/views/reports_view.py — Hesabat & Qrafik UI
from __future__ import annotations

from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QDateEdit, QSpinBox, QComboBox,
    QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

# matplotlib PyQt6 backend
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Tema rəngləri
BG     = "#0D0D0D"
PANEL  = "#1C1C2E"
ACCENT = "#E8A045"
GREEN  = "#2ECC71"
RED    = "#E74C3C"
BLUE   = "#3498DB"
PURPLE = "#9B59B6"
COLORS = [ACCENT, GREEN, BLUE, RED, PURPLE, "#1ABC9C", "#F39C12", "#E91E63"]

plt.rcParams.update({
    "figure.facecolor": PANEL,
    "axes.facecolor":   PANEL,
    "axes.edgecolor":   "#3A3A5A",
    "axes.labelcolor":  "#B0A899",
    "xtick.color":      "#8080A0",
    "ytick.color":      "#8080A0",
    "text.color":       "#F0EAD6",
    "grid.color":       "#2E2E4E",
    "grid.linewidth":   0.5,
    "font.family":      "Arial",
    "font.size":        12,
})


class ChartWidget(FigureCanvas):
    """Matplotlib figuru PyQt6 içinə yerləşdirir."""

    def __init__(self, width: int = 5, height: int = 3.5, dpi: int = 90):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.fig.patch.set_facecolor(PANEL)

    def clear(self):
        self.fig.clear()
        self.draw()

    def get_ax(self):
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(PANEL)
        return ax


class StatCard(QFrame):
    """Kiçik statistika kartı."""
    def __init__(self, icon: str, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet(f"""
            StatCard {{
                background: #1C1C2E;
                border: 1px solid {color}50;
                border-left: 4px solid {color};
                border-radius: 12px;
            }}
        """)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12); v.setSpacing(2)
        row = QHBoxLayout()
        ico = QLabel(icon); ico.setFont(QFont("Segoe UI Emoji", 20))
        row.addWidget(ico)
        ttl = QLabel(title); ttl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")
        row.addWidget(ttl); row.addStretch()
        v.addLayout(row)
        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(QFont("Georgia", 18, QFont.Weight.Bold))
        self.value_lbl.setStyleSheet(f"color:{color};")
        v.addWidget(self.value_lbl)

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class ReportsView(QWidget):

    def __init__(self, db, report_service, parent=None):
        super().__init__(parent)
        self.db  = db
        self.svc = report_service
        self._build_ui()
        self._load_daily()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0D0D0D; }
            QTabBar::tab { background: #141420; color: #8080A0;
                padding: 10px 20px; border: none; font-size: 12px; }
            QTabBar::tab:selected { background: #1C1C2E; color: #E8A045;
                border-bottom: 2px solid #E8A045; font-weight: bold; }
        """)

        tabs.addTab(self._build_daily_tab(),   "📅  Günlük")
        tabs.addTab(self._build_monthly_tab(), "📆  Aylıq")
        tabs.addTab(self._build_yearly_tab(),  "📊  İllik")
        tabs.addTab(self._build_items_tab(),   "🍽️  Top Məhsullar")
        tabs.currentChanged.connect(self._on_tab_change)
        root.addWidget(tabs)
        self.tabs = tabs

    # ── Günlük Tab ────────────────────────────────────────────────────────────

    def _build_daily_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14); v.setSpacing(14)

        # Tarix seçici
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("📅  Tarix:"))
        self.daily_date = QDateEdit()
        self.daily_date.setCalendarPopup(True)
        self.daily_date.setDate(QDate.currentDate())
        self.daily_date.setFixedHeight(36)
        ctrl.addWidget(self.daily_date)
        load_btn = QPushButton("🔄  Yüklə")
        load_btn.setFixedHeight(36); load_btn.setObjectName("secondaryBtn")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_daily)
        ctrl.addWidget(load_btn); ctrl.addStretch()
        v.addLayout(ctrl)

        # Stat kartlar
        cards_row = QHBoxLayout(); cards_row.setSpacing(12)
        self.d_revenue  = StatCard("💰", "Gəlir",       "0.00 ₼", ACCENT)
        self.d_orders   = StatCard("📋", "Ödənilmiş",   "0",       GREEN)
        self.d_avg      = StatCard("🧾", "Orta Çek",    "0.00 ₼", BLUE)
        self.d_discount = StatCard("🏷️",  "Endirim",     "0.00 ₼", RED)
        for c in [self.d_revenue, self.d_orders, self.d_avg, self.d_discount]:
            cards_row.addWidget(c)
        v.addLayout(cards_row)

        # Qrafiklər
        charts_row = QHBoxLayout(); charts_row.setSpacing(14)

        # Saatlara görə sifariş
        hourly_frame = QFrame()
        hourly_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        hf_v = QVBoxLayout(hourly_frame)
        hf_v.setContentsMargins(14, 10, 14, 10)
        hf_lbl = QLabel("🕐  Saatlara Görə Sifariş")
        hf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        hf_v.addWidget(hf_lbl)
        self.hourly_chart = ChartWidget(6, 3)
        hf_v.addWidget(self.hourly_chart)
        charts_row.addWidget(hourly_frame, 3)

        # Ödəniş üsulları
        method_frame = QFrame()
        method_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        mf_v = QVBoxLayout(method_frame)
        mf_v.setContentsMargins(14, 10, 14, 10)
        mf_lbl = QLabel("💳  Ödəniş Üsulları")
        mf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        mf_v.addWidget(mf_lbl)
        self.method_chart = ChartWidget(3.5, 3)
        mf_v.addWidget(self.method_chart)
        charts_row.addWidget(method_frame, 2)

        v.addLayout(charts_row)
        return w

    # ── Aylıq Tab ─────────────────────────────────────────────────────────────

    def _build_monthly_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14); v.setSpacing(14)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("📅  İl:"))
        self.m_year = QSpinBox()
        self.m_year.setRange(2020, 2035)
        self.m_year.setValue(date.today().year)
        self.m_year.setFixedHeight(36)
        ctrl.addWidget(self.m_year)

        ctrl.addWidget(QLabel("  Ay:"))
        self.m_month = QComboBox()
        self.m_month.setFixedHeight(36)
        months = ["Yanvar","Fevral","Mart","Aprel","May","İyun",
                  "İyul","Avqust","Sentyabr","Oktyabr","Noyabr","Dekabr"]
        self.m_month.addItems(months)
        self.m_month.setCurrentIndex(date.today().month - 1)
        ctrl.addWidget(self.m_month)

        load_btn = QPushButton("🔄  Yüklə")
        load_btn.setFixedHeight(36); load_btn.setObjectName("secondaryBtn")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_monthly)
        ctrl.addWidget(load_btn); ctrl.addStretch()
        v.addLayout(ctrl)

        # Stat kartlar
        cards_row = QHBoxLayout(); cards_row.setSpacing(12)
        self.m_revenue = StatCard("💰", "Aylıq Gəlir", "0.00 ₼", ACCENT)
        self.m_orders  = StatCard("📋", "Ödənişlər",   "0",       GREEN)
        self.m_avg     = StatCard("🧾", "Orta Gündəlik","0.00 ₼", BLUE)
        for c in [self.m_revenue, self.m_orders, self.m_avg]:
            cards_row.addWidget(c)
        cards_row.addStretch()
        v.addLayout(cards_row)

        # Gündəlik gəlir qrafiki
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        cf_v = QVBoxLayout(chart_frame)
        cf_v.setContentsMargins(14, 10, 14, 10)
        cf_lbl = QLabel("📈  Gündəlik Gəlir")
        cf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        cf_v.addWidget(cf_lbl)
        self.monthly_chart = ChartWidget(10, 3.5)
        cf_v.addWidget(self.monthly_chart)
        v.addWidget(chart_frame)

        # Kateqoriya bölünməsi
        cat_frame = QFrame()
        cat_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        cat_v = QVBoxLayout(cat_frame)
        cat_v.setContentsMargins(14, 10, 14, 10)
        cat_lbl = QLabel("🍽️  Kateqoriyaya görə gəlir")
        cat_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        cat_v.addWidget(cat_lbl)
        self.cat_chart = ChartWidget(10, 3)
        cat_v.addWidget(self.cat_chart)
        v.addWidget(cat_frame)
        return w

    # ── İllik Tab ─────────────────────────────────────────────────────────────

    def _build_yearly_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14); v.setSpacing(14)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("📅  İl:"))
        self.y_year = QSpinBox()
        self.y_year.setRange(2020, 2035)
        self.y_year.setValue(date.today().year)
        self.y_year.setFixedHeight(36)
        ctrl.addWidget(self.y_year)
        load_btn = QPushButton("🔄  Yüklə")
        load_btn.setFixedHeight(36); load_btn.setObjectName("secondaryBtn")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_yearly)
        ctrl.addWidget(load_btn); ctrl.addStretch()
        v.addLayout(ctrl)

        cards_row = QHBoxLayout(); cards_row.setSpacing(12)
        self.y_revenue = StatCard("💰", "İllik Gəlir",   "0.00 ₼", ACCENT)
        self.y_orders  = StatCard("📋", "Ödənişlər",     "0",       GREEN)
        self.y_avg_m   = StatCard("📆", "Orta Aylıq",    "0.00 ₼", BLUE)
        self.y_best    = StatCard("🏆", "Ən Yaxşı Ay",   "—",       PURPLE)
        for c in [self.y_revenue, self.y_orders, self.y_avg_m, self.y_best]:
            cards_row.addWidget(c)
        v.addLayout(cards_row)

        chart_frame = QFrame()
        chart_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        cf_v = QVBoxLayout(chart_frame)
        cf_v.setContentsMargins(14, 10, 14, 10)
        cf_lbl = QLabel("📊  Aylıq Gəlir Müqayisəsi")
        cf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        cf_v.addWidget(cf_lbl)
        self.yearly_chart = ChartWidget(10, 4)
        cf_v.addWidget(self.yearly_chart)
        v.addWidget(chart_frame)
        return w

    # ── Top Məhsullar Tab ─────────────────────────────────────────────────────

    def _build_items_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w)
        v.setContentsMargins(20, 14, 20, 14); v.setSpacing(14)

        ctrl = QHBoxLayout()
        self.items_period = QComboBox()
        self.items_period.setFixedHeight(36)
        self.items_period.addItems(["Bu gün", "Bu həftə", "Bu ay", "Hamısı"])
        ctrl.addWidget(QLabel("Dövr:")); ctrl.addWidget(self.items_period)
        load_btn = QPushButton("🔄  Yüklə")
        load_btn.setFixedHeight(36); load_btn.setObjectName("secondaryBtn")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_items)
        ctrl.addWidget(load_btn); ctrl.addStretch()
        v.addLayout(ctrl)

        charts_row = QHBoxLayout(); charts_row.setSpacing(14)

        top_frame = QFrame()
        top_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        tf_v = QVBoxLayout(top_frame)
        tf_v.setContentsMargins(14, 10, 14, 10)
        tf_lbl = QLabel("🏆  Ən Çox Satılan 10 Məhsul")
        tf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        tf_v.addWidget(tf_lbl)
        self.top_qty_chart = ChartWidget(6, 4.5)
        tf_v.addWidget(self.top_qty_chart)
        charts_row.addWidget(top_frame, 3)

        rev_frame = QFrame()
        rev_frame.setStyleSheet("background:#1C1C2E; border-radius:12px;")
        rf_v = QVBoxLayout(rev_frame)
        rf_v.setContentsMargins(14, 10, 14, 10)
        rf_lbl = QLabel("💰  Ən Çox Gəlir Gətirən")
        rf_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold; font-size:12px;")
        rf_v.addWidget(rf_lbl)
        self.top_rev_chart = ChartWidget(4, 4.5)
        rf_v.addWidget(self.top_rev_chart)
        charts_row.addWidget(rev_frame, 2)

        v.addLayout(charts_row)
        return w

    # ── Məlumat Yüklə ────────────────────────────────────────────────────────

    def _on_tab_change(self, idx: int):
        if idx == 0:   self._load_daily()
        elif idx == 1: self._load_monthly()
        elif idx == 2: self._load_yearly()
        elif idx == 3: self._load_items()

    def _load_daily(self):
        qd = self.daily_date.date()
        target = date(qd.year(), qd.month(), qd.day())
        data   = self.svc.daily_summary(self.db, target)

        self.d_revenue.set_value(f"{data['revenue']:.2f} ₼")
        self.d_orders.set_value(str(data['orders_paid']))
        self.d_avg.set_value(f"{data['avg_check']:.2f} ₼")
        self.d_discount.set_value(f"{data['discounts']:.2f} ₼")

        # Saatlıq qrafik
        hourly = self.svc.hourly_heatmap(self.db, target)
        self.hourly_chart.fig.clear()
        ax = self.hourly_chart.fig.add_subplot(111)
        ax.set_facecolor(PANEL)
        bars = ax.bar(hourly["hours"], hourly["counts"], color=ACCENT, alpha=0.85, width=0.7)
        ax.set_xlabel("Saat"); ax.set_ylabel("Sifariş sayı")
        ax.grid(axis="y", alpha=0.3)
        ax.set_xlim(-0.5, 23.5)
        for bar, cnt in zip(bars, hourly["counts"]):
            if cnt > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        str(cnt), ha="center", va="bottom", fontsize=7, color="#F0EAD6")
        self.hourly_chart.draw()

        # Ödəniş üsulları pie
        method_labels = {"cash": "Nağd", "card": "Kart", "online": "Online"}
        by_method = data["by_method"]
        filtered = {method_labels.get(k, k): v for k, v in by_method.items() if v > 0}

        self.method_chart.fig.clear()
        ax2 = self.method_chart.fig.add_subplot(111)
        ax2.set_facecolor(PANEL)
        if filtered:
            wedges, texts, autotexts = ax2.pie(
                filtered.values(), labels=filtered.keys(),
                colors=[GREEN, BLUE, PURPLE],
                autopct="%1.0f%%", startangle=140,
                wedgeprops={"linewidth": 2, "edgecolor": PANEL}
            )
            for at in autotexts:
                at.set_color("#F0EAD6"); at.set_fontsize(9)
        else:
            ax2.text(0, 0, "Məlumat yoxdur", ha="center", va="center",
                     color="#6A6A8A", fontsize=11)
        self.method_chart.draw()

    def _load_monthly(self):
        year  = self.m_year.value()
        month = self.m_month.currentIndex() + 1
        data  = self.svc.monthly_summary(self.db, year, month)
        cats  = self.svc.category_breakdown(self.db,
                    since_date=date(year, month, 1))

        self.m_revenue.set_value(f"{data['revenue']:.2f} ₼")
        self.m_orders.set_value(str(data['count']))
        avg = data["revenue"] / max(1, len([v for v in data["values"] if v > 0]))
        self.m_avg.set_value(f"{avg:.2f} ₼")

        # Gündəlik gəlir bar
        self.monthly_chart.fig.clear()
        ax = self.monthly_chart.fig.add_subplot(111)
        ax.set_facecolor(PANEL)
        ax.bar(data["days"], data["values"], color=ACCENT, alpha=0.85, width=0.7)
        ax.plot(data["days"], data["values"], color=GREEN, linewidth=1.5, alpha=0.7)
        ax.set_xlabel("Gün"); ax.set_ylabel("Gəlir (₼)")
        ax.grid(axis="y", alpha=0.3)
        self.monthly_chart.draw()

        # Kateqoriya bar
        self.cat_chart.fig.clear()
        ax2 = self.cat_chart.fig.add_subplot(111)
        ax2.set_facecolor(PANEL)
        if cats:
            names  = [c["name"] for c in cats]
            values = [c["total"] for c in cats]
            y_pos  = range(len(names))
            bars = ax2.barh(list(y_pos), values, color=COLORS[:len(names)], alpha=0.85)
            ax2.set_yticks(list(y_pos)); ax2.set_yticklabels(names, fontsize=8)
            ax2.set_xlabel("Gəlir (₼)")
            ax2.grid(axis="x", alpha=0.3)
            for bar, val in zip(bars, values):
                ax2.text(val + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                         f"{val:.1f} ₼", va="center", fontsize=8, color="#F0EAD6")
        self.cat_chart.draw()

    def _load_yearly(self):
        year = self.y_year.value()
        data = self.svc.yearly_summary(self.db, year)

        self.y_revenue.set_value(f"{data['total_revenue']:.2f} ₼")
        self.y_orders.set_value(str(data['total_orders']))
        avg = data['total_revenue'] / 12
        self.y_avg_m.set_value(f"{avg:.2f} ₼")
        months = ["Yan","Fev","Mar","Apr","May","İyn",
                  "İyl","Avq","Sen","Okt","Noy","Dek"]
        max_val = max(data["monthly_revenue"]) if any(data["monthly_revenue"]) else 0
        if max_val > 0:
            best_idx = data["monthly_revenue"].index(max_val)
            self.y_best.set_value(months[best_idx])
        else:
            self.y_best.set_value("—")

        self.yearly_chart.fig.clear()
        ax = self.yearly_chart.fig.add_subplot(111)
        ax.set_facecolor(PANEL)
        x = range(12)
        ax.bar(list(x), data["monthly_revenue"], color=ACCENT, alpha=0.85, width=0.6, label="Gəlir")
        ax2_twin = ax.twinx()
        ax2_twin.plot(list(x), data["monthly_orders"], color=GREEN,
                      linewidth=2, marker="o", markersize=5, label="Sifariş")
        ax2_twin.set_ylabel("Sifariş sayı", color=GREEN)
        ax2_twin.tick_params(axis="y", colors=GREEN)
        ax.set_xticks(list(x)); ax.set_xticklabels(months, fontsize=8)
        ax.set_ylabel("Gəlir (₼)")
        ax.grid(axis="y", alpha=0.3)
        self.yearly_chart.draw()

    def _load_items(self):
        period_idx = self.items_period.currentIndex()
        today = date.today()
        if period_idx == 0:
            since = today
        elif period_idx == 1:
            from datetime import timedelta
            since = today - timedelta(days=7)
        elif period_idx == 2:
            since = date(today.year, today.month, 1)
        else:
            since = None

        items = self.svc.top_items(self.db, limit=10, since_date=since)

        self.top_qty_chart.fig.clear()
        ax = self.top_qty_chart.fig.add_subplot(111)
        ax.set_facecolor(PANEL)
        if items:
            names = [i["name"][:18] for i in items]
            qtys  = [i["qty"]      for i in items]
            y = range(len(names))
            ax.barh(list(y), qtys, color=COLORS[:len(names)], alpha=0.85)
            ax.set_yticks(list(y)); ax.set_yticklabels(names, fontsize=8)
            ax.set_xlabel("Satış miqdarı")
            ax.grid(axis="x", alpha=0.3)
            for i, (val, yp) in enumerate(zip(qtys, y)):
                ax.text(val + 0.1, yp, str(val), va="center", fontsize=8, color="#F0EAD6")
        else:
            ax.text(0.5, 0.5, "Məlumat yoxdur", ha="center", va="center",
                    transform=ax.transAxes, color="#6A6A8A", fontsize=12)
        self.top_qty_chart.draw()

        # Gəlirə görə pie
        self.top_rev_chart.fig.clear()
        ax2 = self.top_rev_chart.fig.add_subplot(111)
        ax2.set_facecolor(PANEL)
        if items:
            names_short = [i["name"][:14] for i in items[:6]]
            revs        = [i["revenue"]   for i in items[:6]]
            wedges, texts, autotexts = ax2.pie(
                revs, labels=names_short,
                colors=COLORS[:len(revs)],
                autopct="%1.0f%%", startangle=90,
                wedgeprops={"linewidth": 2, "edgecolor": PANEL},
                textprops={"fontsize": 7}
            )
            for at in autotexts:
                at.set_color("#F0EAD6"); at.set_fontsize(8)
        else:
            ax2.text(0, 0, "Məlumat yoxdur", ha="center", va="center",
                     color="#6A6A8A", fontsize=11)
        self.top_rev_chart.draw()
