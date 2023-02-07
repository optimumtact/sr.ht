from flask import Flask, render_template, request, g, Response, redirect, url_for
from flask_login import LoginManager, current_user
from jinja2 import FileSystemLoader, ChoiceLoader

import random
import sys
import os
import locale

from srht.config import _cfg, _cfgi
from srht.database import db, init_db
from srht.objects import User
from srht.common import *
from srht.network import *

from srht.blueprints.html import html
from srht.blueprints.api import api

app = Flask(__name__)
app.secret_key = _cfg("secret_key")
if _cfg("securecookie") and _cfg("securecookie") == "True":
    app.config.update(SESSION_COOKIE_SECURE=True)
app.jinja_env.cache = None
init_db()
login_manager = LoginManager()
login_manager.init_app(app)

app.jinja_loader = ChoiceLoader([
    FileSystemLoader("overrides"),
    FileSystemLoader("templates"),
])

@login_manager.user_loader
def load_user(username):
    return User.query.filter(User.username == username).first()

login_manager.anonymous_user = lambda: None

app.register_blueprint(html)
app.register_blueprint(api)

try:
    locale.setlocale(locale.LC_ALL, 'en_US')
except:
    pass

if not app.debug:
    @app.errorhandler(500)
    def handle_500(e):
        # shit
        try:
            db.rollback()
            db.close()
        except:
            # shit shit
            sys.exit(1)
        return render_template("internal_error.html"), 500
    # Error handler
    if _cfg("errorto") != "":
        import logging
        from logging.handlers import SMTPHandler
        mail_handler = SMTPHandler((_cfg("smtphost"), _cfg("smtpport")),
           _cfg("errorfrom"),
           [_cfg("errorto")],
           'sr.ht application exception occured',
           credentials=(_cfg("smtpuser"), _cfg("smtppassword")),
           secure=())
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

@app.errorhandler(404)
def handle_404(e):
    return render_template("not_found.html"), 404

@app.context_processor
def inject():
    return {
        'root': _cfg("protocol") + "://" + _cfg("domain"),
        'domain': _cfg("domain"),
        'protocol': _cfg("protocol"),
        'len': len,
        'any': any,
        'request': request,
        'locale': locale,
        'url_for': url_for,
        'file_link': file_link,
        'disown_link': disown_link,
        'delete_link': delete_link,
        'admin_delete_link': admin_delete_link,
        'user': current_user,
        'random': random,
        'owner': _cfg("owner"),
        'owner_name': _cfg("owner"),
        'owner_email': _cfg("owner_email"),
        'git_repo': _cfg("git_repo"),
        'support': _cfg("support"),
        'donate_link': _cfg("donate_link"),
        'donate_button_image': _cfg("donate_button_image"),
        'site_cost': _cfg("site_cost"),
        'current_financial_status': _cfg("current_financial_status"),
        '_cfg': _cfg
    }
