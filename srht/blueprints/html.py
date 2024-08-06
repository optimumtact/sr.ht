from flask import (
    Blueprint,
    render_template,
    abort,
    request,
    redirect,
    Response,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import desc
from srht.objects import User, Upload
from srht.config import _cfg, _cfgi
from srht.common import loginrequired, with_session, adminrequired
from srht.email import send_reset, send_request_notification
from srht.database import db

from datetime import datetime, timedelta
import binascii
import os
import urllib
import re
import locale
import bcrypt

encoding = locale.getdefaultlocale()[1]
html = Blueprint("html", __name__, template_folder="../../templates")


@html.route("/")
def index():
    if current_user and current_user.approved:
        new = datetime.now() - timedelta(hours=24) < current_user.approvalDate
        total = Upload.query.count()
        st = os.statvfs("/")
        free_space = st.f_bavail * st.f_frsize
        total_space = st.f_blocks * st.f_frsize
        used_space = (st.f_blocks - st.f_bfree) * st.f_frsize
        approvals = User.query.filter(User.approved is False).filter(User.rejected is False).count()
        return render_template(
            "index-member.html",
            new=new,
            total=total,
            used_space=used_space,
            free_space=free_space,
            total_space=total_space,
            approvals=approvals,
        )
    registration = False
    if _cfg("registration") and _cfg("registration") == "True":
        registration = True
    return render_template("index.html", registration=registration)


@html.route("/register", methods=["POST"])
def register():
    errors = list()
    registration = True
    if _cfg("registration") and _cfg("registration") != "True":
        registration = False
        errors.append("Registration is currently disabled")

    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    comments = request.form.get("comments")
    if not email:
        errors.append("Email is required.")
    else:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please use a valid email address.")
        if User.query.filter(User.username.ilike(username)).first():
            errors.append("This username is already in use.")
    if not username:
        errors.append("Username is required.")
    else:
        if not re.match(r"^[A-Za-z0-9_]+$", username):
            errors.append("Usernames are letters, numbers, underscores only.")
        if len(username) < 3 or len(username) > 24:
            errors.append("Username must be between 3 and 24 characters.")
        if User.query.filter(User.username.ilike(username)).first():
            errors.append("This username is already in use.")
    if not password:
        errors.append("Password is required.")
    else:
        if len(password) < 5 or len(password) > 256:
            errors.append("Password must be between 5 and 256 characters.")
    if len(errors) != 0:
        return render_template(
            "index.html",
            username=username,
            email=email,
            errors=errors,
            registration=registration,
        )
    # All good, create an account for them
    user = User(username, email, password)
    user.comments = comments
    db.session.add(user)
    db.session.commit()
    send_request_notification(user)
    return render_template("index.html", registered=True, registration=registration)


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
                }
            )
        if not bcrypt.hashpw(
            password.encode("UTF-8"), user.password.encode("UTF-8")
        ) == user.password.encode("UTF-8"):
            return render_template(
                "login.html",
                **{
                    "username": username,
                    "errors": "Your username or password is incorrect.",
                }
            )
        if not user.approved:
            return redirect("%s://%s/pending" % (_cfg("protocol"), _cfg("domain")))
        login_user(user, remember=remember)
        if "return_to" in request.form and request.form["return_to"]:
            return redirect(urllib.parse.unquote(request.form.get("return_to")))
        return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))


@html.route("/logout")
@loginrequired
def logout():
    logout_user()
    return redirect("%s://%s/" % (_cfg("protocol"), _cfg("domain")))


@html.route("/pending")
def pending():
    return render_template("pending.html")


@html.route("/donate")
@loginrequired
def donate():
    return render_template("donate.html")


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


@html.route("/approvals")
@loginrequired
@adminrequired
def approvals():
    users = (
        User.query.filter(User.approved is False)
        .filter(User.rejected is False)
        .order_by(User.created)
    )
    return render_template("approvals.html", users=users)


@html.route("/users")
@loginrequired
@adminrequired
def users():
    users = User.query.filter(User.approved).order_by(User.created).all()
    return render_template("users.html", users=users)


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
    user = User.query.filter(User.username == username).first()
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
    uploads = db.paginate(
        db.select(Upload)
        .filter_by(user_id=current_user.id)
        .filter_by(hidden=False)
        .order_by(desc(Upload.created)),
        page=page,
        per_page=_cfgi("perpage"),
    )
    return render_template("uploads.html", pagination=uploads, endpoint="html.uploads")


@html.route("/admin_uploads", methods=["GET"], defaults={"page": 1})
@html.route("/admin_uploads/<page>", methods=["GET"])
@adminrequired
@loginrequired
def uploads_admin(page):
    page = int(page)
    uploads = db.paginate(
        db.select(Upload).order_by(desc(Upload.created)),
        page=page,
        per_page=_cfgi("perpage"),
    )
    return render_template("admin_uploads.html", pagination=uploads, endpoint="html.uploads_admin")
