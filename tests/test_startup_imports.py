from __future__ import annotations

import importlib


def test_menu_service_importable():
    mod = importlib.import_module("modules.menu.menu_service")
    assert hasattr(mod, "MenuService")


def test_web_app_module_importable():
    mod = importlib.import_module("web.app")
    assert hasattr(mod, "create_app")
