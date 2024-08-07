import os
from datetime import datetime

from docopt import docopt
from sqlalchemy import text

from srht.app import app, db
from srht.config import _cfg
from srht.objects import Job, Upload, User
from srht.task_queue import get_next_message, handle_thumbnail_job, queue_thumbnail_job


def do_task(arguments):
    count = int(arguments["<count>"])
    start = 0
    while count > start:
        job = get_next_message()
        if job:
            upload = Upload.query.filter(Upload.id == job.data["uploadid"]).one()
            handle_thumbnail_job(upload)
            job.status = Job.complete
            db.session.add(job)
            db.session.commit()
        start += 1


def queue_task_for_missing_thumbnails(arguments):
    uploads = Upload.query.all()
    for upload in uploads:
        queue_thumbnail_job(upload)
    db.session.commit()


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
                            print(f"Executed {filename}")

            except Exception as e:
                db.session.rollback()
                print(f"An error occurred: {e}")


def remove_admin(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.admin = False  # remove admin
        db.session.commit()
    else:
        print("Not a valid user")


def make_admin(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.admin = True  # make admin
        db.session.commit()
    else:
        print("Not a valid user")


def list_admin(arguments):
    users = User.query.filter(User.admin)
    for u in users:
        print(u.username)


def approve_user(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        u.approved = True  # approve user
        u.approvalDate = datetime.now()
        db.session.commit()
    else:
        print("Not a valid user")


def create_user(arguments):
    u = User(arguments["<name>"], arguments["<email>"], arguments["<password>"])
    if u:
        u.approved = True  # approve user
        u.approvalDate = datetime.now()
        db.session.add(u)
        db.session.commit()
        print("User created")
    else:
        print("Couldn't create the uer")


def reset_password(arguments):
    u = User.query.filter(User.username == arguments["<name>"]).first()
    if u:
        password = arguments["<password>"]
        if len(password) < 5 or len(password) > 256:
            print("Password must be between 5 and 256 characters.")
            return
        u.set_password(password)
        db.session.commit()
    else:
        print("Not a valid user")


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
    manage.py task missingthumbnails

Options:
    -h --help Show this screen.
"""
if __name__ == "__main__":
    with app.app_context():
        arguments = docopt(interface, version="make admin 0.1")
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
        elif arguments["task"] and arguments["missingthumbnails"]:
            queue_task_for_missing_thumbnails(arguments)
