import logging
import os
import sys
from datetime import datetime

from docopt import docopt
from sqlalchemy import text

from srht.app import app, db
from srht.config import _cfg
from srht.objects import Job, PendingJob, Upload, User
from srht.tasks import GenerateImageThumbnail, Task
from srht.tasks.basetask import TaskStatus


def get_manage_logger():
    logger = logging.getLogger("srht.manage")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, "stream", None) is sys.stdout
        for handler in logger.handlers
    ):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(console_handler)
    return logger


logger = get_manage_logger()


def do_task(arguments):
    count = int(arguments["<count>"])
    start = 0
    while count > start:
        task = Task.get_next_task()
        if task:
            task.run(logger)
        start += 1


def stuckfix(arguments):
    """Re-queue QUEUED jobs that have no PendingJob entry."""
    pending_job_ids = {
        row.job_id for row in PendingJob.query.with_entities(PendingJob.job_id).all()
    }
    stuck = Job.query.filter(
        Job.status == int(TaskStatus.QUEUED),
        Job.id.notin_(pending_job_ids),
    ).all()
    if not stuck:
        logger.info("No stuck jobs found.")
        return
    logger.info(f"Found {len(stuck)} stuck job(s). Re-queuing...")
    for job in stuck:
        try:
            if job.version < Task.LATEST_VERSION:
                logger.info(
                    f"Skipping job {job.id}; version {job.version} is older than latest {Task.LATEST_VERSION}."
                )
                continue
            task = Task.get_task(job.id)
            task.queue()
            logger.info(f"Re-queued job {job.id}")
        except Exception as e:
            logger.error(f"Failed to re-queue job {job.id}: {e}")
            db.session.rollback()


def queue_task_for_missing_thumbnails(arguments):
    uploads = Upload.query.filter(Upload.thumbnail == None).all()
    for upload in uploads:
        task = GenerateImageThumbnail(upload.id)
        task.queue()


def apply_migrations(arguments):
    if _cfg("migrations"):
        folder_path = _cfg("migrations")
        if folder_path:
            try:
                # Loop through all files in the folder
                for filename in os.listdir(folder_path):
                    if filename.endswith(".sql"):
                        file_path = os.path.join(folder_path, filename)

                        # Read the SQL script
                        with open(file_path, "r") as file:
                            sql_script = file.read()
                            # Execute the SQL script
                            db.session.execute(text(sql_script))
                            db.session.commit()
                            logger.info(f"Executed {filename}")

            except Exception as e:
                db.session.rollback()
                logger.error(f"An error occurred: {e}")


def remove_admin(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.admin = False  # remove admin
        db.session.commit()
    else:
        logger.error("Not a valid user")


def make_admin(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.admin = True  # make admin
        db.session.commit()
    else:
        logger.error("Not a valid user")


def list_admin(arguments):
    users = User.query.filter(User.admin)
    for u in users:
        logger.info(u.username)


def approve_user(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.approved = True  # approve user
        u.approvalDate = datetime.now()
        db.session.commit()
    else:
        logger.error("Not a valid user")


def create_user(arguments):
    u = User(arguments["<name>"], arguments["<email>"], arguments["<password>"])
    if u:
        u.approved = True  # approve user
        u.approvalDate = datetime.now()
        db.session.add(u)
        db.session.commit()
        logger.info("User created")
    else:
        logger.error("Couldn't create the user")


def reset_password(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        password = arguments["<password>"]
        if len(password) < 5 or len(password) > 256:
            logger.error("Password must be between 5 and 256 characters.")
            return
        u.set_password(password)
        db.session.commit()
    else:
        logger.error("Not a valid user")


interface = """
Command line admin interface
Usage:
    manage.py admin promote <name>
    manage.py admin demote <name>
    manage.py admin list
    manage.py user approve <name>
    manage.py user create <name> <password> <email>
    manage.py user reset_password <name> <password>
    manage.py database migrate
    manage.py task run <count>
    manage.py task fix stuck
    manage.py thumbnails queue
    manage.py thumbnails recreate <url> #TODO

Options:
    -h --help Show this screen.
"""
if __name__ == "__main__":
    with app.app_context():
        arguments = docopt(interface, version="1")
        if arguments["admin"] and arguments["promote"]:
            make_admin(arguments)
        elif arguments["admin"] and arguments["demote"]:
            remove_admin(arguments)
        elif arguments["admin"] and arguments["list"]:
            list_admin(arguments)
        elif arguments["user"] and arguments["approve"]:
            approve_user(arguments)
        elif arguments["user"] and arguments["create"]:
            create_user(arguments)
        elif arguments["user"] and arguments["reset_password"]:
            reset_password(arguments)
        elif arguments["database"] and arguments["migrate"]:
            apply_migrations(arguments)
        elif arguments["task"] and arguments["run"]:
            do_task(arguments)
        elif arguments["task"] and arguments["fix"] and arguments["stuck"]:
            stuckfix(arguments)
        elif arguments["thumbnails"] and arguments["queue"]:
            queue_task_for_missing_thumbnails(arguments)
