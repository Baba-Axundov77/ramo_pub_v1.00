from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Set


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        "manage_kitchen",
        "manage_users",
        "manage_menu",
        "manage_inventory",
        "view_reports",
        "manage_discounts",
        "manage_tables",
        "take_orders",
        "process_payment",
        "manage_reservations",
        "manage_settings",
        "print_receipts",
    },
    "manager": {
        "manage_menu",
        "manage_inventory",
        "view_reports",
        "manage_discounts",
        "manage_tables",
        "take_orders",
        "manage_reservations",
    },
    "waiter": {
        "manage_tables",
        "take_orders",
        "manage_reservations",
    },
    "cashier": {
        "process_payment",
        "view_reports",
        "print_receipts",
    },
    "kitchen": {
        "manage_kitchen",
    },
}


@dataclass(frozen=True)
class UserContext:
    id: int | None
    role: str | None


class PermissionService:
    def get_permissions(self, role: str | None) -> Set[str]:
        if not role:
            return set()
        return ROLE_PERMISSIONS.get(role, set())

    def has_permission(self, role: str | None, permission: str) -> bool:
        return permission in self.get_permissions(role)

    def has_any_permission(self, role: str | None, permissions: Iterable[str]) -> bool:
        role_perms = self.get_permissions(role)
        return any(p in role_perms for p in permissions)


permission_service = PermissionService()
