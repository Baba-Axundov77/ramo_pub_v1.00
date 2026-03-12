# modules/auth/auth_service.py
import hashlib
import hmac
import os
import binascii
from sqlalchemy.orm import Session
from src.core.database.models import User, UserRole
from config import ROLES
from src.core.modules.auth.permissions import permission_service


def _pbkdf2_hash(plain: str) -> str:
    """bcrypt yerine PBKDF2 ile sifre hash'le - standart kutuphanenin parcasi."""
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 260000)
    return "pbkdf2:sha256:260000:" + binascii.hexlify(salt).decode() + ":" + binascii.hexlify(dk).decode()


def _pbkdf2_verify(plain: str, stored: str) -> bool:
    """PBKDF2 hash'i dogrula."""
    try:
        if stored.startswith("pbkdf2:"):
            parts = stored.split(":")
            # format: pbkdf2:sha256:iterations:salt_hex:dk_hex
            iterations = int(parts[2])
            salt = binascii.unhexlify(parts[3])
            expected_dk = binascii.unhexlify(parts[4])
            dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(dk, expected_dk)
        # Kohnə bcrypt hash-lerini de destekle (bcrypt varsa)
        elif stored.startswith("$2"):
            try:
                import bcrypt
                return bcrypt.checkpw(plain.encode(), stored.encode())
            except ImportError:
                # bcrypt yoxdursa, admin sifresini sifirla
                return False
        # Eski hashlib md5 - fallback
        return False
    except Exception:
        return False


class AuthService:
    """Istifadeci autentifikasiyasi ve sessiyanı idarə edir."""

    def __init__(self):
        self.current_user = None

    @staticmethod
    def hash_password(plain: str) -> str:
        # bcrypt varsa onu istifade et, yoksa PBKDF2
        try:
            import bcrypt
            return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            return _pbkdf2_hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return _pbkdf2_verify(plain, hashed)

    def login(self, db: Session, username: str, password: str):
        user = db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        if not user:
            return False, "Istifadeci adi tapilmadi."
        if not self.verify_password(password, user.password):
            return False, "Sifre yanlisdir."
        self.current_user = user
        return True, user

    def logout(self):
        self.current_user = None

    def create_user(self, db: Session, username: str, full_name: str,
                    password: str, role: str, phone: str = None):
        try:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                return False, "Bu istifadeci adi artiq movcuddur."
            user = User(
                username  = username,
                full_name = full_name,
                password  = self.hash_password(password),
                role      = UserRole[role],
                phone     = phone,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return True, user
        except Exception as e:
            db.rollback()
            return False, f"İstifadəçi yaradılarkən xəta: {str(e)}"

    def get_role_display(self, user: User) -> str:
        return ROLES.get(user.role.value, user.role.value)

    def is_admin(self) -> bool:
        return self.current_user and self.current_user.role == UserRole.admin

    def has_permission(self, permission: str) -> bool:
        if not self.current_user:
            return False
        return permission_service.has_permission(self.current_user.role.value, permission)


# Global instance
auth_service = AuthService()


def create_default_admin(db: Session):
    """Eger hec bir admin yoxdursa, default admin yarat."""
    admin_exists = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin_exists:
        svc = AuthService()
        initial_password = os.getenv("RAMO_DEFAULT_ADMIN_PASSWORD")
        if not initial_password:
            initial_password = binascii.hexlify(os.urandom(9)).decode()
        ok, result = svc.create_user(
            db=db,
            username="admin",
            full_name="Sistem Admini",
            password=initial_password,
            role="admin",
        )
        if ok:
            print(f"Default admin yaradildi: admin / {initial_password}")
        return ok, result
    return True, admin_exists
