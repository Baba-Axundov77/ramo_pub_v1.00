# modules/reports/report_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, extract
from database.models import (
    Payment, Order, OrderItem, MenuItem,
    MenuCategory, OrderStatus, PaymentMethod
)


class ReportService:

    @staticmethod
    def _day_range(target_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        return start, end

    @staticmethod
    def _month_range(year: int, month: int) -> tuple[datetime, datetime, int]:
        from calendar import monthrange

        _, last_day = monthrange(year, month)
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return start, end, last_day

    @staticmethod
    def _method_totals(db: Session, start: datetime, end: datetime) -> Dict[str, float]:
        rows = (
            db.query(Payment.method, func.coalesce(func.sum(Payment.final_amount), 0.0))
            .filter(Payment.created_at >= start, Payment.created_at < end)
            .group_by(Payment.method)
            .all()
        )
        totals = {pm.value: 0.0 for pm in PaymentMethod}
        for method, total in rows:
            if method is not None:
                totals[method.value] = float(total or 0.0)
        return totals

    def daily_summary(self, db: Session, target_date: date) -> Dict:
        start, end = self._day_range(target_date)
        revenue, discounts, orders_paid = (
            db.query(
                func.coalesce(func.sum(Payment.final_amount), 0.0),
                func.coalesce(func.sum(Payment.discount_amount), 0.0),
                func.count(Payment.id),
            )
            .filter(Payment.created_at >= start, Payment.created_at < end)
            .one()
        )
        orders_total = (
                db.query(func.count(Order.id))
                .filter(Order.created_at >= start, Order.created_at < end)
                .scalar()
                or 0
        )
        by_method = self._method_totals(db, start, end)
        return {
            "date": target_date,
            "revenue": float(revenue or 0.0),
            "discounts": float(discounts or 0.0),
            "orders_total": int(orders_total),
            "orders_paid": int(orders_paid or 0),
            "avg_check": (float(revenue or 0.0) / float(orders_paid)) if orders_paid else 0.0,
            "by_method": by_method,
        }

    def monthly_summary(self, db: Session, year: int, month: int) -> Dict:
        start, end, last_day = self._month_range(year, month)
        payments = (
            db.query(func.date(Payment.created_at), func.coalesce(func.sum(Payment.final_amount), 0.0))
            .filter(Payment.created_at >= start, Payment.created_at < end)
            .group_by(func.date(Payment.created_at))
            .all()
        )
        daily: Dict[int, float] = {}
        total_revenue = 0.0
        for day_date, day_total in payments:
            if not day_date:
                continue
            day_number = int(str(day_date)[-2:])
            amount = float(day_total or 0.0)
            daily[day_number] = amount
            total_revenue += amount

        payments_count = (
                db.query(func.count(Payment.id))
                .filter(Payment.created_at >= start, Payment.created_at < end)
                .scalar()
                or 0
        )
        days = list(range(1, last_day + 1))
        values = [daily.get(d, 0.0) for d in days]
        return {
            "year": year,
            "month": month,
            "revenue": total_revenue,
            "count": int(payments_count),
            "days": days,
            "values": values,
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
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)

        # SQL aqreqasiyası ilə aylıq məlumatları birbaşa hesabla
        monthly_data = (
            db.query(
                extract('month', Payment.created_at).label('month'),
                func.coalesce(func.sum(Payment.final_amount), 0.0).label('revenue'),
                func.count(Payment.id).label('orders')
            )
            .filter(Payment.created_at >= start, Payment.created_at < end)
            .group_by(extract('month', Payment.created_at))
            .all()
        )

        monthly_revenue: List[float] = [0.0 for _ in range(12)]
        monthly_orders: List[int] = [0 for _ in range(12)]

        for month, revenue, orders in monthly_data:
            idx = int(month) - 1
            monthly_revenue[idx] = float(revenue or 0.0)
            monthly_orders[idx] = int(orders or 0)
        return {
            "year": year,
            "monthly_revenue": monthly_revenue,
            "monthly_orders": monthly_orders,
            "total_revenue": sum(monthly_revenue),
            "total_orders": sum(monthly_orders),
        }

    def weekly_summary(self, db: Session, target_date: date) -> Dict:
        start = datetime.combine(target_date - timedelta(days=6), datetime.min.time())
        end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
        rows = (
            db.query(func.date(Payment.created_at), func.coalesce(func.sum(Payment.final_amount), 0.0))
            .filter(Payment.created_at >= start, Payment.created_at < end)
            .group_by(func.date(Payment.created_at))
            .all()
        )
        totals_by_day = {str(d): float(total or 0.0) for d, total in rows if d}
        labels: List[str] = []
        values: List[float] = []
        day_names = ['B.e.', 'Çər.e', 'Çər.', 'Cüm.e', 'Cüm.', 'Şən.', 'Baz.']
        for i in range(6, -1, -1):
            d = target_date - timedelta(days=i)
            labels.append(day_names[d.weekday()] + '\n' + d.strftime('%d/%m'))
            values.append(round(totals_by_day.get(str(d), 0.0), 2))
        return {
            "labels": labels,
            "values": values,
            "total": sum(values),
        }

    def completed_sales(self, db: Session, target_date: date, limit: int = 50) -> List[Dict]:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        rows = (
            db.query(Order, Payment)
            .options(
                joinedload(Order.table),
                joinedload(Order.waiter),
                selectinload(Order.items).joinedload(OrderItem.menu_item),
            )
            .join(Payment, Payment.order_id == Order.id)
            .filter(Payment.created_at >= start, Payment.created_at <= end)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )
        data: List[Dict] = []
        for order, payment in rows:
            items_detail: List[Dict] = []
            for item in order.items:
                items_detail.append({
                    "name": item.menu_item.name if item.menu_item else "Məhsul",
                    "quantity": int(item.quantity or 0),
                    "unit_price": float(item.unit_price or 0),
                    "subtotal": float(item.subtotal or 0),
                })

            data.append({
                "order_id": order.id,
                "table": order.table.number if order.table else None,
                "status": order.status.value,
                "items": len(order.items),
                "items_detail": items_detail,
                "waiter": order.waiter.full_name if order.waiter else "—",
                "method": payment.method.value,
                "subtotal": float(payment.amount or order.subtotal or 0),
                "discount": float(payment.discount_amount or order.discount_amount or 0),
                "amount": float(payment.final_amount or 0),
                "paid_at": payment.created_at.strftime("%d.%m.%Y %H:%M") if payment.created_at else "—",
            })
        return data

    def hourly_heatmap(self, db: Session, target_date: date) -> Dict:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        orders = db.query(Order).filter(
            Order.created_at >= start,
            Order.created_at <= end,
            Order.status != OrderStatus.cancelled,
        ).all()
        hourly: Dict[int, int] = {h: 0 for h in range(24)}
        for o in orders:
            hourly[o.created_at.hour] += 1
        return {
            "hours": list(range(24)),
            "counts": [hourly[h] for h in range(24)],
        }


report_service = ReportService()
