import argparse
import logging
import os
import sys
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


def build_parser():
    parser = argparse.ArgumentParser(description="Command line admin interface")
    top_level = parser.add_subparsers(dest="command")

    admin_parser = top_level.add_parser("admin")
    admin_commands = admin_parser.add_subparsers(dest="admin_command")

    admin_promote = admin_commands.add_parser("promote")
    admin_promote.add_argument("name")
    admin_promote.set_defaults(handler=make_admin)

    admin_demote = admin_commands.add_parser("demote")
    admin_demote.add_argument("name")
    admin_demote.set_defaults(handler=remove_admin)

    admin_list = admin_commands.add_parser("list")
    admin_list.set_defaults(handler=list_admin)

    user_parser = top_level.add_parser("user")
    user_commands = user_parser.add_subparsers(dest="user_command")

    user_create = user_commands.add_parser("create")
    user_create.add_argument("name")
    user_create.add_argument("password")
    user_create.add_argument("email")
    user_create.set_defaults(handler=create_user)

    user_reset = user_commands.add_parser("reset_password")
    user_reset.add_argument("name")
    user_reset.add_argument("password")
    user_reset.set_defaults(handler=reset_password)

    database_parser = top_level.add_parser("database")
    database_commands = database_parser.add_subparsers(dest="database_command")
    database_migrate = database_commands.add_parser("migrate")
    database_migrate.set_defaults(handler=apply_migrations)

    task_parser = top_level.add_parser("task")
    task_commands = task_parser.add_subparsers(dest="task_command")

    task_run = task_commands.add_parser("run")
    task_run.add_argument("count", type=int)
    task_run.set_defaults(handler=do_task)

    task_fix = task_commands.add_parser("fix")
    task_fix_commands = task_fix.add_subparsers(dest="task_fix_command")
    task_fix_stuck = task_fix_commands.add_parser("stuck")
    task_fix_stuck.set_defaults(handler=stuckfix)

    thumbnails_parser = top_level.add_parser("thumbnails")
    thumbnails_commands = thumbnails_parser.add_subparsers(dest="thumbnails_command")
    thumbnails_queue = thumbnails_commands.add_parser("queue")
    thumbnails_queue.set_defaults(handler=queue_task_for_missing_thumbnails)

    thumbnails_recreate = thumbnails_commands.add_parser("recreate")
    thumbnails_recreate.add_argument("url")

    return parser


def do_task(args):
    count = args.count
    start = 0
    while count > start:
        task = Task.get_next_task()
        if task:
            task.run(logger)
        start += 1


def stuckfix(args):
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


def queue_task_for_missing_thumbnails(args):
    uploads = Upload.query.filter(Upload.thumbnail == None).all()
    for upload in uploads:
        task = GenerateImageThumbnail(upload.id)
        task.queue()


def apply_migrations(args):
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


def remove_admin(args):
    u = User.query.filter(User.username == args.name).first()
    if u:
        u.admin = False  # remove admin
        db.session.commit()
    else:
        logger.error("Not a valid user")


def make_admin(args):
    u = User.query.filter(User.username == args.name).first()
    if u:
        u.admin = True  # make admin
        db.session.commit()
    else:
        logger.error("Not a valid user")


def list_admin(args):
    users = User.query.filter(User.admin)
    for u in users:
        logger.info(u.username)


def create_user(args):
    u = User(args.name, args.email, args.password)
    if u:
        u.suspended = False
        db.session.add(u)
        db.session.commit()
        logger.info("User created")
    else:
        logger.error("Couldn't create the user")


def reset_password(args):
    u = User.query.filter(User.username == args.name).first()
    if u:
        password = args.password
        if len(password) < 5 or len(password) > 256:
            logger.error("Password must be between 5 and 256 characters.")
            return
        u.set_password(password)
        db.session.commit()
    else:
        logger.error("Not a valid user")


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    with app.app_context():
        if hasattr(args, "handler"):
            args.handler(args)
        else:
            parser.print_help()
