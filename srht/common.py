from flask import session, jsonify, redirect, request, Response, abort
from flask.ext.login import current_user
from werkzeug.utils import secure_filename
from functools import wraps
from srht.objects import User
from srht.database import db, Base
from srht.config import _cfg

import json
import urllib
import requests
import xml.etree.ElementTree as ET
import hashlib

def firstparagraph(text):
    try:
        para = text.index("\n\n")
        return text[:para + 2]
    except:
        try:
            para = text.index("\r\n\r\n")
            return text[:para + 4]
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
            return Response(jsonification, mimetype='application/json')

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
        if request.headers.get('x-cors-status', False):
            if isinstance(res, tuple):
                json_text = res[0].data
                code = res[1]
            else:
                json_text = res.data
                code = 200

            o = json.loads(json_text)
            o['x-status'] = code

            return jsonify(o)

        return res

    return wrapper

def file_link(path):
    return _cfg("protocol") + "://" + _cfg("domain") + "/" + path

def disown_link(path):
    return _cfg("protocol") + "://"  + _cfg("domain") + "/disown?filename=" + path
