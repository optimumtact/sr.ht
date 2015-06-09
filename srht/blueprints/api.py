from flask import Blueprint, render_template, abort, request, redirect, session, url_for, send_file
from flask.ext.login import current_user, login_user, logout_user
from sqlalchemy import desc, or_, and_
from srht.objects import *
from srht.common import *
from srht.config import _cfg
from srht.email import send_invite

from datetime import datetime
import hashlib
import binascii
import os
import zipfile
import urllib
import re
import json
import locale
import shlex
import math

encoding = locale.getdefaultlocale()[1]
api = Blueprint('api', __name__, template_folder='../../templates')

@api.route("/api/approve/<id>", methods=["POST"])
@adminrequired
@with_session
@json_output
def approve(id):
    u = User.query.filter(User.id == id).first()
    u.approved = True
    u.approvalDate = datetime.now()
    db.commit()
    send_invite(u)
    return { "success": True }

@api.route("/api/reject/<id>", methods=["POST"])
@adminrequired
@with_session
def reject(id):
    u = User.query.filter(User.id == id).first()
    u.rejected = True
    db.commit()
    # TODO: Send rejection emails?
    return { "success": True }

@api.route("/api/upload", methods=["POST"])
@json_output
def upload():
    key = request.form.get('key')
    f = request.files.get('file')
    if not key:
        return { "error": "API key is required" }, 401
    if not f:
        return { "error": "File is required" }, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return { "error": "API key not recognized" }, 403
    filename = ''.join(c for c in f.filename if c.isalnum() or c == '.')
    upload = Upload()
    upload.user = user
    upload.hash = get_hash(f)
    len = 3
    shorthash = upload.hash[:len]
    while any(Upload.query.filter(Upload.shorthash == shorthash)):
        len += 1
        shorthash = upload.hash[:len]
    upload.shorthash = shorthash
    upload.path = os.path.join(upload.shorthash + "." + extension(filename))

    f.seek(0)
    f.save(os.path.join(_cfg("storage"), upload.path))

    db.add(upload)
    db.commit()
    return {
        "success": True,
        "hash": upload.hash,
        "shorthash": upload.shorthash,
        "url": _cfg("protocol") + "://" + _cfg("domain") + "/" + upload.path
    }

def get_hash(f):
    f.seek(0)
    return hashlib.md5(f.read()).hexdigest()

extension = lambda f: f.rsplit('.', 1)[1].lower()
