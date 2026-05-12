import os
import shutil
import tempfile
import pytest

# Set environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["storage"] = tempfile.mkdtemp()  # dummy for import time
os.environ["protocol"] = "http"
os.environ["domain"] = "localhost"
os.environ["secret_key"] = "test_secret"
os.environ["perpage"] = "20"

from srht.app import app as flask_app
from srht.database import db as _db
from srht.limiter import limiter
from srht.objects import User


@pytest.fixture
def app():
    # Setup temporary storage
    temp_dir = tempfile.mkdtemp()

    # Configure app for testing
    limiter.enabled = False
    flask_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    # Update environment variables that the app uses via _cfg
    os.environ["storage"] = temp_dir
    os.makedirs(os.path.join(temp_dir, "thumbnails"), exist_ok=True)

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()

    # Cleanup temporary storage
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User("testuser", "test@example.com", "password123")
        user.suspended = False
        _db.session.add(user)
        _db.session.commit()
        # Get apiKey while still in session
        api_key = user.apiKey
        # Return a simple object or ensure it's detached but with loaded attributes
        _db.session.refresh(user)
        _db.session.expunge(user)
        return user
