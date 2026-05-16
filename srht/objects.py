import hashlib
import os
from datetime import datetime
from pathlib import Path

import bcrypt
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    JSON,
    UniqueConstraint,
    Text,
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
    tags = relationship(
        "Tag",
        back_populates="upload",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    hash = Column(String, nullable=False)
    shorthash = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    caption_complete = Column(Boolean, nullable=False, default=False)
    path = Column(String, nullable=False)
    created = Column(DateTime)
    original_name = Column(Unicode(512))
    hidden = Column(Boolean())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.created is None:
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
    created = Column(DateTime)
    timeclaimed = Column(DateTime)
    processid = Column(Integer)
    priority = Column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    tasktype: Mapped[int] = mapped_column(Integer, nullable=False)
    pickledclass: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    taskmetadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.created is None:
            self.created = datetime.now()

    def save_task_state(
        self,
        status: int,
        tasktype: int,
        task_data: dict | None = None,
        version: int | None = None,
    ):
        self.status = status
        self.tasktype = tasktype
        if version is not None:
            self.version = version
        self.taskmetadata = task_data or {}
        self.timeclaimed = None
        self.processid = None
        # Keep legacy column non-null while task persistence is JSON-based.
        self.pickledclass = b""
        db.session.add(self)
        db.session.commit()


class TaskSchedule(db.Model):
    __tablename__ = "task_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tasktype: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_run_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("tasktype", name="uq_task_schedule_tasktype"),)

    DEFAULT_CRON = "*/5 * * * *"

    def __init__(
        self,
        tasktype: int,
        cron_expression: str | None = None,
        enabled: bool = True,
        next_run_time: datetime | None = None,
        last_run_time: datetime | None = None,
    ):
        now = datetime.now()
        self.tasktype = tasktype
        self.cron_expression = cron_expression or self.DEFAULT_CRON
        self.enabled = enabled
        self.created = now
        self.updated = now
        self.last_run_time = last_run_time
        self.next_run_time = next_run_time or self.calculate_next_run(now)

    @staticmethod
    def _cron_base_time(base_time: datetime | None = None) -> datetime:
        return base_time or datetime.now()

    def calculate_next_run(self, base_time: datetime | None = None) -> datetime:
        from croniter import croniter

        return croniter(self.cron_expression, self._cron_base_time(base_time)).get_next(datetime)

    def advance(self, base_time: datetime | None = None):
        now = self._cron_base_time(base_time)
        self.last_run_time = now
        self.next_run_time = self.calculate_next_run(self.next_run_time or now)
        self.updated = now

    @classmethod
    def default_schedules(cls):
        from srht.tasks.basetask import TaskType

        return [
            (int(TaskType.BATCH_CAPTIONS), cls.DEFAULT_CRON),
            (int(TaskType.BATCH_TAGS), cls.DEFAULT_CRON),
        ]

    @classmethod
    def ensure_defaults(cls):
        now = datetime.now()
        created = False
        for tasktype, cron_expression in cls.default_schedules():
            existing = cls.query.filter(cls.tasktype == tasktype).one_or_none()
            if existing is None:
                schedule = cls(tasktype=tasktype, cron_expression=cron_expression)
                schedule.created = now
                schedule.updated = now
                db.session.add(schedule)
                created = True
        if created:
            db.session.commit()
        return cls.query.order_by(cls.tasktype.asc()).all()


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
    suspended = Column(Boolean(), nullable=False, default=False)
    ai_opt_in = Column(Boolean(), nullable=False, default=False)
    password = Column(String)
    created = Column(DateTime)
    passwordReset = Column(String(128))
    passwordResetExpiry = Column(DateTime)
    apiKey = Column(String(128))
    comments = Column(Unicode(512))

    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode("UTF-8"), bcrypt.gensalt()).decode("UTF-8")

    def check_password(self, password: str) -> bool:
        if not self.password:
            return False
        return bcrypt.checkpw(password.encode("UTF-8"), self.password.encode("UTF-8"))

    def generate_api_key(self):
        salt = os.urandom(40)
        self.apiKey = hashlib.sha256(salt).hexdigest()

    def __init__(self, username, email, password):
        self.email = email
        self.username = username
        self.admin = False
        self.suspended = False
        self.ai_opt_in = False
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


class Tag(db.Model):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploadid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upload = relationship("Upload", back_populates="tags")
    tag: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (UniqueConstraint("uploadid", "tag", name="uq_tags_uploadid_tag"),)

    def __init__(self, uploadid: int, tag: str, relevance: float = 0.0):
        self.uploadid = uploadid
        self.tag = tag
        self.relevance = relevance
        self.created = datetime.utcnow()


class JobLog(db.Model):
    __tablename__ = "job_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job.id"), nullable=False, index=True)
    job = relationship("Job", backref=backref("logs", order_by=id, lazy="dynamic"))
    created = Column(DateTime, nullable=False)
    level = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)

    def __init__(self, job_id: int, level: int, message: str):
        self.job_id = job_id
        self.created = datetime.utcnow()
        self.level = level
        self.message = message
