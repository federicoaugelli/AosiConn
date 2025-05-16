from auth.auth_handler import decodeJWT
from db.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_id(user_id: str):
    return decodeJWT(user_id)['user_id']


