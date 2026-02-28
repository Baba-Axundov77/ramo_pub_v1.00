# modules/reservation/reservation_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Optional, Tuple, Set
from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session
from database.models import Reservation, Table


class ReservationService:

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
        conflict = db.query(Reservation).filter(
            Reservation.table_id     == table_id,
            Reservation.date         == res_date,
            Reservation.is_cancelled == False,
        ).all()
        for r in conflict:
            r_dt   = datetime.combine(res_date, r.time)
            new_dt = datetime.combine(res_date, res_time)
            if abs((r_dt - new_dt).total_seconds()) < 7200:
                return False, (f"Bu masa {res_date} tarixde saat "
                               f"{r.time.strftime('%H:%M')}-da artiq rezerv edilib.")
        res = Reservation(
            table_id       = table_id,
            customer_name  = customer_name,
            customer_phone = customer_phone,
            date           = res_date,
            time           = res_time,
            guest_count    = guest_count,
            notes          = notes,
            is_confirmed   = True,
        )
        db.add(res); db.commit(); db.refresh(res)
        return True, res

    def confirm(self, db: Session, res_id: int) -> Tuple[bool, object]:
        res = self.get_by_id(db, res_id)
        if not res:
            return False, "Rezervasiya tapilmadi."
        res.is_confirmed = True
        db.commit()
        return True, res

    def cancel(self, db: Session, res_id: int) -> Tuple[bool, str]:
        res = self.get_by_id(db, res_id)
        if not res:
            return False, "Tapilmadi."
        res.is_cancelled = True
        db.commit()
        return True, "Rezervasiya legv edildi."

    def get_today(self, db: Session) -> List[Reservation]:
        return self.get_all(db, target_date=date.today())

    def get_upcoming_count(self, db: Session) -> int:
        return len(self.get_all(db, upcoming_only=True))

    def get_available_tables(self, db: Session, res_date: date,
                              res_time: time, duration_hours: int = 2) -> List[Table]:
        all_tables = db.query(Table).filter(Table.is_active == True).all()
        reserved_ids: Set[int] = set()
        reservations = db.query(Reservation).filter(
            Reservation.date         == res_date,
            Reservation.is_cancelled == False,
        ).all()
        new_dt = datetime.combine(res_date, res_time)
        for r in reservations:
            r_dt = datetime.combine(res_date, r.time)
            if abs((r_dt - new_dt).total_seconds()) < duration_hours * 3600:
                reserved_ids.add(r.table_id)
        return [t for t in all_tables if t.id not in reserved_ids]


reservation_service = ReservationService()
