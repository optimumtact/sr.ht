import logging
import pickle
from enum import IntEnum

from sqlalchemy import text

from srht.database import db
from srht.objects import Job, JobLog, PendingJob


class TaskStatus(IntEnum):
    CREATED = 1
    FAILED = 2
    COMPLETE = 3
    QUEUED = 4


class TaskType(IntEnum):
    BASE = 0
    THUMBNAIL = 1


class Task:
    """An executable task"""

    type = TaskType.BASE

    def log_message(self, message, log_level=logging.INFO):
        if self.logger:
            self.logger.log(log_level, f"Job {self.jobid}: {message}")
        try:
            entry = JobLog(self.jobid, log_level, message)
            db.session.add(entry)
            db.session.commit()
        except Exception:
            pass

    def __init__(self):
        self.logger = None
        self.job = Job()
        self.status = TaskStatus.CREATED
        self.job.status = int(self.status)
        self.job.pickledclass = b""
        self.type = TaskType.BASE
        self.job.tasktype = self.type
        db.session.add(self.job)
        db.session.commit()
        self.jobid = self.job.id
        self.failure_count = 0

    def queue(self):
        self.status = TaskStatus.QUEUED
        self.save_to_db()
        pending = PendingJob(self.job)
        db.session.add(pending)
        db.session.commit()

    def requeue(self):
        print(f"resetting {self.failure_count} to 0 and re-queuing")
        self.failure_count = 0
        self.status = TaskStatus.QUEUED
        self.save_to_db()
        pending = PendingJob(self.job)
        db.session.add(pending)
        db.session.commit()

    def save_to_db(self):
        self.job.pickledclass = pickle.dumps(self)
        self.job.status = self.status
        self.job.tasktype = self.type
        db.session.add(self.job)
        db.session.commit()

    def run(self, logger):
        self.logger = logger
        self.log_message(f"Executing job {self.jobid} of type {TaskType(self.type).name}")
        try:
            self.execute()
            self.complete()
        except Exception as e:
            self.failure_count += 1
            self.log_message(f"Task failure {self.failure_count}", log_level=logging.ERROR)
            self.log_message(str(e), log_level=logging.ERROR)
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

    @staticmethod
    def get_task(jobid: int) -> "Task":
        job = Job.query.filter(Job.id == jobid).one()
        task = pickle.loads(job.pickledclass)
        if not issubclass(type(task), Task):
            raise Exception("Task unpickle got something that was not a task subclass")
        return task

    @staticmethod
    def get_next_task() -> "Task | None":
        sql = text("""DELETE FROM pending_job 
        WHERE id = (
        SELECT id
        FROM pending_job
        ORDER BY created ASC 
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        )
        RETURNING *;
        """)
        result = db.session.execute(sql).fetchall()
        if result:
            jobid = int(result[0][1])
            task = Task.get_task(jobid)
            db.session.commit()
            return task

        return None
