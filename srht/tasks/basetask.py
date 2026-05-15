import logging
import os
from enum import IntEnum
import traceback

from sqlalchemy import text

from srht.database import db
from srht.objects import Job, JobLog


class TaskStatus(IntEnum):
    CREATED = 1
    FAILED = 2
    COMPLETE = 3
    QUEUED = 4
    CLAIMED = 5


class TaskType(IntEnum):
    BASE = 0
    THUMBNAIL = 1
    CAPTION_TAGS = 2


class Task:
    """An executable task"""

    type = TaskType.BASE
    LATEST_VERSION = 2
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "type"):
            Task._registry[int(cls.type)] = cls

    def log_message(self, message, log_level=logging.INFO):
        if self.logger:
            self.logger.log(log_level, f"Job {self.jobid}: {message}")
        try:
            entry = JobLog(self.jobid, log_level, message)
            db.session.add(entry)
            db.session.commit()
        except Exception:
            pass

    def __init__(self, job: Job | None = None, failure_count: int = 0):
        self.logger = None
        self.type = self.__class__.type
        self.failure_count = failure_count
        if job is None:
            self.job = Job()
            self.version = Task.LATEST_VERSION
            self.status = TaskStatus.CREATED
            self.job.save_task_state(
                status=int(self.status),
                tasktype=int(self.type),
                task_data=self.get_as_json(),
                version=self.version,
            )
        else:
            self.job = job
            self.version = job.version
            self.status = TaskStatus(job.status)
        self.jobid = self.job.id

    def queue(self):
        self.status = TaskStatus.QUEUED
        self.save_to_db()

    def requeue(self):
        self.failure_count = 0
        self.status = TaskStatus.QUEUED
        self.save_to_db()

    def save_to_db(self):
        self.job.save_task_state(
            status=int(self.status),
            tasktype=int(self.type),
            task_data=self.get_as_json(),
            version=self.version,
        )

    def run(self, logger=None):
        self.logger = logger
        self.log_message(f"Executing job {self.jobid} of type {TaskType(self.type).name}")
        try:
            self.execute()
            self.complete()
        except Exception as e:
            self.failure_count += 1
            self.log_message(f"Task failure {self.failure_count}", log_level=logging.ERROR)

            error_traceback = traceback.format_exc()
            self.log_message(
                f"Exception: {e}, Stack trace: {error_traceback}", log_level=logging.ERROR
            )
            if self.failure_count > 5:
                self.log_message(
                    "Task failed too many times, marking as failed", log_level=logging.ERROR
                )
                # We flag ourself as failed and do not requeue
                self.fail()
            else:
                # We want to keep trying
                self.queue()

    def fail(self):
        self.status = TaskStatus.FAILED
        self.save_to_db()

    def complete(self):
        self.status = TaskStatus.COMPLETE
        self.save_to_db()

    def execute(self):
        pass

    def get_as_json(self) -> dict:
        return {"failure_count": self.failure_count}

    @staticmethod
    def get_task(jobid: int) -> "Task":
        job = Job.query.filter(Job.id == jobid).one()
        task_class = Task._registry.get(int(job.tasktype))
        if task_class is None:
            raise Exception(f"No task class registered for tasktype={job.tasktype}")
        task_data = job.taskmetadata or {}
        task = task_class(job=job, **task_data)
        if not isinstance(task, Task):
            raise Exception("Task constructor did not produce a Task subclass")
        return task

    @staticmethod
    def get_next_task() -> "Task | None":
        dialect_name = db.session.bind.dialect.name if db.session.bind else ""
        if dialect_name == "postgresql":
            sql = text("""
                WITH next_job AS (
                    SELECT id
                    FROM job
                    WHERE status = :queued_status
                    ORDER BY priority ASC, created ASC, id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE job
                SET status = :claimed_status,
                    processid = :process_id,
                    timeclaimed = NOW()
                FROM next_job
                WHERE job.id = next_job.id
                RETURNING job.id;
                """)
        else:
            # SQLite does not support FOR UPDATE SKIP LOCKED.
            sql = text("""
                UPDATE job
                SET status = :claimed_status,
                    processid = :process_id,
                    timeclaimed = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id
                    FROM job
                    WHERE status = :queued_status
                    ORDER BY priority ASC, created ASC, id ASC
                    LIMIT 1
                )
                AND status = :queued_status
                RETURNING id;
                """)

        result = db.session.execute(
            sql,
            {
                "queued_status": int(TaskStatus.QUEUED),
                "claimed_status": int(TaskStatus.CLAIMED),
                "process_id": os.getpid(),
            },
        ).fetchone()
        if result:
            jobid = int(result[0])
            task = Task.get_task(jobid)
            db.session.commit()
            return task

        return None
