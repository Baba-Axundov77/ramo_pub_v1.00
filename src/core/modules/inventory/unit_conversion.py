from __future__ import annotations

UNIT_ALIASES = {
    "q": "qram",
    "qr": "qram",
    "gram": "qram",
    "g": "qram",
    "kq": "kq",
    "kg": "kq",
    "ml": "ml",
    "millilitr": "ml",
    "l": "litr",
    "lt": "litr",
    "litr": "litr",
    "əd": "ədəd",
    "eded": "ədəd",
    "ədəd": "ədəd",
}

CONVERSION_TO_BASE = {
    "qram": ("mass", 1.0),
    "kq": ("mass", 1000.0),
    "ml": ("volume", 1.0),
    "litr": ("volume", 1000.0),
    "ədəd": ("count", 1.0),
}


def normalize_unit(unit: str | None) -> str:
    if not unit:
        return "ədəd"
    raw = unit.strip().lower()
    return UNIT_ALIASES.get(raw, raw)


def convert_quantity(amount: float, from_unit: str | None, to_unit: str | None) -> tuple[bool, float, str]:
    src = normalize_unit(from_unit)
    dst = normalize_unit(to_unit)
    if src == dst:
        return True, float(amount), ""

    src_data = CONVERSION_TO_BASE.get(src)
    dst_data = CONVERSION_TO_BASE.get(dst)
    if not src_data or not dst_data:
        return False, 0.0, f"Dəstəklənməyən vahid: {src} -> {dst}"

    src_group, src_mul = src_data
    dst_group, dst_mul = dst_data
    if src_group != dst_group:
        return False, 0.0, f"Uyğunsuz vahid çevirməsi: {src} -> {dst}"

    base_amount = float(amount) * src_mul
    converted = base_amount / dst_mul
    return True, converted, ""
