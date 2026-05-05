import os
import re

from flask import Blueprint, Response, abort, redirect, render_template, request
from flask_login import current_user
from sqlalchemy import desc

from srht.common import adminrequired, loginrequired
from srht.config import _cfg, _cfgi
from srht.database import db
from srht.objects import Job, JobLog, Upload, User
from srht.tasks import Task
from srht.tasks.basetask import TaskStatus, TaskType

htmx_admin = Blueprint("htmx_admin", __name__, template_folder="../../templates")


def _is_htmx_request() -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _render_htmx(full_template: str, partial_template: str, **context):
    if _is_htmx_request():
        return render_template(partial_template, **context)
    return render_template(full_template, **context)


def _users_context():
    users = User.query.order_by(User.created).all()
    return {
        "users": users,
    }


def _render_users_content(form_errors=None, form_values=None):
    return render_template(
        "htmx/admin/_users_content.html",
        form_errors=form_errors,
        form_values=form_values,
        **_users_context(),
    )


def _admin_count() -> int:
    return User.query.filter(User.admin).count()


def _validate_new_user(username: str, email: str, password: str):
    errors = []

    if not username:
        errors.append("Username is required.")
    else:
        if not re.match(r"^[A-Za-z0-9_]+$", username):
            errors.append("Usernames are letters, numbers, underscores only.")
        if len(username) < 3 or len(username) > 24:
            errors.append("Username must be between 3 and 24 characters.")
        if User.query.filter(User.username.ilike(username)).first():
            errors.append("This username is already in use.")

    if not email:
        errors.append("Email is required.")
    else:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please use a valid email address.")
        if User.query.filter(User.email.ilike(email)).first():
            errors.append("This email is already in use.")

    if not password:
        errors.append("Password is required.")
    else:
        if len(password) < 5 or len(password) > 256:
            errors.append("Password must be between 5 and 256 characters.")

    return errors


@htmx_admin.route("/htmx/admin/users", methods=["GET"])
@loginrequired
@adminrequired
def users_admin():
    return _render_htmx(
        "htmx/admin/users.html",
        "htmx/admin/_users_content.html",
        **_users_context(),
    )


@htmx_admin.route("/htmx/admin/users/create", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_create():
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    admin = request.form.get("admin") == "on"

    errors = _validate_new_user(username, email, password)

    if errors:
        return _render_users_content(
            form_errors=errors,
            form_values={
                "username": username,
                "email": email,
                "admin": admin,
            },
        )

    user = User(username, email, password)
    user.suspended = False
    user.admin = admin
    db.session.add(user)
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/password", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_set_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    password = request.form.get("password") or ""
    if len(password) < 5 or len(password) > 256:
        return _render_users_content(
            form_errors=["Password must be between 5 and 256 characters."],
        )

    user.set_password(password)
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/make-admin", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_make_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.admin = True
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/make-member", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_make_member(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    if user.id == current_user.id:
        return _render_users_content(form_errors=["You cannot remove your own admin role."])

    if user.admin and _admin_count() <= 1:
        return _render_users_content(form_errors=["At least one admin is required."])

    user.admin = False
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/delete", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_delete(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    if user.id == current_user.id:
        return _render_users_content(form_errors=["You cannot delete your own account."])

    if user.admin and _admin_count() <= 1:
        return _render_users_content(form_errors=["At least one admin is required."])

    upload_count = Upload.query.filter(Upload.user_id == user.id).count()
    if upload_count > 0:
        return _render_users_content(
            form_errors=["Cannot delete a user that still owns uploads."],
        )

    db.session.delete(user)
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/suspend", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_suspend(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    if user.id == current_user.id:
        return _render_users_content(form_errors=["You cannot suspend your own account."])

    if user.admin and _admin_count() <= 1:
        return _render_users_content(form_errors=["At least one admin is required."])

    user.suspended = True
    user.admin = False
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/users/<int:user_id>/unsuspend", methods=["POST"])
@loginrequired
@adminrequired
def users_admin_unsuspend(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.suspended = False
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/htmx/admin/users")


@htmx_admin.route("/htmx/admin/uploads", methods=["GET"], defaults={"page": 1})
@htmx_admin.route("/htmx/admin/uploads/<int:page>", methods=["GET"])
@loginrequired
@adminrequired
def uploads_admin(page):
    pagination = db.paginate(
        db.select(Upload).order_by(desc(Upload.created)),
        page=page,
        per_page=_cfgi("perpage"),
    )
    return _render_htmx(
        "htmx/admin/uploads.html",
        "htmx/admin/_uploads_content.html",
        pagination=pagination,
        endpoint="htmx_admin.uploads_admin",
    )


@htmx_admin.route("/htmx/admin/uploads/<int:upload_id>/delete", methods=["POST"])
@loginrequired
@adminrequired
def uploads_admin_delete(upload_id):
    upload = db.session.get(Upload, upload_id)
    if not upload:
        abort(404)

    full_path = os.path.join(_cfg("storage"), upload.path)
    if os.path.exists(full_path):
        os.remove(full_path)

    if upload.thumbnail:
        thumb_path = os.path.join(_cfg("storage"), upload.thumbnail)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    db.session.delete(upload)
    db.session.commit()

    if _is_htmx_request():
        return Response(status=204)

    return redirect("/htmx/admin/uploads")


@htmx_admin.route("/htmx/admin/jobs", methods=["GET"], defaults={"page": 1})
@htmx_admin.route("/htmx/admin/jobs/<int:page>", methods=["GET"])
@loginrequired
@adminrequired
def jobs(page):
    pagination = db.paginate(
        db.select(Job).order_by(desc(Job.id)),
        page=page,
        per_page=_cfgi("perpage"),
    )
    return _render_htmx(
        "htmx/admin/jobs.html",
        "htmx/admin/_jobs_content.html",
        pagination=pagination,
        endpoint="htmx_admin.jobs",
        TaskType=TaskType,
        TaskStatus=TaskStatus,
        Task=Task,
    )


@htmx_admin.route("/htmx/admin/jobs/<int:job_id>/logs", methods=["GET"])
@loginrequired
@adminrequired
def job_logs(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)
    logs = JobLog.query.filter(JobLog.job_id == job_id).order_by(JobLog.created).all()
    return _render_htmx(
        "htmx/admin/job_logs.html",
        "htmx/admin/_job_logs_content.html",
        job=job,
        logs=logs,
    )


@htmx_admin.route("/htmx/admin/jobs/<int:job_id>/data", methods=["GET"])
@loginrequired
@adminrequired
def job_data(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)
    return _render_htmx(
        "htmx/admin/job_data.html",
        "htmx/admin/_job_data_content.html",
        job=job,
    )


@htmx_admin.route("/htmx/admin/jobs/<int:job_id>/retry", methods=["POST"])
@loginrequired
@adminrequired
def job_retry(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)
    if job.status != int(TaskStatus.FAILED):
        abort(400)

    if job.version < Task.LATEST_VERSION:
        abort(400)

    task = Task.get_task(job_id)
    task.requeue()

    if _is_htmx_request():
        return jobs(1)

    return redirect("/htmx/admin/jobs")
