import hashlib
import os
from datetime import datetime
from pathlib import Path

import bcrypt
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Unicode,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from srht.config import _cfg

from .database import db


class Upload(db.Model):
    __tablename__ = "upload"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", backref=backref("upload", order_by=id, lazy="dynamic"))
    hash = Column(String, nullable=False)
    shorthash = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    path = Column(String, nullable=False)
    created = Column(DateTime)
    original_name = Column(Unicode(512))
    hidden = Column(Boolean())

    def __init__(self):
        self.created = datetime.now()
        self.hidden = False

    def get_storage_path(self):
        storage = _cfg("storage")
        if storage:
            return Path(os.path.join(storage, self.path))
        raise Exception("Invalid storage directory")

    def get_thumbnail_path(self):
        storage = _cfg("storage")
        if storage:
            thumbnaildir = Path(os.path.join(storage, "thumbnails"))
            return thumbnaildir
        raise Exception("Invalid storage directory")

    def save_file(self, f):
        # In case it was read from
        f.seek(0)
        f.save(self.get_storage_path())


class Job(db.Model):
    __tablename__ = "job"
    id = Column(Integer, primary_key=True)
    priority = Column(Integer, default=100)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    tasktype: Mapped[int] = mapped_column(Integer, nullable=False)
    pickledclass: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class PendingJob(db.Model):
    """Just a queue of jobs that need handling by a processor (cron etc)"""

    __tablename__ = "pending_job"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job.id"))
    job = relationship("Job", backref=backref("message", order_by=id, lazy="dynamic"))
    created = Column(DateTime)

    def __init__(self, job: Job):
        self.created = datetime.now()
        self.job_id = job.id


class User(db.Model):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
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
        self.password = bcrypt.hashpw(password.encode("UTF-8"), bcrypt.gensalt()).decode("UTF-8")

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
        return "<User %r>" % self.username

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
