from fastapi import APIRouter, Depends, HTTPException, Body, status, Request, Response
import auth.crypt_utils as crypt_utils
from auth.auth_bearer import JWTBearer
from auth.auth_handler import signAccessJWT, signRefreshJWT, decodeJWT, ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE
import jwt
from schemas.login import user_login_schema, insert_user
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import engine
from utils.router_utils import *
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

COOKIE_ACCESS = "access_token"
COOKIE_REFRESH = "refresh_token"
COOKIE_PATH = "/"
SAME_SITE = "lax"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key=COOKIE_ACCESS,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE,
        httponly=True,
        samesite=SAME_SITE,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=COOKIE_REFRESH,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE,
        httponly=True,
        samesite=SAME_SITE,
        path=COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response):
    response.set_cookie(key=COOKIE_ACCESS, value="", max_age=0, httponly=True, samesite=SAME_SITE, path=COOKIE_PATH)
    response.set_cookie(key=COOKIE_REFRESH, value="", max_age=0, httponly=True, samesite=SAME_SITE, path=COOKIE_PATH)


def _read_token_from_cookie(request: Request, cookie_name: str = COOKIE_ACCESS) -> str | None:
    return request.cookies.get(cookie_name)


@router.post("/login")
def user_login(body: user_login_schema = Body(...), db: Session = Depends(get_db), response: Response = None):
    user = crud.get_user(db, body.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    hashed_pass = user.password

    if not crypt_utils.verify_password(body.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    user_id_str = str(user.id)
    access_token = signAccessJWT(user_id_str, user.name, user.username)
    refresh_token = signRefreshJWT(user_id_str)

    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/refresh")
def refresh_tokens(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = _read_token_from_cookie(request, COOKIE_REFRESH)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decodeJWT(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    jti = payload.get("jti")
    if jti and crud.is_token_revoked(db, jti):
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    crud.revoke_token(db, jti, int(payload["user_id"]), datetime.fromtimestamp(payload["expires"]))

    user_id_str = str(payload["user_id"])
    new_access = signAccessJWT(user_id_str, payload.get("name", ""), payload.get("username", ""))
    new_refresh = signRefreshJWT(user_id_str)

    _set_auth_cookies(response, new_access, new_refresh)

    return {
        "access_token": new_access,
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = _read_token_from_cookie(request, COOKIE_REFRESH)
    if refresh_token:
        payload = decodeJWT(refresh_token)
        if payload and payload.get("jti"):
            crud.revoke_token(
                db,
                payload["jti"],
                int(payload.get("user_id", 0)),
                datetime.fromtimestamp(payload["expires"]),
            )

    _clear_auth_cookies(response)
    return {"detail": "Logged out successfully"}


@router.get("/session")
def get_session(request: Request, response: Response, db: Session = Depends(get_db)):
    access_token = _read_token_from_cookie(request, COOKIE_ACCESS)

    if access_token:
        payload = decodeJWT(access_token)
        if payload and payload.get("type") == "access":
            return {
                "authenticated": True,
                "access_token": access_token,
            }

    refresh_token = _read_token_from_cookie(request, COOKIE_REFRESH)
    if refresh_token:
        payload = decodeJWT(refresh_token)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti")
            if jti and crud.is_token_revoked(db, jti):
                _clear_auth_cookies(response)
                return {"authenticated": False}

            crud.revoke_token(db, jti, int(payload["user_id"]), datetime.fromtimestamp(payload["expires"]))

            user_id_str = str(payload["user_id"])
            new_access = signAccessJWT(user_id_str, "", "")
            new_refresh = signRefreshJWT(user_id_str)
            _set_auth_cookies(response, new_access, new_refresh)

            return {
                "authenticated": True,
                "access_token": new_access,
            }

    _clear_auth_cookies(response)
    return {"authenticated": False}


@router.get("/user")
def get_user_data(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user_data: str = Depends(JWTBearer()),
):
    data = decodeJWT(user_data)

    return data


@router.post("/user")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user.password = crypt_utils.get_hashed_password(user.password)
    db_user = crud.get_user(db, user.username)

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    return crud.create_user(db=db, user=user)
