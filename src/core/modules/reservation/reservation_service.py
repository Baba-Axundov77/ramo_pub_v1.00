# modules/reservation/reservation_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session
from src.core.database.models import Reservation, Table


class ReservationService:

    @staticmethod
    def _time_window(target_time: time, duration_hours: int) -> tuple[time, time]:
        center = datetime.combine(date.today(), target_time)
        delta = timedelta(hours=duration_hours)
        start_dt = center - delta
        end_dt = center + delta
        start_time = max(start_dt.time(), time.min)
        end_time = min(end_dt.time(), time.max)
        return start_time, end_time

    def get_all(self, db: Session, target_date: Optional[date] = None,
                upcoming_only: bool = False) -> List[Reservation]:
        q = db.query(Reservation).filter(Reservation.is_cancelled == False)
        if target_date:
            q = q.filter(Reservation.date == target_date)
        if upcoming_only:
            today = date.today()
            q = q.filter(Reservation.date >= today)
        return q.order_by(Reservation.date, Reservation.time).all()

    def get_by_id(self, db: Session, res_id: int) -> Optional[Reservation]:
        return db.query(Reservation).filter(Reservation.id == res_id).first()

    def create(self, db: Session, table_id: int, customer_name: str,
               customer_phone: str, res_date: date, res_time: time,
               guest_count: int = 2, notes: str = "") -> Tuple[bool, object]:
        try:
            window_start, window_end = self._time_window(res_time, duration_hours=2)
            conflict = db.query(Reservation).filter(
                Reservation.table_id == table_id,
                Reservation.date == res_date,
                Reservation.is_cancelled == False,
                Reservation.time >= window_start,
                Reservation.time <= window_end,
            ).order_by(Reservation.time.asc()).first()
            if conflict:
                return False, (f"Bu masa {res_date} tarixde saat "
                               f"{conflict.time.strftime('%H:%M')}-da artiq rezerv edilib.")
            res = Reservation(
                table_id=table_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                date=res_date,
                time=res_time,
                guest_count=guest_count,
                notes=notes,
                is_confirmed=True,
            )
            db.add(res)
            db.commit()
            db.refresh(res)
            return True, res
        except Exception as e:
            db.rollback()
            return False, f"Rezervasiya yaradılarkən xəta: {str(e)}"

    def confirm(self, db: Session, res_id: int) -> Tuple[bool, object]:
        try:
            res = self.get_by_id(db, res_id)
            if not res:
                return False, "Rezervasiya tapilmadi."
            res.is_confirmed = True
            db.commit()
            return True, res
        except Exception as e:
            db.rollback()
            return False, f"Rezervasiya təsdiqlənərkən xəta: {str(e)}"

    def cancel(self, db: Session, res_id: int) -> Tuple[bool, str]:
        try:
            res = self.get_by_id(db, res_id)
            if not res:
                return False, "Tapilmadi."
            res.is_cancelled = True
            db.commit()
            return True, "Rezervasiya legv edildi."
        except Exception as e:
            db.rollback()
            return False, f"Rezervasiya legv edilərkən xəta: {str(e)}"

    def get_today(self, db: Session) -> List[Reservation]:
        return self.get_all(db, target_date=date.today())

    def get_upcoming_count(self, db: Session) -> int:
        return db.query(Reservation).filter(
            Reservation.is_cancelled == False,
            Reservation.date >= date.today(),
        ).count()

    def get_available_tables(self, db: Session, res_date: date,
                             res_time: time, duration_hours: int = 2) -> List[Table]:
        window_start, window_end = self._time_window(res_time, duration_hours=duration_hours)
        reserved_table_ids = (
            db.query(Reservation.table_id)
            .filter(
                Reservation.date == res_date,
                Reservation.is_cancelled == False,
                Reservation.time >= window_start,
                Reservation.time <= window_end,
            )
            .subquery()
        )
        return (
            db.query(Table)
            .filter(
                Table.is_active == True,
                ~Table.id.in_(reserved_table_ids),
            )
            .order_by(Table.number.asc())
            .all()
        )


reservation_service = ReservationService()
