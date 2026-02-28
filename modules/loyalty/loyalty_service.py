# modules/loyalty/loyalty_service.py
# Python 3.10 uyğun — Optional/Union istifadə edilir
"""Loyallıq & Müştəri İdarəsi xidmət modulu."""

from __future__ import annotations

import typing
from datetime import date, datetime
from typing import List, Optional, Tuple, Dict

from sqlalchemy.orm import Session
from database.models import Customer, Discount, Order, OrderStatus


# ── SABİTLƏR ──────────────────────────────────────────────────────────────────
POINTS_PER_MANAT:    int   = 1      # 1 ₼ = 1 xal
MANAT_PER_100_POINTS: float = 1.0  # 100 xal = 1 ₼ endirim
MIN_REDEEM:          int   = 100   # minimum xal istifadəsi

# Müştəri səviyyələri
TIERS = {
    "bronze": {"min": 0,     "max": 499,   "label": "Bürünc",  "discount_pct": 0,   "icon": "🥉"},
    "silver": {"min": 500,   "max": 1499,  "label": "Gümüş",   "discount_pct": 3,   "icon": "🥈"},
    "gold":   {"min": 1500,  "max": 4999,  "label": "Qızıl",   "discount_pct": 5,   "icon": "🥇"},
    "vip":    {"min": 5000,  "max": 999999, "label": "VIP",     "discount_pct": 10,  "icon": "💎"},
}


def get_tier(points: int) -> Dict[str, object]:
    """Xal sayına görə müştəri səviyyəsini qaytar."""
    for tier_data in reversed(list(TIERS.values())):
        if points >= tier_data["min"]:
            return tier_data
    return TIERS["bronze"]


class LoyaltyService:

    # ── MÜŞTƏRİ CRUD ──────────────────────────────────────────────────────────

    def get_all_customers(
        self, db: Session, search: str = ""
    ) -> List[Customer]:
        q = db.query(Customer)
        if search:
            q = q.filter(
                (Customer.full_name.ilike(f"%{search}%")) |
                (Customer.phone.ilike(f"%{search}%"))
            )
        return q.order_by(Customer.full_name).all()

    def get_customer(
        self, db: Session, customer_id: int
    ) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_phone(
        self, db: Session, phone: str
    ) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.phone == phone).first()

    def create_customer(
        self,
        db: Session,
        full_name: str,
        phone: str,
        email: str = "",
        birthday: Optional[date] = None,
    ) -> Tuple[bool, object]:
        existing = self.get_by_phone(db, phone)
        if existing:
            return False, f"Bu telefon nömrəsi artıq qeydiyyatlıdır: {existing.full_name}"
        customer = Customer(
            full_name=full_name,
            phone=phone,
            email=email,
            birthday=birthday,
            points=0,
            total_spent=0.0,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return True, customer

    def update_customer(
        self, db: Session, customer_id: int, **kwargs
    ) -> Tuple[bool, object]:
        customer = self.get_customer(db, customer_id)
        if not customer:
            return False, "Müştəri tapılmadı."
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        db.commit()
        return True, customer

    def delete_customer(
        self, db: Session, customer_id: int
    ) -> Tuple[bool, str]:
        customer = self.get_customer(db, customer_id)
        if not customer:
            return False, "Tapılmadı."
        db.delete(customer)
        db.commit()
        return True, "Müştəri silindi."

    # ── XALLAR ────────────────────────────────────────────────────────────────

    def add_points(
        self, db: Session, customer_id: int, amount_paid: float
    ) -> Tuple[bool, int]:
        """Ödəniş məbləğinə görə xal əlavə et. (1 ₼ = 1 xal)"""
        customer = self.get_customer(db, customer_id)
        if not customer:
            return False, 0
        points = int(amount_paid * POINTS_PER_MANAT)
        customer.points += points
        customer.total_spent += amount_paid
        db.commit()
        return True, points

    def redeem_points(
        self, db: Session, customer_id: int, points_to_use: int
    ) -> Tuple[bool, object]:
        """Xalları endirim kimi istifadə et."""
        if points_to_use < MIN_REDEEM:
            return False, f"Minimum {MIN_REDEEM} xal istifadə edilə bilər."
        customer = self.get_customer(db, customer_id)
        if not customer:
            return False, "Müştəri tapılmadı."
        if customer.points < points_to_use:
            return False, f"Kifayət qədər xal yoxdur. Mövcud: {customer.points}"
        discount_value = (points_to_use / 100) * MANAT_PER_100_POINTS
        customer.points -= points_to_use
        db.commit()
        return True, discount_value

    def adjust_points(
        self, db: Session, customer_id: int, delta: int, reason: str = ""
    ) -> Tuple[bool, str]:
        """Xalları əl ilə artır / azalt (admin funksiyası)."""
        customer = self.get_customer(db, customer_id)
        if not customer:
            return False, "Tapılmadı."
        new_total = customer.points + delta
        if new_total < 0:
            return False, "Xal mənfi ola bilməz."
        customer.points = new_total
        db.commit()
        return True, f"Xal balansı: {new_total}"

    # ── ENDİRİM KUPONLARI ─────────────────────────────────────────────────────

    def get_all_discounts(
        self, db: Session, active_only: bool = False
    ) -> List[Discount]:
        q = db.query(Discount)
        if active_only:
            q = q.filter(Discount.is_active == True)
        return q.order_by(Discount.created_at.desc()).all()

    def get_discount_by_code(
        self, db: Session, code: str
    ) -> Optional[Discount]:
        return db.query(Discount).filter(
            Discount.code == code.upper()
        ).first()

    def create_discount(
        self,
        db: Session,
        code: str,
        description: str,
        disc_type: str,        # "percent" | "fixed"
        value: float,
        min_order: float = 0.0,
        usage_limit: int = 0,
        valid_from: Optional[date] = None,
        valid_until: Optional[date] = None,
    ) -> Tuple[bool, object]:
        existing = self.get_discount_by_code(db, code)
        if existing:
            return False, f"'{code.upper()}' kodu artıq mövcuddur."
        disc = Discount(
            code=code.upper(),
            description=description,
            type=disc_type,
            value=value,
            min_order=min_order,
            usage_limit=usage_limit,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        db.add(disc)
        db.commit()
        db.refresh(disc)
        return True, disc

    def update_discount(
        self, db: Session, disc_id: int, **kwargs
    ) -> Tuple[bool, object]:
        disc = db.query(Discount).filter(Discount.id == disc_id).first()
        if not disc:
            return False, "Tapılmadı."
        for key, value in kwargs.items():
            if hasattr(disc, key):
                setattr(disc, key, value)
        db.commit()
        return True, disc

    def toggle_discount(
        self, db: Session, disc_id: int
    ) -> Tuple[bool, object]:
        disc = db.query(Discount).filter(Discount.id == disc_id).first()
        if not disc:
            return False, "Tapılmadı."
        disc.is_active = not disc.is_active
        db.commit()
        return True, disc

    def delete_discount(
        self, db: Session, disc_id: int
    ) -> Tuple[bool, str]:
        disc = db.query(Discount).filter(Discount.id == disc_id).first()
        if not disc:
            return False, "Tapılmadı."
        db.delete(disc)
        db.commit()
        return True, "Endirim silindi."

    # ── STATİSTİKA ────────────────────────────────────────────────────────────

    def get_customer_stats(
        self, db: Session, customer_id: int
    ) -> Dict[str, object]:
        customer = self.get_customer(db, customer_id)
        if not customer:
            return {}
        tier = get_tier(customer.points)
        orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.status == OrderStatus.paid,
        ).all()
        return {
            "customer":       customer,
            "tier":           tier,
            "total_orders":   len(orders),
            "total_spent":    customer.total_spent,
            "points":         customer.points,
            "redeem_value":   (customer.points / 100) * MANAT_PER_100_POINTS,
            "next_tier_pts":  self._next_tier_points(customer.points),
        }

    def _next_tier_points(self, points: int) -> int:
        for tier_data in TIERS.values():
            if points < tier_data["min"]:
                return tier_data["min"] - points
        return 0

    def get_summary(self, db: Session) -> Dict[str, object]:
        customers = db.query(Customer).all()
        return {
            "total":        len(customers),
            "total_points": sum(c.points for c in customers),
            "total_spent":  sum(c.total_spent for c in customers),
            "vip_count":    sum(1 for c in customers if c.points >= 5000),
        }

    def seed_defaults(self, db: Session) -> None:
        """Nümunə endirim kodları yarat."""
        if db.query(Discount).count() > 0:
            return
        samples = [
            ("WELCOME10", "Xoş gəldin endirimi",  "percent", 10,  0,    1,    None, None),
            ("SUMMER20",  "Yay kampaniyası",       "percent", 20,  20,   100,  None, None),
            ("VIP50",     "VIP müştəri endirimi",  "fixed",   5,   30,   0,    None, None),
            ("BIRTHDAY",  "Ad günü endirimi",      "percent", 15,  0,    0,    None, None),
        ]
        for code, desc, dtype, val, min_ord, limit, vf, vu in samples:
            db.add(Discount(
                code=code, description=desc, type=dtype,
                value=val, min_order=min_ord, usage_limit=limit,
                valid_from=vf, valid_until=vu,
            ))
        db.commit()


loyalty_service = LoyaltyService()
