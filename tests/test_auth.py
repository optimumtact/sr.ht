from srht.database import db
from srht.objects import User


def test_suspended_user_cannot_login(client, app):
    with app.app_context():
        user = User("suspended_user", "suspended@example.com", "password123")
        user.suspended = True
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={"username": "suspended_user", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Your account is suspended. Please contact the site owner." in response.data
