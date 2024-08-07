import base64
import hashlib
import locale
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request

from srht.common import (
    adminrequired,
    file_link,
    generate_thumbnail,
    json_output,
    with_session,
)
from srht.config import _cfg
from srht.database import db
from srht.email import send_invite, send_rejection
from srht.objects import Upload, User
from srht.task_queue import queue_thumbnail_job

encoding = locale.getdefaultlocale()[1]
api = Blueprint("api", __name__, template_folder="../../templates")


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
    return {"success": True}


@api.route("/api/reject/<id>", methods=["POST"])
@adminrequired
@with_session
@json_output
def reject(id):
    u = User.query.filter(User.id == id).first()
    u.rejected = True
    db.session.commit()
    send_rejection(u)
    return {"success": True}


@api.route("/api/resetkey", methods=["POST"])
@json_output
def reset_key():
    key = request.form.get("key")
    if not key:
        return {"error": "Maybe you should include the actual key, dumbass"}, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return {"error": "API key not recognized"}, 403
    user.generate_api_key()
    db.session.commit()
    return {"key": user.apiKey}


@api.route("/api/upload", methods=["POST"])
@json_output
def upload():
    key = request.form.get("key")
    f = request.files.get("file")
    if not key:
        return {"error": "API key is required"}, 401
    if not f:
        return {"error": "File is required"}, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return {"error": "API key not recognized"}, 403
    filename = "".join(c for c in f.filename if c.isalnum() or c == ".")
    upload = Upload()
    upload.user = user
    hash = get_hash(f)
    upload.hash = hash
    existing = Upload.query.filter(Upload.hash == hash).first()
    if existing:
        db.session.rollback()  # file already exists, end this session
        return {
            "success": True,
            "hash": existing.hash,
            "shorthash": existing.shorthash,
            "url": file_link(existing.path),
        }
    upload.path = os.path.join(upload.hash + extension(filename))
    upload.original_name = filename

    # Save files to the directories as required
    savefile = upload.get_storage_path()
    # thumbnaildir = Path(os.path.join(_cfg("storage"), "thumbnails"))
    # Rewind the file and save it to the directory
    f.seek(0)
    f.save(savefile)
    # thumbnail = generate_thumbnail(savefile, thumbnaildir)
    # Save the thumbnail name
    # upload.thumbnail = 'thumbnails'+'/'+thumbnail.name

    if upload.hash is None:
        return {"success": False, "error": "Upload interrupted"}

    db.session.add(upload)
    db.session.commit()
    queue_thumbnail_job(upload)
    return {
        "success": True,
        "hash": upload.hash,
        "url": _cfg("protocol") + "://" + _cfg("domain") + "/" + upload.path,
    }


@api.route("/api/disown", methods=["POST"])
@json_output
def disown():
    key = request.form.get("key")
    filename = request.form.get("filename")
    if not key:
        return {"error": "API key is required"}, 401
    if not filename:
        return {"error": "File is required"}, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return {"error": "API key not recognized"}, 403
    Upload.query.filter_by(path=filename).first().hidden = True
    db.session.commit()
    return {"success": True, "filename": filename}


@api.route("/api/delete", methods=["POST"])
@json_output
def delete():
    key = request.form.get("key")
    filename = request.form.get("filename")
    if not key:
        return {"error": "API key is required"}, 401
    if not filename:
        return {"error": "File is required"}, 400
    user = User.query.filter(User.apiKey == key).first()
    if not user:
        return {"error": "API key not recognized"}, 403
    file = Upload.query.filter_by(path=filename).first()
    if file and (user.admin or user == file.user):
        db.session.delete(file)
        os.remove(os.path.join(_cfg("storage"), file.path))
        os.remove(os.path.join(_cfg("storage"), file.thumbnail))
        db.session.commit()
        return {"success": True, "filename": filename}

    else:
        return {"error": "File doesn't exist or is not belonging to you"}, 400


def get_hash(f):
    f.seek(0)
    # TODO we need to swap this to sha1, but that means we need to rencode all existing hashes
    return base64.urlsafe_b64encode(hashlib.md5(f.read()).digest()).decode("utf-8")


def extension(filename: str) -> str:
    return Path(filename).suffix.lower()
