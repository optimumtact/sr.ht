from flask import Blueprint, render_template, abort, request, redirect, session, url_for, send_file
from flask_login import current_user, login_user, logout_user
from sqlalchemy import desc, or_, and_
from srht.objects import *
from srht.common import *
from srht.config import _cfg
from srht.email import send_invite, send_rejection

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
import base64

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
    db.session.commit()
    send_invite(u)
    return { "success": True }

@api.route("/api/reject/<id>", methods=["POST"])
@adminrequired
@with_session
@json_output
def reject(id):
    u = User.query.filter(User.id == id).first()
    u.rejected = True
    db.session.commit()
    send_rejection(u)
    return { "success": True }

@api.route("/api/resetkey", methods=["POST"])
@json_output
def reset_key():
    key = request.form.get('key')
    if not key:
        return { "error": "Maybe you should include the actual key, dumbass" }, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return { "error": "API key not recognized" }, 403
    user.generate_api_key()
    db.session.commit()
    return { "key": user.apiKey }

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
    hash = get_hash(f)
    upload.hash = hash
    existing = Upload.query.filter(Upload.hash == hash).first()
    if existing:
        db.session.rollback()#file already exists, end this session
        return {
            "success": True,
            "hash": existing.hash,
            "shorthash": existing.shorthash,
            "url": file_link(existing.path)
        }
    len = 4
    shorthash = upload.hash[:len]
    while any(Upload.query.filter(Upload.shorthash == shorthash)):
        len += 1
        shorthash = upload.hash[:len]
    upload.shorthash = shorthash
    upload.path = os.path.join(upload.shorthash + "." + extension(filename))
    upload.original_name = f.filename

    f.seek(0)
    f.save(os.path.join(_cfg("storage"), upload.path))

    if upload.shorthash is None:
        return {
            "success": False,
            "error": "Upload interrupted"
        }

    db.session.add(upload)
    db.session.commit()
    return {
        "success": True,
        "hash": upload.hash,
        "shorthash": upload.shorthash,
        "url": _cfg("protocol") + "://" + _cfg("domain") + "/" + upload.path
    }

@api.route("/api/disown", methods=["POST"])
@json_output
def disown():
    key = request.form.get('key')
    filename = request.form.get('filename')
    if not key:
        return { "error": "API key is required" }, 401
    if not filename:
        return { "error": "File is required" }, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return { "error": "API key not recognized" }, 403
    Upload.query.filter_by(path=filename).first().hidden = True
    db.session.commit()
    return {
            "success": True,
            "filename": filename
    }

@api.route("/api/delete", methods=["POST"])
@json_output
def delete():
    key = request.form.get('key')
    filename = request.form.get('filename')
    if not key:
        return { "error": "API key is required" }, 401
    if not filename:
        return { "error": "File is required" }, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return { "error": "API key not recognized" }, 403
    file = Upload.query.filter_by(path=filename).first()
    if file and (user.admin or user == file.user):
        db.session.delete(file)
        os.remove(os.path.join(_cfg("storage"), file.path))
        db.session.commit()
        return {
                "success": True,
                "filename": filename
        }

    else:
    	return { "error": "File doesn't exist or is not belonging to you" }, 400

def get_hash(f):
    f.seek(0)
    return base64.urlsafe_b64encode(hashlib.md5(f.read()).digest()).decode("utf-8")

extension = lambda f: f.rsplit('.', 1)[-1].lower()
