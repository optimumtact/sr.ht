from flask import Blueprint, render_template, abort, request, redirect, session, url_for, send_file
from flask.ext.login import current_user, login_user, logout_user
from sqlalchemy import desc, or_, and_
from srht.objects import *
from srht.common import *
from srht.config import _cfg

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
html = Blueprint('html', __name__, template_folder='../../templates')

@html.route("/")
def index():
    return render_template("index.html")

@html.route("/register", methods=['POST'])
def register():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    errors = list()
    if not email:
        errors.append('Email is required.')
    else:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append('Please use a valid email address.')
        if User.query.filter(User.username.ilike(username)).first():
            errors.append('This username is already in use.')
    if not username:
        errors.append('Username is required.')
    else:
        if not re.match(r"^[A-Za-z0-9_]+$", username):
            errors.append('Usernames are letters, numbers, underscores only.')
        if len(username) < 3 or len(username) > 24:
            errors.append('Username must be between 3 and 24 characters.')
        if User.query.filter(User.username.ilike(username)).first():
            errors.append('This username is already in use.')
    if not password:
        errors.append('Password is required.')
    else:
        if len(password) < 5 or len(password) > 256:
            errors.append('Password must be between 5 and 256 characters.')
    if len(errors) != 0:
        return render_template("index.html", username=username, email=email, errors=errors)
    # All good, create an account for them
    user = User(username, email, password)
    db.add(user)
    db.commit()
    return render_template("index.html", registered=True)

@html.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user:
            return redirect("/")
        reset = request.args.get('reset') == '1'
        return render_template("login.html", **{ 'return_to': request.args.get('return_to'), 'reset': reset })
    else:
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember-me')
        if remember == "on":
            remember = True
        else:
            remember = False
        user = User.query.filter(User.username.ilike(username)).first()
        if not user:
            return render_template("login.html", **{ "username": username, "errors": 'Your username or password is incorrect.' })
        if user.confirmation != '' and user.confirmation != None:
            return redirect("/pending")
        if not bcrypt.checkpw(password, user.password):
            return render_template("login.html", **{ "username": username, "errors": 'Your username or password is incorrect.' })
        login_user(user, remember=remember)
        if 'return_to' in request.form and request.form['return_to']:
            return redirect(urllib.parse.unquote(request.form.get('return_to')))
        return redirect("/")

@html.route("/logout")
@loginrequired
def logout():
    logout_user()
    return redirect("/")

@html.route("/pending")
def pending():
    return render_template("pending.html")
