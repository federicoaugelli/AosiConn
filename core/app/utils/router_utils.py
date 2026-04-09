from auth.auth_handler import decodeJWT
from db.database import SessionLocal
from fastapi import HTTPException


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_id(user_id: str):
    payload = decodeJWT(user_id)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token or expired token.")
    return payload["user_id"]
