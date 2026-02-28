# modules/reports/report_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import (
    Payment, Order, OrderItem, MenuItem,
    MenuCategory, OrderStatus, PaymentMethod
)


class ReportService:

    def daily_summary(self, db: Session, target_date: date) -> Dict:
        start = datetime.combine(target_date, datetime.min.time())
        end   = datetime.combine(target_date, datetime.max.time())
        payments = db.query(Payment).filter(
            Payment.created_at >= start,
            Payment.created_at <= end,
        ).all()
        orders = db.query(Order).filter(
            Order.created_at >= start,
            Order.created_at <= end,
        ).all()
        revenue   = sum(p.final_amount for p in payments)
        discounts = sum(p.discount_amount for p in payments)
        by_method: Dict[str, float] = {}
        for pm in PaymentMethod:
            by_method[pm.value] = sum(
                p.final_amount for p in payments if p.method == pm
            )
        return {
            "date":         target_date,
            "revenue":      revenue,
            "discounts":    discounts,
            "orders_total": len(orders),
            "orders_paid":  len(payments),
            "avg_check":    revenue / len(payments) if payments else 0.0,
            "by_method":    by_method,
        }

    def monthly_summary(self, db: Session, year: int, month: int) -> Dict:
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        end   = datetime(year, month, last_day, 23, 59, 59)
        payments = db.query(Payment).filter(
            Payment.created_at >= start,
            Payment.created_at <= end,
        ).all()
        daily: Dict[int, float] = {}
        for p in payments:
            day = p.created_at.day
            daily[day] = daily.get(day, 0) + p.final_amount
        days   = list(range(1, last_day + 1))
        values = [daily.get(d, 0.0) for d in days]
        return {
            "year":    year,
            "month":   month,
            "revenue": sum(p.final_amount for p in payments),
            "count":   len(payments),
            "days":    days,
            "values":  values,
        }

    def top_items(self, db: Session, limit: int = 10,
                  since_date: Optional[date] = None) -> List[Dict]:
        q = (
            db.query(
                MenuItem.name,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.subtotal).label("total_revenue"),
            )
            .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status == OrderStatus.paid)
        )
        if since_date:
            q = q.filter(Order.created_at >= datetime.combine(since_date, datetime.min.time()))
        rows = q.group_by(MenuItem.name).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(limit).all()
        return [
            {"name": r.name, "qty": int(r.total_qty), "revenue": float(r.total_revenue)}
            for r in rows
        ]

    def category_breakdown(self, db: Session,
                            since_date: Optional[date] = None) -> List[Dict]:
        q = (
            db.query(
                MenuCategory.name,
                func.sum(OrderItem.subtotal).label("total"),
            )
            .join(MenuItem, MenuItem.category_id == MenuCategory.id)
            .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status == OrderStatus.paid)
        )
        if since_date:
            q = q.filter(Order.created_at >= datetime.combine(since_date, datetime.min.time()))
        rows = q.group_by(MenuCategory.name).order_by(
            func.sum(OrderItem.subtotal).desc()
        ).all()
        return [{"name": r.name, "total": float(r.total)} for r in rows]

    def yearly_summary(self, db: Session, year: int) -> Dict:
        monthly_revenue: List[float] = []
        monthly_orders:  List[int]   = []
        for month in range(1, 13):
            data = self.monthly_summary(db, year, month)
            monthly_revenue.append(data["revenue"])
            monthly_orders.append(data["count"])
        return {
            "year":            year,
            "monthly_revenue": monthly_revenue,
            "monthly_orders":  monthly_orders,
            "total_revenue":   sum(monthly_revenue),
            "total_orders":    sum(monthly_orders),
        }


    def completed_sales(self, db: Session, target_date: date, limit: int = 50) -> List[Dict]:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        rows = (
            db.query(Order, Payment)
            .join(Payment, Payment.order_id == Order.id)
            .filter(Payment.created_at >= start, Payment.created_at <= end)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )
        data: List[Dict] = []
        for order, payment in rows:
            data.append({
                "order_id": order.id,
                "table": order.table.number if order.table else None,
                "status": order.status.value,
                "items": len(order.items),
                "method": payment.method.value,
                "amount": float(payment.final_amount or 0),
                "paid_at": payment.created_at,
            })
        return data

    def hourly_heatmap(self, db: Session, target_date: date) -> Dict:
        start = datetime.combine(target_date, datetime.min.time())
        end   = datetime.combine(target_date, datetime.max.time())
        orders = db.query(Order).filter(
            Order.created_at >= start,
            Order.created_at <= end,
            Order.status     != OrderStatus.cancelled,
        ).all()
        hourly: Dict[int, int] = {h: 0 for h in range(24)}
        for o in orders:
            hourly[o.created_at.hour] += 1
        return {
            "hours":  list(range(24)),
            "counts": [hourly[h] for h in range(24)],
        }


report_service = ReportService()
