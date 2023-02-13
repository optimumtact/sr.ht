from sqlalchemy import Column, Integer, String, Unicode, Boolean, DateTime
from sqlalchemy import ForeignKey, Table, UnicodeText, Text, text
from sqlalchemy.orm import relationship, backref
from .database import db

from datetime import datetime
import bcrypt
import os
import hashlib

class Upload(db.Model):
    __tablename__ = 'upload'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref=backref('upload', order_by=id, lazy='dynamic'))
    hash = Column(String, nullable=False)
    shorthash = Column(String, nullable=False)
    path = Column(String, nullable=False)
    created = Column(DateTime)
    original_name = Column(Unicode(512))
    hidden = Column(Boolean())

    def __init__(self):
        self.created = datetime.now()
        self.hidden = False

class User(db.Model):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    username = Column(String(128), nullable=False, index=True)
    email = Column(String(256), nullable=False, index=True)
    admin = Column(Boolean())
    password = Column(String)
    created = Column(DateTime)
    approvalDate = Column(DateTime)
    passwordReset = Column(String(128))
    passwordResetExpiry = Column(DateTime)
    apiKey = Column(String(128))
    comments = Column(Unicode(512))
    approved = Column(Boolean())
    rejected = Column(Boolean())

    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode('UTF-8'), bcrypt.gensalt()).decode('UTF-8')

    def generate_api_key(self):
        salt = os.urandom(40)
        self.apiKey = hashlib.sha256(salt).hexdigest()

    def __init__(self, username, email, password):
        self.email = email
        self.username = username
        self.admin = False
        self.approved = False
        self.rejected = False
        self.created = datetime.now()
        self.generate_api_key()
        self.set_password(password)

    def __repr__(self):
        return '<User %r>' % self.username

    # Flask.Login stuff
    # We don't use most of these features
    def is_authenticated(self):
        return True
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return self.username
