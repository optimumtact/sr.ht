import logging
import os
import sys
from datetime import datetime
from typing import Annotated

import random
import time

import typer
from sqlalchemy import func, text

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


def do_task(count: int, delay: bool = False):
    from srht.tasks import Task

    if delay:
        delay_seconds = random.uniform(1, 30)
        logger.info(f"Delaying task execution by {delay_seconds:.2f} seconds to reduce contention.")
        time.sleep(delay_seconds)

    start = 0
    run_due_schedules()
    while count > start:
        task = Task.get_next_task()
        if task:
            task.run(logger)
        start += 1


def stuckfix():
    from srht.objects import Job
    from srht.tasks import Task
    from srht.tasks.basetask import TaskStatus

    stuck = Job.query.filter(Job.status == int(TaskStatus.CLAIMED)).all()
    if not stuck:
        logger.info("No claimed jobs found.")
        return
    logger.info(f"Found {len(stuck)} claimed job(s). Re-queuing...")
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


def _has_active_jobs(task_type: int) -> bool:
    from srht.objects import Job
    from srht.tasks.basetask import TaskStatus

    active_count = (
        Job.query.filter(Job.tasktype == int(task_type))
        .filter(Job.status.in_([int(TaskStatus.QUEUED), int(TaskStatus.CLAIMED)]))
        .count()
    )
    return active_count > 0


def queue_caption_batch(limit: int, force: bool = False):
    from srht.objects import Upload, User
    from srht.tasks import BatchGenerateImageCaptions
    from srht.tasks.basetask import TaskType

    if not force and _has_active_jobs(TaskType.BATCH_CAPTIONS):
        logger.info("Skipped caption batch enqueue: active caption batch already exists")
        return

    uploads = (
        Upload.query.filter(Upload.caption.is_(None))
        .filter(Upload.caption_complete.is_(False))
        .filter(Upload.thumbnail.isnot(None))
        .filter(Upload.user.has(User.ai_opt_in.is_(True)))
        .order_by(Upload.created, Upload.id)
        .limit(limit)
        .all()
    )
    upload_ids = [upload.id for upload in uploads]
    if not upload_ids:
        logger.info("Skipped caption batch enqueue: no thumbnail-ready uploads require captions")
        return None

    task = BatchGenerateImageCaptions(upload_ids=upload_ids)
    task.queue()
    logger.info(
        f"Queued caption batch job {task.jobid} with {len(upload_ids)} uploads (limit={limit})"
    )
    return task


def queue_tag_batch(limit: int, force: bool = False):
    from srht.objects import Upload, User
    from srht.tasks import BatchGenerateImageTags
    from srht.tasks.basetask import TaskType

    if not force and _has_active_jobs(TaskType.BATCH_TAGS):
        logger.info("Skipped tag batch enqueue: active tag batch already exists")
        return

    uploads = (
        Upload.query.filter(Upload.caption.isnot(None))
        .filter(func.length(func.trim(Upload.caption)) > 0)
        .filter(~Upload.tags.any())
        .filter(Upload.user.has(User.ai_opt_in.is_(True)))
        .order_by(Upload.created, Upload.id)
        .limit(limit)
        .all()
    )
    upload_ids = [upload.id for upload in uploads]
    if not upload_ids:
        logger.info("Skipped tag batch enqueue: no captioned uploads require tags")
        return None

    task = BatchGenerateImageTags(upload_ids=upload_ids)
    task.queue()
    logger.info(f"Queued tag batch job {task.jobid} with {len(upload_ids)} uploads (limit={limit})")
    return task


def run_due_schedules():
    from srht.objects import TaskSchedule
    from srht.tasks.basetask import TaskType

    now = datetime.now()
    TaskSchedule.ensure_defaults()
    due_schedules = (
        TaskSchedule.query.filter(TaskSchedule.enabled.is_(True))
        .filter(TaskSchedule.next_run_time <= now)
        .order_by(TaskSchedule.next_run_time.asc(), TaskSchedule.id.asc())
        .all()
    )
    print(f"Found {len(due_schedules)} due schedule(s).")
    if not due_schedules:
        return 0

    queued_count = 0

    for schedule in due_schedules:
        try:
            queued_task = None
            if schedule.tasktype == int(TaskType.BATCH_CAPTIONS):
                queued_task = queue_caption_batch(limit=50)
            elif schedule.tasktype == int(TaskType.BATCH_TAGS):
                queued_task = queue_tag_batch(limit=50)
            else:
                logger.info(f"Skipping unknown schedule task type {schedule.tasktype}")
                continue

            schedule.advance(now)
            db = get_db()
            db.session.add(schedule)
            db.session.commit()
            if queued_task:
                queued_count += 1
                logger.info(
                    f"Queued scheduled task {schedule.tasktype} from schedule {schedule.id}; next run {schedule.next_run_time}"
                )
            else:
                logger.info(
                    f"Advanced schedule {schedule.id} for task type {schedule.tasktype}; next run {schedule.next_run_time}"
                )
        except Exception as exc:
            logger.error(f"Failed to evaluate schedule {schedule.id}: {exc}")
            get_db().session.rollback()

    return queued_count


def apply_migrations():
    from srht.config import _cfg

    db = get_db()
    if _cfg("migrations"):
        folder_path = _cfg("migrations")
        if folder_path:
            try:

                def _migration_sort_key(name: str):
                    if not name.endswith(".sql"):
                        return (1, name)

                    prefix = name.split("_", 1)[0]
                    if prefix.isdigit():
                        return (0, int(prefix), name)

                    return (0, float("inf"), name)

                for filename in sorted(os.listdir(folder_path), key=_migration_sort_key):
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
        typer.Option(
            "--count",
            "-c",
            "-n",
            min=1,
            help="Maximum number of queued jobs to run.",
        ),
    ] = 1,
    delay: Annotated[
        bool,
        typer.Option(
            "--delay",
            help="Add a random delay to task execution to reduce contention when multiple workers are running.",
        ),
    ] = False,
):
    with get_app_context():
        do_task(count, delay=delay)


@task_cli.command("fix-stuck")
def task_fix_stuck():
    with get_app_context():
        stuckfix()


@task_cli.command("queue-caption-batch")
def task_queue_caption_batch(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", min=1, help="Maximum uploads to include in caption batch."),
    ] = 50,
    force: Annotated[
        bool,
        typer.Option("--force", help="Queue batch even if one is already active."),
    ] = False,
):
    with get_app_context():
        queue_caption_batch(limit=limit, force=force)


@task_cli.command("queue-tag-batch")
def task_queue_tag_batch(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", min=1, help="Maximum uploads to include in tag batch."),
    ] = 50,
    force: Annotated[
        bool,
        typer.Option("--force", help="Queue batch even if one is already active."),
    ] = False,
):
    with get_app_context():
        queue_tag_batch(limit=limit, force=force)


@thumbnails_cli.command("queue")
def thumbnails_queue_missing():
    with get_app_context():
        queue_task_for_missing_thumbnails()


if __name__ == "__main__":
    cli()
