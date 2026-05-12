from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from flask import current_app

ADMIN_REAUTH_COOKIE_NAME = "admin_reauth"
ADMIN_REAUTH_COOKIE_PATH = "/admin"
ADMIN_REAUTH_MAX_AGE_SECONDS = 900
ADMIN_REAUTH_SALT = "srht-admin-reauth-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.secret_key, salt=ADMIN_REAUTH_SALT)


def issue_admin_reauth_cookie(response, user_id: int) -> None:
    token = _serializer().dumps({"uid": user_id})
    response.set_cookie(
        ADMIN_REAUTH_COOKIE_NAME,
        token,
        max_age=ADMIN_REAUTH_MAX_AGE_SECONDS,
        httponly=True,
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
        samesite="Strict",
        path=ADMIN_REAUTH_COOKIE_PATH,
    )


def clear_admin_reauth_cookie(response) -> None:
    response.delete_cookie(ADMIN_REAUTH_COOKIE_NAME, path=ADMIN_REAUTH_COOKIE_PATH)


def verify_admin_reauth_cookie(token: str, expected_user_id: int) -> bool:
    if not token:
        return False

    try:
        payload = _serializer().loads(token, max_age=ADMIN_REAUTH_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False

    return payload.get("uid") == expected_user_id
