from flask import Blueprint, render_template, abort, request, redirect, session, url_for, send_file
from flask.ext.login import current_user, login_user, logout_user
from sqlalchemy import desc, or_, and_
from srht.objects import *
from srht.common import *
from srht.config import _cfg
from srht.email import send_invite

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

@api.route("/api/upload")
def upload():
    # TODO
    pass
