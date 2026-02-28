# modules/staff/staff_service.py - Python 3.10 uyumlu
from __future__ import annotations
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session
from database.models import User, Shift, UserRole


class StaffService:

    def get_all_staff(self, db: Session, active_only: bool = True) -> List[User]:
        q = db.query(User)
        if active_only:
            q = q.filter(User.is_active == True)
        return q.order_by(User.full_name).all()

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def create_staff(self, db: Session, username: str, full_name: str,
                     password: str, role: str, phone: str = "") -> Tuple[bool, object]:
        from modules.auth.auth_service import AuthService
        svc = AuthService()
        return svc.create_user(db, username, full_name, password, role, phone)

    def update_staff(self, db: Session, user_id: int, **kwargs) -> Tuple[bool, object]:
        user = self.get_user(db, user_id)
        if not user:
            return False, "Isci tapilmadi."
        for k, v in kwargs.items():
            if k == "password" and v:
                from modules.auth.auth_service import AuthService
                v = AuthService.hash_password(v)
                setattr(user, "password", v)
            elif hasattr(user, k):
                setattr(user, k, v)
        db.commit()
        return True, user

    def deactivate(self, db: Session, user_id: int) -> Tuple[bool, str]:
        user = self.get_user(db, user_id)
        if not user:
            return False, "Tapilmadi."
        user.is_active = False
        db.commit()
        return True, f"{user.full_name} deaktiv edildi."

    def get_shifts(self, db: Session, user_id: Optional[int] = None,
                   target_date: Optional[date] = None) -> List[Shift]:
        q = db.query(Shift)
        if user_id:
            q = q.filter(Shift.user_id == user_id)
        if target_date:
            q = q.filter(Shift.date == target_date)
        return q.order_by(Shift.date.desc()).all()

    def add_shift(self, db: Session, user_id: int, shift_date: date,
                  start: str = "09:00", end: str = "21:00",
                  notes: str = "") -> Tuple[bool, object]:
        from datetime import time as dtime
        try:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
            shift = Shift(
                user_id    = user_id,
                date       = shift_date,
                start_time = dtime(sh, sm),
                end_time   = dtime(eh, em),
                notes      = notes,
            )
            db.add(shift); db.commit(); db.refresh(shift)
            return True, shift
        except Exception as e:
            return False, str(e)

    def delete_shift(self, db: Session, shift_id: int) -> Tuple[bool, str]:
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            return False, "Novbe tapilmadi."
        db.delete(shift); db.commit()
        return True, "Novbe silindi."

    def get_today_shifts(self, db: Session) -> List[Shift]:
        return self.get_shifts(db, target_date=date.today())


staff_service = StaffService()
