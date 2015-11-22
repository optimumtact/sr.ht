from flask import Blueprint, render_template, abort, request, redirect, url_for, send_file, Response
from flask.ext.login import current_user, login_user, logout_user
from srht.database import db
from srht.objects import *
from srht.common import *
from srht.config import _cfg

from datetime import datetime, timedelta
import os
import hashlib

oauth = Blueprint('oauth', __name__, template_folder='../../templates')

@oauth.route("/oauth/clients")
def clients():
    return render_template("oauth-clients.html")

@oauth.route("/oauth/clients", methods=["POST"])
def clients_POST():
    name = request.form.get("name")
    info_url = request.form.get("info_url")
    redirect_uri = request.form.get("redirect_uri")
    if not name or not info_url or not redirect_uri:
        return render_template("oauth-clients.html", errors="All fields are required.")
    if not info_url.startswith("http://") and not info_url.startswith("https://"):
        return render_template("oauth-clients.html", errors="URL fields must be a URL.")
    if not redirect_uri.startswith("http://") and not redirect_uri.startswith("https://"):
        return render_template("oauth-clients.html", errors="URL fields must be a URL.")
    client = OAuthClient(current_user, name, info_url, redirect_uri)
    db.add(client)
    db.commit()
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/regenerate")
def regenerate(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    salt = os.urandom(40)
    client.client_secret = hashlib.sha256(salt).hexdigest()[:40]
    db.commit()
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/revoke")
def revoke_all(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    # TODO: Revoke tokens
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/delete")
def delete_client(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    db.delete(client)
    db.commit()
    return redirect("/oauth/clients")
