from flask import Flask, render_template, request, url_for
from flask_login import LoginManager, current_user, login_user
from jinja2 import FileSystemLoader, ChoiceLoader

import random
import sys
import locale

from srht.config import _cfg
from srht.database import db
from srht.objects import User
from srht.common import admin_delete_link, file_link, disown_link, delete_link

from srht.blueprints.html import html
from srht.blueprints.api import api
from pathlib import Path
import os

app = Flask(__name__)
app.secret_key = _cfg("secret_key")
if _cfg("securecookie") and _cfg("securecookie") == "True":
    app.config.update(SESSION_COOKIE_SECURE=True)
app.jinja_env.cache = None
app.config["SQLALCHEMY_DATABASE_URI"] = _cfg("DATABASE_URL")
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Create thumbnail dir if ti doesnt exist
thumbnaildir = Path(os.path.join(_cfg("storage"), "thumbnails"))
os.makedirs(thumbnaildir, exist_ok=True)

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
    if _cfg('headerlogin') == "True":
        username = request.headers.get('Remote-User')
        user = User.query.filter(User.username.ilike(username)).first()
        if (user):
            login_user(user)

login_manager.anonymous_user = lambda: None

app.register_blueprint(html)
app.register_blueprint(api)

try:
    locale.setlocale(locale.LC_ALL, "en_US")
except:
    pass

if not app.debug:

    @app.errorhandler(500)
    def handle_500(e):
        # shit
        try:
            db.session.rollback()
            db.session.session.close()
        except:
            # shit shit
            sys.exit(1)
        return render_template("internal_error.html"), 500

    # Error handler
    if _cfg("errorto") != "":
        import logging
        from logging.handlers import SMTPHandler

        mail_handler = SMTPHandler(
            (_cfg("smtphost"), _cfg("smtpport")),
            _cfg("errorfrom"),
            [_cfg("errorto")],
            "sr.ht application exception occured",
            credentials=(_cfg("smtpuser"), _cfg("smtppassword")),
            secure=(),
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


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
