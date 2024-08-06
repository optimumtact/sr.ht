from flask import jsonify, redirect, request, Response, abort
from flask_login import current_user
from functools import wraps
from srht.database import db
from srht.config import _cfg
from pathlib import Path
import magic
import json
import urllib
from PIL import Image
from moviepy.video.io.VideoFileClip import VideoFileClip

def is_valid_image_pillow(file_name: Path) -> bool:
    """Check if an image is a valid iamge

    Args:
        file_name (Path): The file path to check

    Returns:
        bool: True if the image is a valid image
    """
    try:
        with Image.open(file_name) as img:
            img.verify()
            return True
    except (IOError, SyntaxError):
        return False


def generate_thumbnail(uploaded_file_path: Path, thumbnail_path: Path, size=(500, 500)) -> Path:
    """Generate a thumbnail from a given file path
    will attempt to guess the media type and use PIL or pyvideo as needed

    Args:
        image_path (Path): The image path
        thumbnail_path (Path): The thumbnail directory
        size (tuple, optional): The image size. Defaults to (128, 128).

    Returns:
        bool: True if the thumbnail was created successfully.
    """
    thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.name)
    guessed_mimetype = magic.from_file(uploaded_file_path, mime=True)
    if guessed_mimetype is not None:
        type, extension = guessed_mimetype.split('/')
        if type == "image":
            # Does pillow recognise it, otherwise fall through to the default
            if is_valid_image_pillow(uploaded_file_path):
                return generate_image_thumbnail(uploaded_file_path, thumbnail_file_path, size)
        if type == "video":
            # We want to save the first frame as a png
            thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem+".png")
            return generate_video_thumbnail(uploaded_file_path, thumbnail_file_path, size)
    # Unknown file type we want to save as a png of the same name
    thumbnail_file_path = thumbnail_path.joinpath(uploaded_file_path.stem+".png")
    return generate_blank_thumbnail(uploaded_file_path, thumbnail_file_path, size)


def generate_blank_thumbnail(uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)) -> Path:
    color = (255, 255, 255, 0)
    image = Image.new("RGBA", (size[0], size[1]), color)
    image.save(thumbnail_file_path)
    return thumbnail_file_path
    

def generate_video_thumbnail(uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)) -> Path:
    print(f"Generating video thumbnail to {thumbnail_file_path}")
    video = VideoFileClip(uploaded_file_path.as_posix())
    video.save_frame(thumbnail_file_path, t=1.00)
    # Now we defer to the thumbnail generation
    generate_image_thumbnail(thumbnail_file_path, thumbnail_file_path, size)
    return thumbnail_file_path

def generate_image_thumbnail(uploaded_file_path: Path, thumbnail_file_path: Path, size=(128, 128)) -> Path:
    with Image.open(uploaded_file_path) as img:
        img.thumbnail(size)
        img.save(thumbnail_file_path)
        return thumbnail_file_path


def firstparagraph(text):
    try:
        para = text.index("\n\n")
        return text[: para + 2]
    except:
        try:
            para = text.index("\r\n\r\n")
            return text[: para + 4]
        except:
            return text


def with_session(f):
    @wraps(f)
    def go(*args, **kw):
        try:
            ret = f(*args, **kw)
            db.commit()
            return ret
        except:
            db.rollback()
            db.close()
            raise

    return go


def loginrequired(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user or not current_user.approved:
            return redirect("/login?return_to=" + urllib.parse.quote_plus(request.url))
        else:
            return f(*args, **kwargs)

    return wrapper


def adminrequired(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user or not current_user.approved:
            return redirect("/login?return_to=" + urllib.parse.quote_plus(request.url))
        else:
            if not current_user.admin:
                abort(401)
            return f(*args, **kwargs)

    return wrapper


def json_output(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        def jsonify_wrap(obj):
            jsonification = json.dumps(obj)
            return Response(jsonification, mimetype="application/json")

        result = f(*args, **kwargs)
        if isinstance(result, tuple):
            return jsonify_wrap(result[0]), result[1]
        if isinstance(result, dict):
            return jsonify_wrap(result)
        if isinstance(result, list):
            return jsonify_wrap(result)

        # This is a fully fleshed out response, return it immediately
        return result

    return wrapper


def cors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        res = f(*args, **kwargs)
        if request.headers.get("x-cors-status", False):
            if isinstance(res, tuple):
                json_text = res[0].data
                code = res[1]
            else:
                json_text = res.data
                code = 200

            o = json.loads(json_text)
            o["x-status"] = code

            return jsonify(o)

        return res

    return wrapper


def file_link(path):
    return _cfg("protocol") + "://" + _cfg("domain") + "/" + path


def disown_link(path):
    return _cfg("protocol") + "://" + _cfg("domain") + "/disown?filename=" + path


def delete_link(path):
    returnto = urllib.parse.quote_plus(_cfg("protocol") + "://" + _cfg("domain") + "/uploads")
    return (
        _cfg("protocol")
        + "://"
        + _cfg("domain")
        + "/delete?filename="
        + path
        + "&return_to="
        + returnto
    )


def admin_delete_link(path):
    returnto = urllib.parse.quote_plus(_cfg("protocol") + "://" + _cfg("domain") + "/admin_uploads")
    return (
        _cfg("protocol")
        + "://"
        + _cfg("domain")
        + "/delete?filename="
        + path
        + "&return_to="
        + returnto
    )
