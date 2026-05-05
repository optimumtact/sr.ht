from srht.database import db
from srht.objects import Job, User
from srht.tasks.basetask import TaskStatus, TaskType


def _create_admin(app):
    with app.app_context():
        user = User("admin", "admin@example.com", "password123")
        user.approved = True
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


def test_htmx_admin_jobs_renders_for_admin(client, app):
    _create_admin(app)
    _login_admin(client)

    response = client.get("/htmx/admin/jobs")
    assert response.status_code == 200
    assert b"Jobs queue" in response.data


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
    assert b"Users and approvals" in response.data


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
        assert user.approved is True
        assert user.admin is True


def test_htmx_admin_users_approve_and_reject(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("pending1", "pending1@example.com", "password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    approve_response = client.post(
        f"/htmx/admin/users/{user_id}/approve",
        headers={"HX-Request": "true"},
    )
    assert approve_response.status_code == 200

    with app.app_context():
        approved_user = db.session.get(User, user_id)
        assert approved_user.approved is True
        assert approved_user.rejected is False

    reject_response = client.post(
        f"/htmx/admin/users/{user_id}/reject",
        headers={"HX-Request": "true"},
    )
    assert reject_response.status_code == 200

    with app.app_context():
        rejected_user = db.session.get(User, user_id)
        assert rejected_user.approved is False
        assert rejected_user.rejected is True


def test_htmx_admin_users_password_update(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member1", "member1@example.com", "password123")
        user.approved = True
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
        user.approved = True
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


def test_htmx_admin_users_disable_enable(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member3", "member3@example.com", "password123")
        user.approved = True
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    disable = client.post(
        f"/htmx/admin/users/{user_id}/disable",
        headers={"HX-Request": "true"},
    )
    assert disable.status_code == 200

    with app.app_context():
        disabled = db.session.get(User, user_id)
        assert disabled.approved is False
        assert disabled.rejected is True

    enable = client.post(
        f"/htmx/admin/users/{user_id}/enable",
        headers={"HX-Request": "true"},
    )
    assert enable.status_code == 200

    with app.app_context():
        enabled = db.session.get(User, user_id)
        assert enabled.approved is True
        assert enabled.rejected is False


def test_htmx_admin_users_delete(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        user = User("member4", "member4@example.com", "password123")
        user.approved = True
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


def test_htmx_admin_users_cannot_disable_self(client, app):
    _create_admin(app)
    _login_admin(client)

    with app.app_context():
        admin = User.query.filter(User.username == "admin").first()
        admin_id = admin.id

    response = client.post(
        f"/htmx/admin/users/{admin_id}/disable",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert b"cannot disable your own account" in response.data.lower()
