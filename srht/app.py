import locale
import logging
import os
import random
from pathlib import Path

from flask import Flask, render_template, request, url_for
from flask_login import LoginManager, current_user, login_user
from jinja2 import ChoiceLoader, FileSystemLoader

from srht.blueprints.api import api
from srht.blueprints.html import html
from srht.common import (
    admin_delete_link,
    delete_link,
    disown_link,
    file_link,
    thumbnail_class,
    thumbnail_link,
    validate_storage_directory,
)
from srht.config import _cfg
from srht.database import db
from srht.objects import User

app = Flask(__name__)
app.secret_key = _cfg("secret_key")
if _cfg("securecookie") and _cfg("securecookie") == "True":
    app.config.update(SESSION_COOKIE_SECURE=True)
app.jinja_env.cache = None
app.config["SQLALCHEMY_DATABASE_URI"] = _cfg("DATABASE_URL")
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

validate_storage_directory()
app.jinja_loader = ChoiceLoader(
    [
        FileSystemLoader("overrides"),
        FileSystemLoader("templates"),
    ]
)


@login_manager.user_loader
def load_user(username):
    return User.query.filter(User.username == username).first()


# Middleware to log in user based on request headers
# TODO create user?
@app.before_request
def authenticate_user_from_header():
    if _cfg("headerlogin") == "True":
        username = request.headers.get("Remote-User")
        if username:
            user = User.query.filter(User.username.ilike(username)).first()
            if user:
                login_user(user)


login_manager.anonymous_user = lambda: None

app.register_blueprint(html)
app.register_blueprint(api)

try:
    locale.setlocale(locale.LC_ALL, "en_US")
except:
    pass


@app.errorhandler(500)
def handle_500(e):
    if app.debug:
        raise e
    try:
        db.session.rollback()
        db.session.close()
    except Exception:
        app.logger.exception("Failed to clean up DB session after 500")
    return render_template("internal_error.html"), 500


@app.errorhandler(404)
def handle_404(e):
    return render_template("not_found.html"), 404


@app.context_processor
def inject():
    return {
        "root": _cfg("protocol") + "://" + _cfg("domain"),
        "domain": _cfg("domain"),
        "protocol": _cfg("protocol"),
        "len": len,
        "any": any,
        "request": request,
        "locale": locale,
        "url_for": url_for,
        "file_link": file_link,
        "thumbnail_link": thumbnail_link,
        "thumbnail_class": thumbnail_class,
        "disown_link": disown_link,
        "delete_link": delete_link,
        "admin_delete_link": admin_delete_link,
        "user": current_user,
        "random": random,
        "owner": _cfg("owner"),
        "owner_name": _cfg("owner"),
        "owner_email": _cfg("owner_email"),
        "git_repo": _cfg("git_repo"),
        "support": _cfg("support"),
        "donate_link": _cfg("donate_link"),
        "donate_button_image": _cfg("donate_button_image"),
        "site_cost": _cfg("site_cost"),
        "current_financial_status": _cfg("current_financial_status"),
        "_cfg": _cfg,
    }
