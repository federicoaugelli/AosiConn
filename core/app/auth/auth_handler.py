import time
import uuid
from typing import Dict
import jwt
from decouple import config

JWT_SECRET = config("JWT_SECRET_KEY", default="change-me-in-production")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE = 60 * 60 * 2        # 2 hours
REFRESH_TOKEN_EXPIRE = 60 * 60 * 24 * 7  # 7 days


def token_response(access_token: str, refresh_token: str | None = None):
    body: dict = {"access_token": access_token}
    if refresh_token:
        body["refresh_token"] = refresh_token
    return body


def signAccessJWT(user_id: str, name: str, username: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "name": name,
        "username": username,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "expires": time.time() + ACCESS_TOKEN_EXPIRE,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def signRefreshJWT(user_id: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "expires": time.time() + REFRESH_TOKEN_EXPIRE,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except:
        return {}
