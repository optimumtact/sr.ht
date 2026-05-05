import logging
import os
import sys
from typing import Annotated

import typer
from sqlalchemy import text

cli = typer.Typer(help="Command line admin interface")
admin_cli = typer.Typer(help="Admin user management commands")
user_cli = typer.Typer(help="User management commands")
database_cli = typer.Typer(help="Database maintenance commands")
task_cli = typer.Typer(help="Background task commands")
thumbnails_cli = typer.Typer(help="Thumbnail maintenance commands")

cli.add_typer(admin_cli, name="admin")
cli.add_typer(user_cli, name="user")
cli.add_typer(database_cli, name="database")
cli.add_typer(task_cli, name="task")
cli.add_typer(thumbnails_cli, name="thumbnails")


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


def get_app_context():
    from srht.app import app

    return app.app_context()


def get_db():
    from srht.app import db

    return db


def do_task(count: int):
    from srht.tasks import Task

    start = 0
    while count > start:
        task = Task.get_next_task()
        if task:
            task.run(logger)
        start += 1


def stuckfix():
    from srht.objects import Job, PendingJob
    from srht.tasks import Task
    from srht.tasks.basetask import TaskStatus

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
        except Exception as exc:
            logger.error(f"Failed to re-queue job {job.id}: {exc}")
            get_db().session.rollback()


def queue_task_for_missing_thumbnails():
    from srht.objects import Upload
    from srht.tasks import GenerateImageThumbnail

    uploads = Upload.query.filter(Upload.thumbnail == None).all()
    for upload in uploads:
        task = GenerateImageThumbnail(upload.id)
        task.queue()


def apply_migrations():
    from srht.config import _cfg

    db = get_db()
    if _cfg("migrations"):
        folder_path = _cfg("migrations")
        if folder_path:
            try:
                for filename in os.listdir(folder_path):
                    if filename.endswith(".sql"):
                        file_path = os.path.join(folder_path, filename)

                        with open(file_path, "r") as file:
                            sql_script = file.read()
                            db.session.execute(text(sql_script))
                            db.session.commit()
                            logger.info(f"Executed {filename}")

            except Exception as exc:
                db.session.rollback()
                logger.error(f"An error occurred: {exc}")


def remove_admin(name: str):
    from srht.objects import User

    db = get_db()
    user = User.query.filter(User.username == name).first()
    if user:
        user.admin = False
        db.session.commit()
    else:
        logger.error("Not a valid user")


def make_admin(name: str):
    from srht.objects import User

    db = get_db()
    user = User.query.filter(User.username == name).first()
    if user:
        user.admin = True
        db.session.commit()
    else:
        logger.error("Not a valid user")


def create_user(name: str, password: str, email: str):
    from srht.objects import User

    db = get_db()
    user = User(name, email, password)
    if user:
        user.suspended = False
        db.session.add(user)
        db.session.commit()
        logger.info("User created")
    else:
        logger.error("Couldn't create the user")


def reset_password(name: str, password: str):
    from srht.objects import User

    db = get_db()
    user = User.query.filter(User.username == name).first()
    if user:
        if len(password) < 5 or len(password) > 256:
            logger.error("Password must be between 5 and 256 characters.")
            raise typer.Exit(code=1)
        user.set_password(password)
        db.session.commit()
    else:
        logger.error("Not a valid user")
        raise typer.Exit(code=1)


def list_admin():
    from srht.objects import User

    users = User.query.filter(User.admin)
    for user in users:
        logger.info(user.username)


@admin_cli.command("promote")
def admin_promote(name: str):
    with get_app_context():
        make_admin(name)


@admin_cli.command("demote")
def admin_demote(name: str):
    with get_app_context():
        remove_admin(name)


@admin_cli.command("list")
def admin_list():
    with get_app_context():
        list_admin()


@user_cli.command("create")
def user_create(name: str, password: str, email: str):
    with get_app_context():
        create_user(name, password, email)


@user_cli.command("reset-password")
def user_reset_password(name: str, password: str):
    with get_app_context():
        reset_password(name, password)


@database_cli.command("migrate")
def database_migrate():
    with get_app_context():
        apply_migrations()


@task_cli.command("run")
def task_run(
    count: Annotated[
        int,
        typer.Option("--count", "-c", min=1, help="Maximum number of queued jobs to run."),
    ] = 1,
):
    with get_app_context():
        do_task(count)


@task_cli.command("fix-stuck")
def task_fix_stuck():
    with get_app_context():
        stuckfix()


@thumbnails_cli.command("queue")
def thumbnails_queue_missing():
    with get_app_context():
        queue_task_for_missing_thumbnails()


if __name__ == "__main__":
    cli()
