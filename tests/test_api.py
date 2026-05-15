import io
import json
import os
from srht.config import _cfg
from srht.objects import Job, Tag, Upload
from srht.tasks import (
    BatchGenerateImageCaptions,
    BatchGenerateImageTags,
    GenerateImageThumbnail,
    Task,
    TaskType,
)
import srht.tasks.image_caption_tags as image_caption_tags
import srht.tasks.image_thumbnail as image_thumbnail
from srht.tasks.basetask import TaskStatus
from srht.database import db
import manage


def test_upload_file(client, test_user):
    data = {"key": test_user.apiKey, "file": (io.BytesIO(b"this is a test file"), "test.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    result = json.loads(response.data)
    assert result["success"] is True
    assert "url" in result
    assert "hash" in result

    # Verify file is viewable
    url = result["url"]
    path = url.split("/")[-1]

    response = client.get(f"/f/{path}")
    assert response.status_code == 200
    assert response.data == b"this is a test file"


def test_delete_file(client, test_user):
    # First upload
    data = {"key": test_user.apiKey, "file": (io.BytesIO(b"file to delete"), "delete_me.txt")}
    upload_response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    result = json.loads(upload_response.data)
    filename = result["url"].split("/")[-1]

    # Then delete
    delete_data = {"key": test_user.apiKey, "filename": filename}
    delete_response = client.post("/api/delete", data=delete_data)
    assert delete_response.status_code == 200
    assert json.loads(delete_response.data)["success"] is True

    # Verify it's gone
    get_response = client.get(f"/f/{filename}")
    assert get_response.status_code == 404


def test_upload_invalid_key(client):
    data = {"key": "invalid_key", "file": (io.BytesIO(b"test"), "test.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 403
    assert b"API key not recognized" in response.data


def test_thumbnail_task_queued(client, test_user, app):
    # Use 1.png from _static
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "1.png")}

    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert json.loads(response.data)["success"] is True

    # Check if a thumbnail task was queued in the database
    with app.app_context():
        # Verify Job exists
        job = Job.query.filter(Job.tasktype == TaskType.THUMBNAIL).first()
        assert job is not None

        # Verify job was queued
        assert job.status == int(TaskStatus.QUEUED)


def test_thumbnail_execution(client, test_user, app, monkeypatch):
    monkeypatch.setattr(image_caption_tags, "_HAS_ML_DEPS", False)
    # 1. Upload an image
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "test_image.png")}

    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    # 2. Claim and run the queued task
    with app.app_context():
        task = None
        for _ in range(3):
            candidate = Task.get_next_task()
            assert candidate is not None
            if isinstance(candidate, GenerateImageThumbnail):
                task = candidate
                break
            candidate.run()

        assert task is not None

        claimed_job = Job.query.filter(Job.id == task.jobid).first()
        assert claimed_job is not None
        assert claimed_job.status == int(TaskStatus.CLAIMED)
        assert claimed_job.processid is not None
        assert claimed_job.timeclaimed is not None

        task.run()

        # 3. Verify results in DB
        upload = Upload.query.filter(Upload.id == task.uploadid).first()
        assert upload.thumbnail is not None
        assert upload.thumbnail.startswith("thumbnails/")

        # 4. Verify file exists on disk
        storage_path = os.environ.get("storage")
        thumb_full_path = os.path.join(storage_path, upload.thumbnail)
        assert os.path.exists(thumb_full_path)

        # 5. Verify it's viewable via HTML route
        response = client.get(f"/f/{upload.thumbnail}")
        assert response.status_code == 200
        assert response.mimetype.startswith("image/")


def test_video_thumbnail_execution(client, test_user, app, monkeypatch):
    monkeypatch.setattr(image_caption_tags, "_HAS_ML_DEPS", False)
    # 1. Upload a video
    video_filename = "500_Tage_20_Prozent_geimpft.webm.480p.vp9.webm"
    with open(f"tests/test_files/{video_filename}", "rb") as f:
        video_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(video_data), video_filename)}

    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    # 2. Claim and run the queued task
    with app.app_context():
        task = None
        for _ in range(3):
            candidate = Task.get_next_task()
            assert candidate is not None
            if isinstance(candidate, GenerateImageThumbnail):
                task = candidate
                break
            candidate.run()

        assert task is not None

        claimed_job = Job.query.filter(Job.id == task.jobid).first()
        assert claimed_job is not None
        assert claimed_job.status == int(TaskStatus.CLAIMED)
        assert claimed_job.processid is not None
        assert claimed_job.timeclaimed is not None

        task.run()

        # 3. Verify results in DB
        upload = Upload.query.filter(Upload.id == task.uploadid).first()
        assert upload.thumbnail is not None
        assert upload.thumbnail.endswith(".png")

        # 4. Verify file exists on disk
        storage_path = os.environ.get("storage")
        thumb_full_path = os.path.join(storage_path, upload.thumbnail)
        assert os.path.exists(thumb_full_path)

        # 5. Verify it's viewable via HTML route
        response = client.get(f"/f/{upload.thumbnail}")
        assert response.status_code == 200
        assert response.mimetype == "image/png"


def _claim_tasks(app, max_count=4):
    claimed = []
    with app.app_context():
        for _ in range(max_count):
            task = Task.get_next_task()
            if not task:
                break
            claimed.append(task)
    return claimed


def test_caption_task_queued(client, test_user, app, monkeypatch):
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "1.png")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert json.loads(response.data)["success"] is True

    with app.app_context():
        # Thumbnail should be queued immediately after upload
        thumbnail_job = Job.query.filter(Job.tasktype == TaskType.THUMBNAIL).first()
        assert thumbnail_job is not None
        assert thumbnail_job.status == int(TaskStatus.QUEUED)

    # Execute thumbnail task
    claimed = _claim_tasks(app)
    thumbnail_task = next(
        (task for task in claimed if isinstance(task, GenerateImageThumbnail)), None
    )
    assert thumbnail_task is not None

    with app.app_context():
        thumbnail_task.run()


def test_caption_task_execution_inserts_normalized_unique_tags(client, test_user, app, monkeypatch):
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "tagged.png")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    # First, execute the thumbnail task.
    claimed = _claim_tasks(app)
    thumbnail_task = next(
        (task for task in claimed if isinstance(task, GenerateImageThumbnail)), None
    )
    assert thumbnail_task is not None

    with app.app_context():
        thumbnail_task.run()

    # Queue and run caption batch.
    monkeypatch.setattr(image_caption_tags, "_HAS_ML_DEPS", True)
    monkeypatch.setattr(
        BatchGenerateImageCaptions,
        "_generate_caption",
        lambda self, path: "A red flower in a green field under sunlight.",
    )
    monkeypatch.setattr(
        BatchGenerateImageCaptions,
        "_get_moondream_model",
        lambda self: (object(), object()),
    )
    with app.app_context():
        manage.queue_caption_batch(limit=20)

    claimed = _claim_tasks(app)
    caption_task = next(
        (task for task in claimed if isinstance(task, BatchGenerateImageCaptions)), None
    )
    assert caption_task is not None

    with app.app_context():
        caption_task.run()

    # Queue and run tag batch.
    monkeypatch.setattr(
        BatchGenerateImageTags,
        "_extract_tags",
        lambda self, caption: [
            ("Red Flower", 0.91),
            ("flower", 0.52),
            ("Green Field", 0.84),
            ("green field", 0.77),
            ("sunlight", 0.64),
        ],
    )
    monkeypatch.setattr(BatchGenerateImageTags, "_get_keybert_model", lambda self: object())

    with app.app_context():
        manage.queue_tag_batch(limit=20)

    claimed = _claim_tasks(app)
    caption_task = next(
        (task for task in claimed if isinstance(task, BatchGenerateImageTags)), None
    )
    assert caption_task is not None

    with app.app_context():
        caption_task.run()
        assert caption_task.status == TaskStatus.COMPLETE

        tags = (
            db.session.query(Tag.tag, Tag.relevance)
            .filter(Tag.uploadid == thumbnail_task.uploadid)
            .order_by(Tag.tag.asc())
            .all()
        )
        values = [row[0] for row in tags]
        assert values == ["flower", "green field", "red flower", "sunlight"]
        relevances = {row[0]: row[1] for row in tags}
        assert relevances["red flower"] == 0.91
        # Keep the higher score when normalized duplicates collapse.
        assert relevances["green field"] == 0.84
        assert relevances["flower"] == 0.52
        assert relevances["sunlight"] == 0.64


def test_caption_task_skips_non_image_upload(client, test_user, app, monkeypatch):
    data = {"key": test_user.apiKey, "file": (io.BytesIO(b"plain text"), "note.txt")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    # First, execute the thumbnail task.
    claimed = _claim_tasks(app)
    thumbnail_task = next(
        (task for task in claimed if isinstance(task, GenerateImageThumbnail)), None
    )
    assert thumbnail_task is not None

    with app.app_context():
        thumbnail_task.run()

    # Queue a caption batch and verify unsupported media is skipped.
    monkeypatch.setattr(image_caption_tags, "_HAS_ML_DEPS", True)
    monkeypatch.setattr(
        BatchGenerateImageCaptions,
        "_generate_caption",
        lambda self, path: "this should not run",
    )
    monkeypatch.setattr(
        BatchGenerateImageCaptions,
        "_get_moondream_model",
        lambda self: (object(), object()),
    )

    with app.app_context():
        manage.queue_caption_batch(limit=20)

    claimed = _claim_tasks(app)
    caption_task = next(
        (task for task in claimed if isinstance(task, BatchGenerateImageCaptions)), None
    )
    assert caption_task is not None

    with app.app_context():
        caption_task.run()
        upload_id = caption_task.upload_ids[0]
        upload = Upload.query.filter(Upload.id == upload_id).one()
        assert upload.caption is None
        tags = db.session.query(Tag).filter(Tag.uploadid == upload_id).all()
        assert tags == []


def test_queue_caption_batch_requires_thumbnail(client, test_user, app):
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "needs-thumb.png")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    with app.app_context():
        manage.queue_caption_batch(limit=20)
        batch_job = Job.query.filter(Job.tasktype == TaskType.BATCH_CAPTIONS).first()
        assert batch_job is None

    claimed = _claim_tasks(app)
    thumbnail_task = next(
        (task for task in claimed if isinstance(task, GenerateImageThumbnail)), None
    )
    assert thumbnail_task is not None

    with app.app_context():
        thumbnail_task.run()
        manage.queue_caption_batch(limit=20)
        batch_job = Job.query.filter(Job.tasktype == TaskType.BATCH_CAPTIONS).first()
        assert batch_job is not None
        assert batch_job.status == int(TaskStatus.QUEUED)


def test_queue_caption_batch_skips_if_active(client, test_user, app):
    with open("tests/test_files/1.png", "rb") as f:
        img_data = f.read()

    data = {"key": test_user.apiKey, "file": (io.BytesIO(img_data), "active-batch.png")}
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    claimed = _claim_tasks(app)
    thumbnail_task = next(
        (task for task in claimed if isinstance(task, GenerateImageThumbnail)), None
    )
    assert thumbnail_task is not None

    with app.app_context():
        thumbnail_task.run()
        manage.queue_caption_batch(limit=20)
        manage.queue_caption_batch(limit=20)

        batch_jobs = Job.query.filter(Job.tasktype == TaskType.BATCH_CAPTIONS).all()
        assert len(batch_jobs) == 1
