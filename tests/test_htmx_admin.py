from datetime import datetime

from srht.database import db
from srht.objects import Job, Upload, User
from srht.tasks.basetask import TaskStatus, TaskType


def _create_admin(app):
    with app.app_context():
        user = User("admin", "admin@example.com", "password123")
        user.suspended = False
        user.admin = True
        db.session.add(user)
        db.session.commit()


def _login_admin(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=False,
    )


def test_htmx_admin_uploads_requires_login(client):
    response = client.get("/htmx/admin/uploads")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_htmx_admin_uploads_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/uploads")
    assert response.status_code == 200
    assert b"All uploads" in response.data


def test_htmx_admin_uploads_filters_by_uploader_and_date(client, app):
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
        f"/htmx/admin/uploads?uploader_id={alice_id}&uploaded_from=2026-01-12&uploaded_to=2026-01-12"
    )
    assert response.status_code == 200
    assert b"alice-upload.png" in response.data
    assert b"bob-upload.png" not in response.data
    assert b'name="uploaded_from" value="2026-01-12"' in response.data
    assert b'name="uploaded_to" value="2026-01-12"' in response.data


def test_htmx_admin_uploads_invalid_date_filter_shows_error(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/uploads?uploaded_from=2026-99-99")
    assert response.status_code == 200
    assert b"Upload from date must be in YYYY-MM-DD format." in response.data


def test_htmx_admin_jobs_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/jobs")
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
        "/htmx/admin/jobs?job_type=THUMBNAIL&job_status=FAILED&job_version=2&created_from=2026-02-01&created_to=2026-02-28"
    )
    assert response.status_code == 200
    assert f"/htmx/admin/jobs/{matching_job_id}/data".encode("utf-8") in response.data
    assert f"/htmx/admin/jobs/{non_matching_job_id}/data".encode("utf-8") not in response.data


def test_htmx_admin_jobs_invalid_created_range_shows_error(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/jobs?created_from=2026-99-99")
    assert response.status_code == 200
    assert b"Created from date must be in YYYY-MM-DD format." in response.data


def test_htmx_admin_jobs_partial_for_hx_request(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/jobs", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert b'id="admin-content"' in response.data


def test_htmx_admin_job_data_not_found(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/jobs/999999/data")
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

    response = client.get(f"/htmx/admin/jobs/{job_id}/logs")
    assert response.status_code == 200
    assert f"Job #{job_id} logs".encode("utf-8") in response.data


def test_htmx_admin_users_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/users")
    assert response.status_code == 200
    assert b"User management" in response.data


def test_htmx_admin_users_create(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.post(
        "/htmx/admin/users/create",
        data={
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "password123",
            "admin": "on",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter(User.username == "newmember").first()
        assert user is not None
        assert user.suspended is False
        assert user.admin is True


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
        f"/htmx/admin/users/{user_id}/password",
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
        f"/htmx/admin/users/{user_id}/make-admin",
        headers={"HX-Request": "true"},
    )
    assert promote.status_code == 200

    with app.app_context():
        promoted = db.session.get(User, user_id)
        assert promoted.admin is True

    demote = client.post(
        f"/htmx/admin/users/{user_id}/make-member",
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
        f"/htmx/admin/users/{user_id}/delete",
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
        f"/htmx/admin/users/{admin_id}/make-member",
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
        f"/htmx/admin/users/{user_id}/suspend",
        headers={"HX-Request": "true"},
    )
    assert suspend_response.status_code == 200

    with app.app_context():
        suspended_user = db.session.get(User, user_id)
        assert suspended_user.suspended is True
        assert suspended_user.admin is False

    unsuspend_response = client.post(
        f"/htmx/admin/users/{user_id}/unsuspend",
        headers={"HX-Request": "true"},
    )
    assert unsuspend_response.status_code == 200

    with app.app_context():
        unsuspended_user = db.session.get(User, user_id)
        assert unsuspended_user.suspended is False
