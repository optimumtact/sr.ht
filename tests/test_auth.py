from datetime import datetime

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
        "/uploads?uploaded_from=2026-01-01&uploaded_to=2026-01-31&original_name=in-range",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert b'id="uploads-content"' in response.data
    assert b"in-range.png" in response.data
    assert b"out-of-range.png" not in response.data
    assert b"hidden.png" not in response.data
    assert b'name="original_name" value="in-range"' in response.data


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

    disown_own = client.post(
        f"/uploads/{owner_upload_id}/disown",
        headers={"HX-Request": "true"},
    )
    assert disown_own.status_code == 200

    with app.app_context():
        hidden_upload = db.session.get(Upload, owner_upload_id)
        assert hidden_upload.hidden is True


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
