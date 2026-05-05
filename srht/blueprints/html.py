from flask import (
    Blueprint,
    render_template,
    abort,
    request,
    redirect,
    Response,
    send_from_directory,
    current_app,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import desc
from srht.objects import User, Upload
from srht.config import _cfg, _cfgi
from srht.common import loginrequired, with_session
from srht.email import send_reset
from srht.database import db
from datetime import datetime, timedelta
import binascii
import os
import urllib
import re
import locale
import bcrypt

html = Blueprint("html", __name__, template_folder="../../templates")


def _is_htmx_request() -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _render_htmx(full_template: str, partial_template: str, **context):
    if _is_htmx_request():
        return render_template(partial_template, **context)
    return render_template(full_template, **context)


@html.route("/setup", methods=["GET", "POST"])
def setup():
    if User.query.count() != 0:
        return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))

    if request.method == "GET":
        return render_template("setup.html")

    errors = []
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    app_key = request.form.get("app_key")

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

    if not app_key:
        errors.append("App key is required.")
    elif app_key != _cfg("secret_key"):
        errors.append("App key is incorrect.")

    if errors:
        return render_template(
            "setup.html",
            username=username,
            email=email,
            errors=errors,
        )

    user = User(username, email, password)
    user.suspended = False
    user.admin = True
    db.session.add(user)
    db.session.commit()

    return redirect("%s://%s/login" % (_cfg("protocol"), _cfg("domain")))


@html.route("/")
def index():
    if User.query.count() == 0:
        return redirect("%s://%s/setup" % (_cfg("protocol"), _cfg("domain")))
    if current_user and not current_user.suspended:
        new = datetime.now() - timedelta(hours=24) < current_user.created
        total = Upload.query.count()
        st = os.statvfs("/")
        free_space = st.f_bavail * st.f_frsize
        total_space = st.f_blocks * st.f_frsize
        used_space = (st.f_blocks - st.f_bfree) * st.f_frsize
        return render_template(
            "index-member.html",
            new=new,
            total=total,
            used_space=used_space,
            free_space=free_space,
            total_space=total_space,
        )
    return render_template("index.html")


@html.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user:
            return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))
        reset = request.args.get("reset") == "1"
        return render_template(
            "login.html", **{"return_to": request.args.get("return_to"), "reset": reset}
        )
    else:
        username = request.form["username"]
        password = request.form["password"]
        remember = request.form.get("remember-me")
        if remember == "on":
            remember = True
        else:
            remember = False
        user = User.query.filter(User.username.ilike(username)).first()
        if not user:
            return render_template(
                "login.html",
                **{
                    "username": username,
                    "errors": "Your username or password is incorrect.",
                },
            )
        if not bcrypt.hashpw(
            password.encode("UTF-8"), user.password.encode("UTF-8")
        ) == user.password.encode("UTF-8"):
            return render_template(
                "login.html",
                **{
                    "username": username,
                    "errors": "Your username or password is incorrect.",
                },
            )
        if user.suspended:
            return render_template(
                "login.html",
                **{
                    "username": username,
                    "errors": "Your account is suspended. Please contact the site owner.",
                },
            )
        login_user(user, remember=remember)
        if "return_to" in request.form and request.form["return_to"]:
            return redirect(urllib.parse.unquote(request.form.get("return_to")))
        return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))


@html.route("/logout")
@loginrequired
def logout():
    logout_user()
    return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))


@html.route("/resources")
@loginrequired
def resources():
    return render_template("resources.html")


@html.route("/script")
@loginrequired
def script():
    return render_template("script.html")


@html.route("/sharex")
@loginrequired
def sharex():
    return render_template("sharex.html")


@html.route("/script.plain")
def script_plain():
    with open("templates/pstepw", "r") as f:
        resp = f.read().replace("{{ protocol }}", _cfg("protocol"))
        resp = resp.replace("{{ domain }}", _cfg("domain"))
    return Response(resp, mimetype="text/plain")


@html.route("/forgot-password", methods=["GET", "POST"])
@with_session
def forgot_password():
    if request.method == "GET":
        return render_template("forgot.html")
    else:
        email = request.form.get("email")
        if not email:
            return render_template("forgot.html", bad_email=True)
        user = User.query.filter(User.email == email).first()
        if not user:
            return render_template("forgot.html", bad_email=True, email=email)
        user.passwordReset = binascii.b2a_hex(os.urandom(20)).decode("utf-8")
        user.passwordResetExpiry = datetime.now() + timedelta(days=1)
        db.session.commit()
        send_reset(user)
        return render_template("forgot.html", success=True)


@html.route("/change", methods=["GET", "POST"])
@loginrequired
def change_password():
    if request.method == "GET":
        return render_template("change.html")
    else:
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not password or not password2:
            return render_template("change.html", errors="Please fill out both fields.")
        if password != password2:
            return render_template(
                "change.html",
                errors="You seem to have mistyped one of these, please try again.",
            )
        current_user.set_password(password)
        db.session.commit()
        return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))


@html.route("/reset", methods=["GET", "POST"])
@html.route("/reset/<username>/<confirmation>", methods=["GET", "POST"])
@with_session
def reset_password(username, confirmation):
    user = User.query.filter_by(username=username).first()
    if not user:
        redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))
    if request.method == "GET":
        if user.passwordResetExpiry is None or user.passwordResetExpiry < datetime.now():
            return render_template("reset.html", expired=True)
        if user.passwordReset != confirmation:
            redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))
        return render_template("reset.html", username=username, confirmation=confirmation)
    else:
        if user.passwordResetExpiry == None or user.passwordResetExpiry < datetime.now():
            abort(401)
        if user.passwordReset != confirmation:
            abort(401)
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not password or not password2:
            return render_template(
                "reset.html",
                username=username,
                confirmation=confirmation,
                errors="Please fill out both fields.",
            )
        if password != password2:
            return render_template(
                "reset.html",
                username=username,
                confirmation=confirmation,
                errors="You seem to have mistyped one of these, please try again.",
            )
        user.set_password(password)
        user.passwordReset = None
        user.passwordResetExpiry = None
        db.session.commit()
        return redirect("%s://%s/login?reset=1" % (_cfg("protocol"), _cfg("domain")))


@html.route("/uploads", methods=["GET"], defaults={"page": 1})
@html.route("/uploads/<page>", methods=["GET"])
@loginrequired
def uploads(page):
    page = int(page)
    original_name_raw = (request.args.get("original_name") or "").strip()
    uploaded_from_raw = (request.args.get("uploaded_from") or "").strip()
    uploaded_to_raw = (request.args.get("uploaded_to") or "").strip()
    filter_errors = []

    stmt = (
        db.select(Upload)
        .filter_by(user_id=current_user.id)
        .filter_by(hidden=False)
        .order_by(desc(Upload.created))
    )

    if original_name_raw:
        stmt = stmt.where(Upload.original_name.ilike(f"%{original_name_raw}%"))

    uploaded_from = None
    uploaded_to = None

    if uploaded_from_raw:
        try:
            uploaded_from = datetime.strptime(uploaded_from_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Uploaded from date must be in YYYY-MM-DD format.")

    if uploaded_to_raw:
        try:
            uploaded_to = datetime.strptime(uploaded_to_raw, "%Y-%m-%d")
        except ValueError:
            filter_errors.append("Uploaded to date must be in YYYY-MM-DD format.")

    if uploaded_from and uploaded_to and uploaded_from > uploaded_to:
        filter_errors.append("Upload date range is invalid.")

    if uploaded_from:
        stmt = stmt.where(Upload.created >= uploaded_from)
    if uploaded_to:
        stmt = stmt.where(Upload.created < uploaded_to + timedelta(days=1))

    uploads = db.paginate(
        stmt,
        page=page,
        per_page=_cfgi("perpage"),
    )

    pagination_query_params = {}
    if original_name_raw:
        pagination_query_params["original_name"] = original_name_raw
    if uploaded_from_raw:
        pagination_query_params["uploaded_from"] = uploaded_from_raw
    if uploaded_to_raw:
        pagination_query_params["uploaded_to"] = uploaded_to_raw

    context = {
        "pagination": uploads,
        "endpoint": "html.uploads",
        "selected_original_name": original_name_raw,
        "selected_uploaded_from": uploaded_from_raw,
        "selected_uploaded_to": uploaded_to_raw,
        "filter_errors": filter_errors,
        "pagination_query_params": pagination_query_params,
    }

    if request.headers.get("HX-Request", "").lower() == "true":
        return render_template("_uploads_content.html", **context)

    return render_template("uploads.html", **context)


@html.route("/uploads/<int:upload_id>/disown", methods=["POST"])
@loginrequired
def uploads_disown(upload_id):
    upload = Upload.query.filter_by(id=upload_id, user_id=current_user.id).first()
    if not upload:
        abort(404)

    upload.hidden = True
    db.session.commit()

    if request.headers.get("HX-Request", "").lower() == "true":
        return Response("", status=200)

    return redirect("/uploads")


@html.route("/uploads/<int:upload_id>/delete", methods=["POST"])
@loginrequired
def uploads_delete(upload_id):
    upload = Upload.query.filter_by(id=upload_id).first()
    if not upload:
        abort(404)

    if not (current_user.admin or upload.user_id == current_user.id):
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

    if request.headers.get("HX-Request", "").lower() == "true":
        return Response("", status=200)

    return redirect("/uploads")


@html.route("/<path:filename>", methods=["GET"])
def serve_file(filename):
    print(_cfg("storage"), filename)
    return send_from_directory(_cfg("storage"), filename)
