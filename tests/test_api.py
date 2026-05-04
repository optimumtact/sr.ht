import io
import json
import os
from srht.config import _cfg
from srht.objects import Job, PendingJob, Upload
from srht.tasks import TaskType, Task, GenerateImageThumbnail
from srht.database import db

def test_upload_file(client, test_user):
    data = {
        'key': test_user.apiKey,
        'file': (io.BytesIO(b"this is a test file"), 'test.txt')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    
    result = json.loads(response.data)
    assert result['success'] is True
    assert 'url' in result
    assert 'hash' in result
    
    # Verify file is viewable
    url = result['url']
    path = url.split('/')[-1]
    
    response = client.get(f'/{path}')
    assert response.status_code == 200
    assert response.data == b"this is a test file"

def test_delete_file(client, test_user):
    # First upload
    data = {
        'key': test_user.apiKey,
        'file': (io.BytesIO(b"file to delete"), 'delete_me.txt')
    }
    upload_response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    result = json.loads(upload_response.data)
    filename = result['url'].split('/')[-1]
    
    # Then delete
    delete_data = {
        'key': test_user.apiKey,
        'filename': filename
    }
    delete_response = client.post('/api/delete', data=delete_data)
    assert delete_response.status_code == 200
    assert json.loads(delete_response.data)['success'] is True
    
    # Verify it's gone
    get_response = client.get(f'/{filename}')
    assert get_response.status_code == 404

def test_upload_invalid_key(client):
    data = {
        'key': 'invalid_key',
        'file': (io.BytesIO(b"test"), 'test.txt')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 403
    assert b"API key not recognized" in response.data

def test_thumbnail_task_queued(client, test_user, app):
    # Use 1.png from _static
    with open('tests/test_files/1.png', 'rb') as f:
        img_data = f.read()
    
    data = {
        'key': test_user.apiKey,
        'file': (io.BytesIO(img_data), '1.png')
    }
    
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert json.loads(response.data)['success'] is True
    
    # Check if a thumbnail task was queued in the database
    with app.app_context():
        # Verify Job exists
        job = Job.query.filter(Job.tasktype == TaskType.THUMBNAIL).first()
        assert job is not None
        
        # Verify PendingJob exists for this job
        pending = PendingJob.query.filter(PendingJob.job_id == job.id).first()
        assert pending is not None

def test_thumbnail_execution(client, test_user, app):
    # 1. Upload an image
    with open('tests/test_files/1.png', 'rb') as f:
        img_data = f.read()
    
    data = {
        'key': test_user.apiKey,
        'file': (io.BytesIO(img_data), 'test_image.png')
    }
    
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    
    # 2. Manually trigger the task processing
    with app.app_context():
        pending = PendingJob.query.first()
        assert pending is not None
        
        # Instantiate task from the queued job
        task = Task.get_task(pending.job_id)
        assert isinstance(task, GenerateImageThumbnail)
        
        # Run the task
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
        response = client.get(f"/{upload.thumbnail}")
        assert response.status_code == 200
        assert response.mimetype.startswith("image/")

def test_video_thumbnail_execution(client, test_user, app):
    # 1. Upload a video
    video_filename = '500_Tage_20_Prozent_geimpft.webm.480p.vp9.webm'
    with open(f'tests/test_files/{video_filename}', 'rb') as f:
        video_data = f.read()
    
    data = {
        'key': test_user.apiKey,
        'file': (io.BytesIO(video_data), video_filename)
    }
    
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    
    # 2. Manually trigger the task processing
    with app.app_context():
        # Get the latest pending job (the one for this video)
        pending = PendingJob.query.order_by(PendingJob.id.desc()).first()
        assert pending is not None
        
        task = Task.get_task(pending.job_id)
        assert isinstance(task, GenerateImageThumbnail)
        
        # Run the task
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
        response = client.get(f"/{upload.thumbnail}")
        assert response.status_code == 200
        assert response.mimetype == "image/png"
