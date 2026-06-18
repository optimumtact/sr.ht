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

    content_hash = get_content_hash(f)

    existing = Upload.query.filter(Upload.hash == content_hash).first()
    if existing:
        return {
            "success": True,
            "hash": existing.hash,
            "shorthash": existing.shorthash,
            "url": file_link(existing.path),
        }

    upload = Upload()
    upload.user = user
    upload.hash = content_hash
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
        "url": file_link(upload.path),
    }


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
    # Backward-compatible wrapper kept for any external imports.
    digest = get_content_hash(f)
    return digest, ""


def get_content_hash(f):
    # Single-pass, URL-safe digest for stable URLs and dedupe.
    f.seek(0)
    digest = hashlib.blake2b(digest_size=20)
    while chunk := f.read(1024 * 1024):
        digest.update(chunk)
    f.seek(0)
    return base64.urlsafe_b64encode(digest.digest()).decode("ascii").rstrip("=")


def extension(filename: str) -> str:
    return Path(filename).suffix.lower()
