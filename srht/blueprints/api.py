import base64
import hashlib
import os
from pathlib import Path

from flask import Blueprint, request

from srht.common import adminrequired, file_link, json_output, with_session
from srht.config import _cfg
from srht.database import db
from srht.objects import Upload, User
from srht.tasks import GenerateImageThumbnail

api = Blueprint("api", __name__, template_folder="../../templates")


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
    
    sha256_hash, md5_hash = get_hashes(f)
    
    # Check for existing using either the new SHA256 or legacy MD5
    existing = Upload.query.filter((Upload.hash == sha256_hash) | (Upload.hash == md5_hash)).first()
    if existing:
        return {
            "success": True,
            "hash": existing.hash,
            "shorthash": existing.shorthash,
            "url": file_link(existing.path),
        }

    upload = Upload()
    upload.user = user
    upload.hash = sha256_hash
    upload.path = os.path.join(upload.hash + extension(filename))
    upload.original_name = filename

    # Save files to the directories as required
    upload.save_file(f)

    if upload.hash is None:
        return {"success": False, "error": "Upload interrupted"}

    db.session.add(upload)
    db.session.commit()
    task = GenerateImageThumbnail(upload.id)
    task.queue()
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
    upload = Upload.query.filter_by(path=filename, user_id=user.id).first()
    if not upload:
        return {"error": "File not found or does not belong to you"}, 403
    upload.hidden = True
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
        full_path = os.path.join(_cfg("storage"), file.path)
        if os.path.exists(full_path):
            os.remove(full_path)
        if file.thumbnail:
            thumb_path = os.path.join(_cfg("storage"), file.thumbnail)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        db.session.commit()
        return {"success": True, "filename": filename}

    else:
        return {"error": "File doesn't exist or is not belonging to you"}, 400


def get_hashes(f):
    f.seek(0)
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    while chunk := f.read(8192):
        sha256_hash.update(chunk)
        md5_hash.update(chunk)
    f.seek(0)
    
    return (
        base64.urlsafe_b64encode(sha256_hash.digest()).decode("utf-8"),
        base64.urlsafe_b64encode(md5_hash.digest()).decode("utf-8")
    )


def extension(filename: str) -> str:
    return Path(filename).suffix.lower()

