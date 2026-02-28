#!/usr/bin/env python3
# check_setup.py  —  Sistemi başlatmadan əvvəl yoxla
"""
İstifadə:
    python check_setup.py
"""
from __future__ import annotations

import sys
import importlib
from typing import List, Tuple

MIN_PYTHON = (3, 10)

def check_python() -> Tuple[bool, str]:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    return ok, f"Python {v.major}.{v.minor}.{v.micro}"

def check_package(import_name: str, pip_name: str = "") -> Tuple[bool, str]:
    try:
        mod = importlib.import_module(import_name)
        ver = getattr(mod, "__version__", "?")
        return True, ver
    except ImportError:
        return False, f"YÜKLƏNMƏYİB — pip install {pip_name or import_name}"

PACKAGES: List[Tuple[str, str, str]] = [
    # (import_name,      pip_name,              açıqlama)
    ("sqlalchemy",       "SQLAlchemy",           "Verilənlər bazası ORM"),
    ("psycopg2",         "psycopg2-binary",      "PostgreSQL sürücüsü"),
    ("dotenv",           "python-dotenv",        "Mühit dəyişənləri"),
    ("PyQt6.QtWidgets",  "PyQt6",                "Desktop UI (PyQt6)"),
    ("matplotlib",       "matplotlib",           "Qrafiklər"),
    ("PIL",              "Pillow",               "Şəkil işləmə"),
    ("flask",            "Flask",                "Web panel"),
    ("werkzeug",         "Werkzeug",             "Flask asılılığı"),
    ("reportlab",        "reportlab",            "PDF çek (istəyə bağlı)"),
]

def main():
    print("\n" + "═"*54)
    print("  🍺 Ramo Pub — Sistem Yoxlaması")
    print("═"*54)

    # Python versiyası
    ok, info = check_python()
    status = "✅" if ok else "❌"
    print(f"\n{status}  Python  {info}")
    if not ok:
        print(f"   ❗ Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ tələb olunur!")
        sys.exit(1)

    print("\n  Paketlər:")
    print("  " + "-"*50)

    all_ok = True
    missing_required: List[str] = []
    missing_optional: List[str] = []
    optional = {"reportlab"}

    for import_name, pip_name, desc in PACKAGES:
        ok, info = check_package(import_name, pip_name)
        status = "✅" if ok else ("⚠️ " if pip_name in optional else "❌")
        label = f"v{info}" if ok else info
        print(f"  {status}  {desc:<30} {label}")
        if not ok:
            if pip_name in optional:
                missing_optional.append(pip_name)
            else:
                missing_required.append(pip_name)
                all_ok = False

    # .env faylı
    import os
    from pathlib import Path
    env_ok = Path(".env").exists()
    print(f"\n  {'✅' if env_ok else '❌'}  .env faylı{'    mövcuddur' if env_ok else '    YÜKLƏNMƏYİB'}")
    if not env_ok:
        print("     → cp .env.example .env  komandası ilə yaradın")
        all_ok = False

    # PostgreSQL yoxlaması
    if not missing_required or "psycopg2-binary" not in missing_required:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            import sqlalchemy as sa
            db_url = (
                f"postgresql://{os.getenv('DB_USER','postgres')}:"
                f"{os.getenv('DB_PASSWORD','')}@"
                f"{os.getenv('DB_HOST','localhost')}:"
                f"{os.getenv('DB_PORT','5432')}/"
                f"{os.getenv('DB_NAME','ramo_pub')}"
            )
            engine = sa.create_engine(db_url, pool_timeout=3, connect_args={"connect_timeout": 3})
            with engine.connect():
                print("  ✅  PostgreSQL    qoşuldu")
        except Exception as e:
            short = str(e)[:60]
            print(f"  ⚠️   PostgreSQL    Qoşulmadı → {short}")
            print("       → .env-dəki DB_PASSWORD-u yoxlayın")

    # Nəticə
    print("\n" + "═"*54)
    if all_ok:
        print("  ✅  Sistem hazırdır! →  python main.py")
    else:
        print("  ❌  Çatışmayan paketlər:")
        print(f"      pip install {' '.join(missing_required)}")
    if missing_optional:
        print(f"  ⚠️   İstəyə bağlı:  pip install {' '.join(missing_optional)}")
    print("═"*54 + "\n")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
