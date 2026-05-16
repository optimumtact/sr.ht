from datetime import datetime
import re

from srht.database import db
from srht.objects import Job, Tag, Upload, User
from srht.tasks.basetask import TaskStatus, TaskType


def _create_admin(app):
    with app.app_context():
        user = User("admin", "admin@example.com", "password123")
        user.suspended = False
        user.admin = True
        db.session.add(user)
        db.session.commit()


def _login_admin(client):
    login_response = client.post(
        "/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=False,
    )

    reauth_form = client.get("/admin/login?return_to=%2Fadmin%2Fusers")
    csrf_match = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"',
        reauth_form.get_data(as_text=True),
    )
    csrf_token = csrf_match.group(1) if csrf_match else ""

    reauth_response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "password123",
            "return_to": "/admin/users",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    return login_response, reauth_response


def _login_admin_user_session_only(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=False,
    )


def test_htmx_admin_uploads_requires_login(client):
    response = client.get("/admin/uploads")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_htmx_admin_uploads_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/uploads")
    assert response.status_code == 200
    assert b"All uploads" in response.data


def test_htmx_admin_uploads_filters_by_uploader_date_and_description(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        alice = User("alice", "alice@example.com", "password123")
        alice.suspended = False
        bob = User("bob", "bob@example.com", "password123")
        bob.suspended = False
        db.session.add_all([alice, bob])
        db.session.flush()

        upload_alice = Upload()
        upload_alice.user_id = alice.id
        upload_alice.hash = "hash-alice"
        upload_alice.path = "alice-upload.png"
        upload_alice.thumbnail = None
        upload_alice.original_name = "alice-upload.png"
        upload_alice.created = datetime(2026, 1, 12, 9, 30, 0)

        upload_bob = Upload()
        upload_bob.user_id = bob.id
        upload_bob.hash = "hash-bob"
        upload_bob.path = "bob-upload.png"
        upload_bob.thumbnail = None
        upload_bob.original_name = "bob-upload.png"
        upload_bob.created = datetime(2026, 1, 13, 10, 45, 0)

        db.session.add_all([upload_alice, upload_bob])
        db.session.commit()
        alice_id = alice.id

    response = client.get(
        f"/admin/uploads?uploader_id={alice_id}&uploaded_from=2026-01-12&uploaded_to=2026-01-12&description=alice"
    )
    assert response.status_code == 200
    assert b"alice-upload.png" in response.data
    assert b"bob-upload.png" not in response.data
    assert b'name="description" value="alice"' in response.data
    assert b'name="uploaded_from" value="2026-01-12"' in response.data
    assert b'name="uploaded_to" value="2026-01-12"' in response.data


def test_htmx_admin_uploads_invalid_date_filter_shows_error(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/uploads?uploaded_from=2026-99-99")
    assert response.status_code == 200
    assert b"Upload from date must be in YYYY-MM-DD format." in response.data


def test_admin_deletes_other_user_upload_via_admin_endpoint_only(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        member = User("member_upload_owner", "member_upload_owner@example.com", "password123")
        member.suspended = False
        db.session.add(member)
        db.session.flush()

        upload = Upload()
        upload.user_id = member.id
        upload.hash = "owner-upload-hash"
        upload.path = "owner-upload.png"
        upload.thumbnail = None
        upload.original_name = "owner-upload.png"
        db.session.add(upload)
        db.session.flush()

        tag = Tag(uploadid=upload.id, tag="admin cleanup", relevance=0.9)
        db.session.add(tag)
        db.session.commit()
        upload_id = upload.id

    regular_delete = client.post(
        f"/uploads/{upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert regular_delete.status_code == 404

    admin_delete = client.post(
        f"/admin/uploads/{upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert admin_delete.status_code == 204

    with app.app_context():
        deleted_upload = db.session.get(Upload, upload_id)
        assert deleted_upload is None
        deleted_tags = db.session.query(Tag).filter(Tag.uploadid == upload_id).all()
        assert deleted_tags == []


def test_htmx_admin_jobs_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/jobs")
    assert response.status_code == 200
    assert b"Jobs queue" in response.data


def test_htmx_admin_jobs_filters_by_type_status_version_and_created_range(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        matching_job = Job(
            status=int(TaskStatus.FAILED),
            tasktype=int(TaskType.THUMBNAIL),
            priority=10,
            version=2,
            pickledclass=b"",
            taskmetadata={"example": True},
        )
        matching_job.created = datetime(2026, 2, 10, 9, 0, 0)

        non_matching_job = Job(
            status=int(TaskStatus.COMPLETE),
            tasktype=int(TaskType.THUMBNAIL),
            priority=20,
            version=1,
            pickledclass=b"",
            taskmetadata={"example": False},
        )
        non_matching_job.created = datetime(2026, 3, 10, 9, 0, 0)

        db.session.add_all([matching_job, non_matching_job])
        db.session.commit()
        matching_job_id = matching_job.id
        non_matching_job_id = non_matching_job.id

    response = client.get(
        "/admin/jobs?job_type=THUMBNAIL&job_status=FAILED&job_version=2&created_from=2026-02-01&created_to=2026-02-28"
    )
    assert response.status_code == 200
    assert f"/admin/jobs/{matching_job_id}/data".encode("utf-8") in response.data
    assert f"/admin/jobs/{non_matching_job_id}/data".encode("utf-8") not in response.data


def test_htmx_admin_jobs_invalid_created_range_shows_error(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/jobs?created_from=2026-99-99")
    assert response.status_code == 200
    assert b"Created from date must be in YYYY-MM-DD format." in response.data


def test_htmx_admin_jobs_partial_for_hx_request(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/jobs", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert b'id="admin-content"' in response.data


def test_htmx_admin_job_data_not_found(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/jobs/999999/data")
    assert response.status_code == 404


def test_htmx_admin_job_logs_renders(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        job = Job(
            status=int(TaskStatus.COMPLETE),
            tasktype=int(TaskType.THUMBNAIL),
            priority=10,
            version=1,
            pickledclass=b"",
            taskmetadata={"example": True},
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    response = client.get(f"/admin/jobs/{job_id}/logs")
    assert response.status_code == 200
    assert f"Job #{job_id} logs".encode("utf-8") in response.data


def test_htmx_admin_users_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"User management" in response.data


def test_htmx_admin_users_create(client, app):
    _create_admin(app)
    _login_admin(client)

    # Get the form to extract CSRF token
    form_response = client.get("/admin/users")
    assert form_response.status_code == 200

    csrf_match = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"', form_response.get_data(as_text=True)
    )
    csrf_token = csrf_match.group(1) if csrf_match else ""

    response = client.post(
        "/admin/users/create",
        data={
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "password123",
            "admin": "on",
            "csrf_token": csrf_token,
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter(User.username == "newmember").first()
        assert user is not None
        assert user.suspended is False
        assert user.admin is True
        assert user.ai_opt_in is False


def test_htmx_admin_users_ai_toggle(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member_ai", "member_ai@example.com", "password123")
        user.suspended = False
        user.ai_opt_in = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    enable = client.post(
        f"/admin/users/{user_id}/enable-ai",
        headers={"HX-Request": "true"},
    )
    assert enable.status_code == 200

    with app.app_context():
        enabled = db.session.get(User, user_id)
        assert enabled.ai_opt_in is True

    disable = client.post(
        f"/admin/users/{user_id}/disable-ai",
        headers={"HX-Request": "true"},
    )
    assert disable.status_code == 200

    with app.app_context():
        disabled = db.session.get(User, user_id)
        assert disabled.ai_opt_in is False


def test_htmx_admin_users_password_update(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member1", "member1@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        old_password_hash = user.password

    response = client.post(
        f"/admin/users/{user_id}/password",
        data={"password": "newpassword123"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200

    with app.app_context():
        updated_user = db.session.get(User, user_id)
        assert updated_user.password != old_password_hash


def test_htmx_admin_users_role_toggle(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member2", "member2@example.com", "password123")
        user.suspended = False
        user.admin = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    promote = client.post(
        f"/admin/users/{user_id}/make-admin",
        headers={"HX-Request": "true"},
    )
    assert promote.status_code == 200

    with app.app_context():
        promoted = db.session.get(User, user_id)
        assert promoted.admin is True

    demote = client.post(
        f"/admin/users/{user_id}/make-member",
        headers={"HX-Request": "true"},
    )
    assert demote.status_code == 200

    with app.app_context():
        demoted = db.session.get(User, user_id)
        assert demoted.admin is False


def test_htmx_admin_users_delete(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member4", "member4@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    response = client.post(
        f"/admin/users/{user_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200

    with app.app_context():
        deleted = db.session.get(User, user_id)
        assert deleted is None


def test_htmx_admin_users_cannot_demote_self(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        admin = User.query.filter(User.username == "admin").first()
        admin_id = admin.id

    response = client.post(
        f"/admin/users/{admin_id}/make-member",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert b"cannot remove your own admin role" in response.data.lower()


def test_htmx_admin_users_suspend_and_unsuspend(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member5", "member5@example.com", "password123")
        user.suspended = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    suspend_response = client.post(
        f"/admin/users/{user_id}/suspend",
        headers={"HX-Request": "true"},
    )
    assert suspend_response.status_code == 200

    with app.app_context():
        suspended_user = db.session.get(User, user_id)
        assert suspended_user.suspended is True
        assert suspended_user.admin is False

    unsuspend_response = client.post(
        f"/admin/users/{user_id}/unsuspend",
        headers={"HX-Request": "true"},
    )
    assert unsuspend_response.status_code == 200

    with app.app_context():
        unsuspended_user = db.session.get(User, user_id)
        assert unsuspended_user.suspended is False


def test_admin_browsing_does_not_require_reauth_cookie(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"User management" in response.data


def test_admin_mutation_requests_require_reauth_cookie(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    with app.app_context():
        user = User("mutation_target", "mutation_target@example.com", "password123")
        user.suspended = False
        user.admin = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    response = client.post(
        f"/admin/users/{user_id}/make-admin",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.headers.get("HX-Redirect")
    assert response.headers["HX-Redirect"].startswith("/admin/login?return_to=")


def test_admin_reauth_redirects_user_mutation_posts_to_users_view(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    with app.app_context():
        user = User("redirect_users_target", "redirect_users_target@example.com", "password123")
        user.suspended = False
        user.admin = False
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    response = client.post(
        f"/admin/users/{user_id}/make-admin",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.headers["HX-Redirect"].endswith("return_to=%2Fadmin%2Fusers")


def test_admin_reauth_redirects_upload_mutation_posts_to_uploads_view(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    with app.app_context():
        owner = User("redirect_upload_owner", "redirect_upload_owner@example.com", "password123")
        owner.suspended = False
        db.session.add(owner)
        db.session.flush()

        upload = Upload()
        upload.user_id = owner.id
        upload.hash = "redirect-upload-hash"
        upload.path = "redirect-upload.png"
        upload.thumbnail = None
        upload.original_name = "redirect-upload.png"
        db.session.add(upload)
        db.session.commit()
        upload_id = upload.id

    response = client.post(
        f"/admin/uploads/{upload_id}/delete",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.headers["HX-Redirect"].endswith("return_to=%2Fadmin%2Fuploads")


def test_admin_reauth_redirects_job_mutation_posts_to_jobs_view(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    with app.app_context():
        job = Job(
            status=int(TaskStatus.FAILED),
            tasktype=int(TaskType.THUMBNAIL),
            priority=10,
            version=1,
            pickledclass=b"",
            taskmetadata={"example": True},
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    response = client.post(
        f"/admin/jobs/{job_id}/retry",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.headers["HX-Redirect"].endswith("return_to=%2Fadmin%2Fjobs")


def test_admin_reauth_sets_strict_cookie(client, app):
    _create_admin(app)
    _login_admin_user_session_only(client)

    form_response = client.get("/admin/login?return_to=%2Fadmin%2Fusers")
    csrf_match = re.search(
        r'name="csrf_token" type="hidden" value="([^"]+)"',
        form_response.get_data(as_text=True),
    )
    csrf_token = csrf_match.group(1) if csrf_match else ""

    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "password123",
            "return_to": "/admin/users",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "admin_reauth=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=Strict" in set_cookie
