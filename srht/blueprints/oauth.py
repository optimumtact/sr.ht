from flask import Blueprint, render_template, abort, request, redirect, url_for, send_file, Response
from flask.ext.login import current_user, login_user, logout_user
from srht.database import db
from srht.objects import *
from srht.common import *
from srht.config import _cfg

from datetime import datetime, timedelta
import urllib
import redis
import os
import hashlib

oauth = Blueprint('oauth', __name__, template_folder='../../templates')

@oauth.route("/oauth/clients")
@loginrequired
def clients():
    return render_template("oauth-clients.html")

@oauth.route("/oauth/clients", methods=["POST"])
@loginrequired
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
    if len(current_user.clients) > 10:
        return render_template("oauth-clients.html", errors="You can only have 10 clients, chill out dude.")
    client = OAuthClient(current_user, name, info_url, redirect_uri)
    db.add(client)
    db.commit()
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/regenerate")
@loginrequired
def regenerate(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    salt = os.urandom(40)
    client.client_secret = hashlib.sha256(salt).hexdigest()[:40]
    db.commit()
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/revoke")
@loginrequired
def revoke_all(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    # TODO: Revoke tokens
    return redirect("/oauth/clients")

@oauth.route("/oauth/clients/<secret>/delete")
@loginrequired
def delete_client(secret):
    client = OAuthClient.query.filter(OAuthClient.client_secret == secret).first()
    if not client:
        abort(404)
    db.delete(client)
    db.commit()
    return redirect("/oauth/clients")

@oauth.route("/oauth/authorize")
@loginrequired
def authorize():
    client_id = request.args.get("client_id")
    if not client_id:
        return render_template("oauth-authorize.html", errors="Missing client_id in URL")
    client = OAuthClient.query.filter(OAuthClient.client_id == client_id).first()
    if not client:
        abort(404)
    return render_template("oauth-authorize.html", client=client)

@oauth.route("/oauth/authorize", methods=["POST"])
@loginrequired
def authorize_POST():
    client_id = request.form.get("client_id")
    if not client_id:
        return render_template("oauth-authorize.html", errors="Missing client_id")
    client = OAuthClient.query.filter(OAuthClient.client_id == client_id).first()
    if not client:
        abort(404)
    salt = os.urandom(40)
    code = hashlib.sha256(salt).hexdigest()[:10]
    r = redis.Redis()
    r.setex("oauth.exchange.client." + code, client_id, 600) # expires in 10 minutes
    r.setex("oauth.exchange.user." + code, current_user.id, 600)
    params = {
        "code": code
    }
    parts = list(urllib.parse.urlparse(client.redirect_uri))
    parsed = urllib.parse.parse_qs(parts[4])
    parsed.update(params)
    parts[4] = urllib.parse.urlencode(parsed)
    return redirect(urllib.parse.urlunparse(parts))

@oauth.route("/oauth/exchange", methods=["POST"])
@json_output
def exchange():
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    code = request.form.get("code")
    if not client_id:
        return { "error": "Missing client_id" }, 400

    client = OAuthClient.query.filter(OAuthClient.client_id == client_id).first()
    if not client:
        return { "error": "Unknown client" }, 404

    if client.client_secret != client_secret:
        return { "error": "Incorrect client secret" }, 401

    r = redis.Redis()
    _client_id = r.get("oauth.exchange.client." + code)
    user_id = r.get("oauth.exchange.user." + code)
    if not client_id or not user_id:
        return { "error": "Unknown or expired exchange code" }, 404

    _client_id = _client_id.decode("utf-8")
    user_id = int(user_id.decode("utf-8"))
    user = User.query.filter(User.id == user_id).first()
    if not user or _client_id != client.client_id:
        return { "error": "Unknown or expired exchange code" }, 404

    token = OAuthToken.query.filter(OAuthToken.client == client, OAuthToken.user == user).first()
    if not token:
        token = OAuthToken(user, client)
        db.add(token)
        db.commit()

    r.delete("oauth.exchange.client." + code)
    r.delete("oauth.exchange.user." + code)
    return { "token": token.token }

@oauth.route("/oauth/tokens")
@loginrequired
def tokens():
    return render_template("oauth-tokens.html")

@oauth.route("/oauth/tokens/<token>/revoke")
@loginrequired
def revoke_token(token):
    token = OAuthToken.query.filter(OAuthToken.token == token).first()
    if not token:
        abort(404)
    if token.user != current_user:
        abort(404)
    db.delete(token)
    db.commit()
    return redirect("/oauth/tokens")
