from datetime import datetime
import re

from srht.database import db
from srht.objects import Upload, User


def test_suspended_user_cannot_login(client, app):
    with app.app_context():
        user = User("suspended_user", "suspended@example.com", "password123")
        user.suspended = True
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={"username": "suspended_user", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Your account is suspended. Please contact the site owner." in response.data


def test_user_uploads_supports_htmx_filtering(client, app):
    with app.app_context():
        user = User("member_uploads", "member_uploads@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.flush()

        in_range = Upload()
        in_range.user_id = user.id
        in_range.hash = "in-range"
        in_range.path = "in-range.png"
        in_range.original_name = "in-range.png"
        in_range.thumbnail = None
        in_range.hidden = False
        in_range.created = datetime(2026, 1, 10, 10, 0, 0)

        out_of_range = Upload()
        out_of_range.user_id = user.id
        out_of_range.hash = "out-of-range"
        out_of_range.path = "out-of-range.png"
        out_of_range.original_name = "out-of-range.png"
        out_of_range.thumbnail = None
        out_of_range.hidden = False
        out_of_range.created = datetime(2026, 2, 10, 10, 0, 0)

        hidden_upload = Upload()
        hidden_upload.user_id = user.id
        hidden_upload.hash = "hidden"
        hidden_upload.path = "hidden.png"
        hidden_upload.original_name = "hidden.png"
        hidden_upload.thumbnail = None
        hidden_upload.hidden = True
        hidden_upload.created = datetime(2026, 1, 11, 10, 0, 0)

        db.session.add_all([in_range, out_of_range, hidden_upload])
        db.session.commit()

    client.post(
        "/login",
        data={"username": "member_uploads", "password": "password123"},
        follow_redirects=False,
    )

    response = client.get(
        "/uploads?uploaded_from=2026-01-01&uploaded_to=2026-01-31&original_name=in-range&description=flower",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert b'id="uploads-content"' in response.data
    assert b"in-range.png" in response.data
    assert b"out-of-range.png" not in response.data
    assert b"hidden.png" not in response.data
    assert b'name="original_name" value="in-range"' in response.data
    assert b'name="description" value="flower"' in response.data


def test_user_upload_actions_are_owner_scoped(client, app):
    with app.app_context():
        owner = User("owner_user", "owner_user@example.com", "password123")
        owner.suspended = False
        other = User("other_user", "other_user@example.com", "password123")
        other.suspended = False
        db.session.add_all([owner, other])
        db.session.flush()

        owner_upload = Upload()
        owner_upload.user_id = owner.id
        owner_upload.hash = "owner-hash"
        owner_upload.path = "owner.png"
        owner_upload.original_name = "owner.png"
        owner_upload.thumbnail = None
        owner_upload.hidden = False

        other_upload = Upload()
        other_upload.user_id = other.id
        other_upload.hash = "other-hash"
        other_upload.path = "other.png"
        other_upload.original_name = "other.png"
        other_upload.thumbnail = None
        other_upload.hidden = False

        db.session.add_all([owner_upload, other_upload])
        db.session.commit()
        owner_upload_id = owner_upload.id
        other_upload_id = other_upload.id

    client.post(
        "/login",
        data={"username": "owner_user", "password": "password123"},
        follow_redirects=False,
    )

    forbidden_delete = client.post(
        f"/uploads/{other_upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert forbidden_delete.status_code == 404

    own_delete = client.post(
        f"/uploads/{owner_upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert own_delete.status_code == 200

    with app.app_context():
        deleted_upload = db.session.get(Upload, owner_upload_id)
        assert deleted_upload is None


def test_non_admin_cannot_delete_another_users_upload(client, app):
    with app.app_context():
        attacker = User("attacker_user", "attacker_user@example.com", "password123")
        attacker.suspended = False
        victim = User("victim_user", "victim_user@example.com", "password123")
        victim.suspended = False
        db.session.add_all([attacker, victim])
        db.session.flush()

        victim_upload = Upload()
        victim_upload.user_id = victim.id
        victim_upload.hash = "victim-hash"
        victim_upload.path = "victim.png"
        victim_upload.original_name = "victim.png"
        victim_upload.thumbnail = None
        victim_upload.hidden = False
        db.session.add(victim_upload)
        db.session.commit()
        victim_upload_id = victim_upload.id

    client.post(
        "/login",
        data={"username": "attacker_user", "password": "password123"},
        follow_redirects=False,
    )

    response = client.post(
        f"/uploads/{victim_upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 404

    with app.app_context():
        upload_still_exists = db.session.get(Upload, victim_upload_id)
        assert upload_still_exists is not None


def test_member_index_renders_full_page_for_logged_in_user(client, app):
    with app.app_context():
        user = User("member_index", "member_index@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "member_index", "password": "password123"},
        follow_redirects=False,
    )

    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert b"<!doctype html>" in response.data
    assert b'id="index-member-content"' in response.data
    assert b"Logged in as member_index" in response.data


def test_donate_route_removed(client, app):
    with app.app_context():
        user = User("member_no_donate", "member_no_donate@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "member_no_donate", "password": "password123"},
        follow_redirects=False,
    )

    response = client.get("/donate")
    assert response.status_code == 404


def test_admin_login_requires_existing_user_session(client, app):
    with app.app_context():
        admin = User("admin_reauth_only", "admin_reauth_only@example.com", "password123")
        admin.suspended = False
        admin.admin = True
        db.session.add(admin)
        db.session.commit()

    response = client.get("/admin/login?return_to=%2Fadmin%2Fusers")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_login_sets_cookie_and_redirects(client, app):
    with app.app_context():
        admin = User("admin_reauth", "admin_reauth@example.com", "password123")
        admin.suspended = False
        admin.admin = True
        db.session.add(admin)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "admin_reauth", "password": "password123"},
        follow_redirects=False,
    )

    form_response = client.get("/admin/login?return_to=%2Fadmin%2Fusers")
    csrf_match = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"',
        form_response.get_data(as_text=True),
    )
    csrf_token = csrf_match.group(1) if csrf_match else ""

    response = client.post(
        "/admin/login",
        data={
            "username": "admin_reauth",
            "password": "password123",
            "return_to": "/admin/users",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")
    assert "admin_reauth=" in response.headers.get("Set-Cookie", "")


def test_logout_clears_admin_reauth_cookie(client, app):
    with app.app_context():
        admin = User("admin_logout", "admin_logout@example.com", "password123")
        admin.suspended = False
        admin.admin = True
        db.session.add(admin)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "admin_logout", "password": "password123"},
        follow_redirects=False,
    )

    form_response = client.get("/admin/login?return_to=%2Fadmin%2Fusers")
    csrf_match = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"',
        form_response.get_data(as_text=True),
    )
    csrf_token = csrf_match.group(1) if csrf_match else ""

    client.post(
        "/admin/login",
        data={
            "username": "admin_logout",
            "password": "password123",
            "return_to": "/admin/users",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "admin_reauth=;" in set_cookie
