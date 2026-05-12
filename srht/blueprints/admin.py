import os
import re
import urllib
from datetime import datetime, timedelta

from flask import Blueprint, Response, abort, make_response, redirect, render_template, request
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import desc

from srht.admin_auth import (
    ADMIN_REAUTH_COOKIE_NAME,
    issue_admin_reauth_cookie,
    verify_admin_reauth_cookie,
)
from srht.common import adminreauthrequired, adminrequired, loginrequired
from srht.config import _cfg, _cfgi
from srht.database import db
from srht.objects import Job, JobLog, Upload, User
from srht.tasks import Task
from srht.tasks.basetask import TaskStatus, TaskType

admin = Blueprint("admin", __name__, template_folder="../../templates")


class NewUserForm(FlaskForm):
    """Form used solely for CSRF protection on the user creation endpoint."""

    pass


class AdminLoginForm(FlaskForm):
    """Form used solely for CSRF protection on the admin re-auth endpoint."""

    pass


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
        new_user_form=NewUserForm(),
        **_users_context(),
    )


def _admin_count() -> int:
    return User.query.filter(User.admin).count()


def _safe_admin_return_to(raw_return_to: str | None) -> str:
    if not raw_return_to:
        return "/admin/uploads"

    return_to = urllib.parse.unquote(raw_return_to)
    parsed = urllib.parse.urlparse(return_to)
    if parsed.netloc or parsed.scheme:
        return "/admin/uploads"
    if not return_to.startswith("/admin"):
        return "/admin/uploads"

    return return_to


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


@admin.route("/admin/login", methods=["GET", "POST"])
@loginrequired
@adminrequired
def admin_login():
    form = AdminLoginForm()
    return_to = _safe_admin_return_to(
        request.args.get("return_to") if request.method == "GET" else request.form.get("return_to")
    )

    if request.method == "GET":
        token = request.cookies.get(ADMIN_REAUTH_COOKIE_NAME)
        if token and verify_admin_reauth_cookie(token, current_user.id):
            return redirect(return_to)
        return render_template("admin_login.html", form=form, return_to=return_to)

    if not form.validate():
        abort(400)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    errors = []
    if username != current_user.username:
        errors.append("Invalid username or password.")
    elif not current_user.check_password(password):
        errors.append("Invalid username or password.")

    if errors:
        return render_template(
            "admin_login.html",
            form=form,
            return_to=return_to,
            username=username,
            errors=errors,
        )

    response = make_response(redirect(return_to))
    issue_admin_reauth_cookie(response, current_user.id)
    return response


@admin.route("/admin/users", methods=["GET"])
@loginrequired
@adminrequired
def users_admin():
    return _render_htmx(
        "htmx/admin/users.html",
        "htmx/admin/_users_content.html",
        new_user_form=NewUserForm(),
        **_users_context(),
    )


@admin.route("/admin/users/create", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
def users_admin_create():
    form = NewUserForm()
    if not form.validate():
        abort(400)

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

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/password", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
def users_admin_make_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.admin = True
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/make-member", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/suspend", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/users")


@admin.route("/admin/users/<int:user_id>/unsuspend", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
def users_admin_unsuspend(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    user.suspended = False
    db.session.commit()

    if _is_htmx_request():
        return _render_users_content()

    return redirect("/admin/users")


@admin.route("/admin/uploads", methods=["GET"], defaults={"page": 1})
@admin.route("/admin/uploads/<int:page>", methods=["GET"])
@loginrequired
@adminrequired
def uploads_admin(page):
    original_name_raw = (request.args.get("original_name") or "").strip()
    uploader_id_raw = (request.args.get("uploader_id") or "").strip()
    uploaded_on = (request.args.get("uploaded_on") or "").strip()
    uploaded_from_raw = (request.args.get("uploaded_from") or uploaded_on).strip()
    uploaded_to_raw = (request.args.get("uploaded_to") or uploaded_on).strip()
    filter_errors = []

    stmt = db.select(Upload).order_by(desc(Upload.created))

    if original_name_raw:
        stmt = stmt.where(Upload.original_name.ilike(f"%{original_name_raw}%"))

    uploader_id = None
    if uploader_id_raw:
        try:
            uploader_id = int(uploader_id_raw)
            stmt = stmt.where(Upload.user_id == uploader_id)
        except ValueError:
            filter_errors.append("Uploader filter is invalid.")

    uploaded_from = None
    uploaded_to = None

    if uploaded_from_raw:
        try:
            uploaded_from = datetime.strptime(uploaded_from_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Upload from date must be in YYYY-MM-DD format.")

    if uploaded_to_raw:
        try:
            uploaded_to = datetime.strptime(uploaded_to_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Upload to date must be in YYYY-MM-DD format.")

    if uploaded_from and uploaded_to and uploaded_from > uploaded_to:
        filter_errors.append("Upload date range is invalid.")

    if uploaded_from:
        stmt = stmt.where(Upload.created >= uploaded_from)
    if uploaded_to:
        stmt = stmt.where(Upload.created < uploaded_to + timedelta(days=1))

    pagination = db.paginate(
        stmt,
        page=page,
        per_page=_cfgi("perpage"),
    )

    uploader_users = User.query.order_by(User.username).all()
    pagination_query_params = {}
    if original_name_raw:
        pagination_query_params["original_name"] = original_name_raw
    if uploader_id_raw:
        pagination_query_params["uploader_id"] = uploader_id_raw
    if uploaded_from_raw:
        pagination_query_params["uploaded_from"] = uploaded_from_raw
    if uploaded_to_raw:
        pagination_query_params["uploaded_to"] = uploaded_to_raw

    return _render_htmx(
        "htmx/admin/uploads.html",
        "htmx/admin/_uploads_content.html",
        pagination=pagination,
        endpoint="admin.uploads_admin",
        uploader_users=uploader_users,
        selected_original_name=original_name_raw,
        selected_uploader_id=uploader_id_raw,
        selected_uploaded_from=uploaded_from_raw,
        selected_uploaded_to=uploaded_to_raw,
        filter_errors=filter_errors,
        pagination_query_params=pagination_query_params,
    )


@admin.route("/admin/uploads/<int:upload_id>/delete", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/uploads")


@admin.route("/admin/jobs", methods=["GET"], defaults={"page": 1})
@admin.route("/admin/jobs/<int:page>", methods=["GET"])
@loginrequired
@adminrequired
def jobs(page):
    job_type_raw = (request.args.get("job_type") or "").strip()
    job_status_raw = (request.args.get("job_status") or "").strip()
    job_version_raw = (request.args.get("job_version") or "").strip()
    created_from_raw = (request.args.get("created_from") or "").strip()
    created_to_raw = (request.args.get("created_to") or "").strip()
    filter_errors = []

    stmt = db.select(Job).order_by(desc(Job.id))

    if job_type_raw:
        parsed_job_type = None
        enum_key = job_type_raw.upper()
        if enum_key in TaskType.__members__:
            parsed_job_type = int(TaskType[enum_key])
        else:
            try:
                parsed_job_type = int(job_type_raw)
                TaskType(parsed_job_type)
            except (ValueError, KeyError):
                filter_errors.append("Job type filter is invalid.")
        if parsed_job_type is not None:
            stmt = stmt.where(Job.tasktype == parsed_job_type)

    if job_status_raw:
        parsed_job_status = None
        enum_key = job_status_raw.upper()
        if enum_key in TaskStatus.__members__:
            parsed_job_status = int(TaskStatus[enum_key])
        else:
            try:
                parsed_job_status = int(job_status_raw)
                TaskStatus(parsed_job_status)
            except (ValueError, KeyError):
                filter_errors.append("Job status filter is invalid.")
        if parsed_job_status is not None:
            stmt = stmt.where(Job.status == parsed_job_status)

    if job_version_raw:
        try:
            parsed_version = int(job_version_raw)
            if parsed_version < 0:
                raise ValueError
            stmt = stmt.where(Job.version == parsed_version)
        except ValueError:
            filter_errors.append("Job version filter is invalid.")

    created_from = None
    created_to = None
    if created_from_raw:
        try:
            created_from = datetime.strptime(created_from_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Created from date must be in YYYY-MM-DD format.")

    if created_to_raw:
        try:
            created_to = datetime.strptime(created_to_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Created to date must be in YYYY-MM-DD format.")

    if created_from and created_to and created_from > created_to:
        filter_errors.append("Created date range is invalid.")

    if created_from:
        stmt = stmt.where(Job.created >= created_from)
    if created_to:
        stmt = stmt.where(Job.created < created_to + timedelta(days=1))

    pagination = db.paginate(
        stmt,
        page=page,
        per_page=_cfgi("perpage"),
    )

    pagination_query_params = {}
    if job_type_raw:
        pagination_query_params["job_type"] = job_type_raw
    if job_status_raw:
        pagination_query_params["job_status"] = job_status_raw
    if job_version_raw:
        pagination_query_params["job_version"] = job_version_raw
    if created_from_raw:
        pagination_query_params["created_from"] = created_from_raw
    if created_to_raw:
        pagination_query_params["created_to"] = created_to_raw

    return _render_htmx(
        "htmx/admin/jobs.html",
        "htmx/admin/_jobs_content.html",
        pagination=pagination,
        endpoint="admin.jobs",
        TaskType=TaskType,
        TaskStatus=TaskStatus,
        Task=Task,
        job_type_options=[t for t in TaskType],
        job_status_options=[s for s in TaskStatus],
        selected_job_type=job_type_raw,
        selected_job_status=job_status_raw,
        selected_job_version=job_version_raw,
        selected_created_from=created_from_raw,
        selected_created_to=created_to_raw,
        filter_errors=filter_errors,
        pagination_query_params=pagination_query_params,
    )


@admin.route("/admin/jobs/<int:job_id>/logs", methods=["GET"])
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


@admin.route("/admin/jobs/<int:job_id>/data", methods=["GET"])
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


@admin.route("/admin/jobs/<int:job_id>/retry", methods=["POST"])
@loginrequired
@adminrequired
@adminreauthrequired
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

    return redirect("/admin/jobs")
