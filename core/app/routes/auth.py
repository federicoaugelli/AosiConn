from fastapi import APIRouter, Depends, HTTPException, Body, status
import auth.crypt_utils as crypt_utils
from auth.auth_bearer import JWTBearer
from auth.auth_handler import signJWT
import jwt
from schemas.login import user_login_schema, insert_user
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import engine
from utils.router_utils import *

models.Base.metadata.create_all(bind=engine)

router = APIRouter()


@router.post("/login")
def user_login(body: user_login_schema = Body(...), db: Session = Depends(get_db)):
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
   
    return signJWT(user.id, user.name, user.username)

@router.post("/user")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user.password = crypt_utils.get_hashed_password(user.password)
    db_user = crud.get_user(db, user.username)

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    return crud.create_user(db=db, user=user)

@router.get("/user")
def get_user_data(user_data: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer())):
    data = decodeJWT(user_data)
    
    return data



