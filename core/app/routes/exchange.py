from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from exchange import bitmex
from auth.auth_bearer import JWTBearer
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import engine
from utils.router_utils import *
import os

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

@router.get("/list/")
async def get_exchanges() -> Dict:
    raw_exchanges = os.listdir("exchange")
    exchanges = [file[:-3] for file in raw_exchanges if file.endswith(".py")]
    return {
        "exchanges": exchanges
    }

@router.get("/balance/")
def get_balance(exchange: str, currency: str, user_id: str = Depends(JWTBearer()), dependencies=Depends(JWTBearer()), db: Session = Depends(get_db)):
    uid = get_user_id(user_id)
    _exchange = globals().get(exchange)
    if _exchange:
        key = crud.get_key(db, uid, exchange)
        if key:
            balance = _exchange.get_balance(key.api_key, key.api_secret, currency)
            return balance
        else:
            raise HTTPException(status_code=404, detail="No key found for exchange")
    else:
        raise HTTPException(status_code=404, detail="Exchange not found")

@router.get("/quote/")
def get_quote(exchange: str, pair: str, size: str, count: int):

    _exchange = globals().get(exchange)
    if _exchange:
        quote = _exchange.get_data(size, pair, count)
        return quote
    else:
        raise HTTPException(status_code=404, detail="Exchange not found")
