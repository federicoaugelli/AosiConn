from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from auth.auth_bearer import JWTBearer
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import engine
from utils.router_utils import *
import os

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

@router.get("/")
async def get_api_key(exchange: str | None = None, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer()), db: Session = Depends(get_db)):
    uid = get_user_id(user_id)
    if exchange == None:
        key = crud.get_keys(db, uid)
    else:
        key = crud.get_key(db, uid, exchange)

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    return key

@router.post("/")
async def create_api_key(key_schema: schemas.KeyBase, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer()), db: Session = Depends(get_db)):
    # Retrieve all exchanges to check if available
    raw_exchanges = os.listdir("exchange")
    exchanges = [file[:-3] for file in raw_exchanges if file.endswith(".py")]

    if key_schema.exchange not in exchanges:
        raise HTTPException(status_code=404, detail="Exchange doesn't exists")

    uid = get_user_id(user_id)
    key_check = crud.get_key(db, uid, key_schema.exchange)

    if key_check:
        raise HTTPException(status_code=409, detail="Key already exists")

    key = crud.create_key(db, key_schema, uid)
    return key

@router.put("/")
async def update_api_key(key_schema: schemas.KeyBase, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer()), db: Session = Depends(get_db)):
    uid = get_user_id(user_id)
    
    key = crud.get_key(db, uid, key_schema.exchange)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    key = crud.modify_key(db, uid, key_schema.exchange, key_schema.api_key, key_schema.api_secret)
    return key

@router.delete("/")
async def delete_api_key(exchange: str, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer()), db: Session = Depends(get_db)):
    uid = get_user_id(user_id)

    key = crud.get_key(db, uid, exchange)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    key = crud.delete_key(db, uid, exchange)
    return {"Hello": "World"}
