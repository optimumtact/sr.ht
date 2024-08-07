from pathlib import Path

from sqlalchemy import text

from srht.common import generate_thumbnail
from srht.config import _cfg
from srht.database import db
from srht.objects import Job, Message, Upload


def queue_thumbnail_job(uploaded_file: Upload):
    njob = Job()
    njob.status = Job.queued
    njob.data = {"uploadid": uploaded_file.id}
    db.session.add(njob)
    db.session.commit()
    send_message_to_workers(njob)


def handle_thumbnail_job(uploaded_file: Upload):
    thumbnail = generate_thumbnail(
        uploaded_file.get_storage_path(), uploaded_file.get_thumbnail_path()
    )
    uploaded_file.thumbnail = "thumbnails" + "/" + thumbnail.name
    print(uploaded_file.thumbnail)
    db.session.add(uploaded_file)
    # Save the thumbnail name
    # upload.thumbnail = 'thumbnails'+'/'+thumbnail.name


def send_message_to_workers(job: Job):
    message = Message()
    message.job_id = job.id
    db.session.add(message)
    db.session.commit()


def get_next_message() -> Job | None:
    sql = text(
        """DELETE FROM message 
    WHERE id = (
      SELECT id
      FROM message
      ORDER BY created ASC 
      FOR UPDATE SKIP LOCKED
      LIMIT 1
    )
    RETURNING *;
    """
    )
    result = db.session.execute(sql).fetchall()
    if result:
        job = Job.query.filter(Job.id == result[0][1]).one()
        return job
    return None
