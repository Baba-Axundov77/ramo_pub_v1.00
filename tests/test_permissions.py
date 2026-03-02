from modules.auth.permissions import permission_service


def test_admin_has_manage_users_permission():
    assert permission_service.has_permission("admin", "manage_users")


def test_waiter_cannot_manage_users():
    assert not permission_service.has_permission("waiter", "manage_users")
