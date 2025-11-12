from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/", include_in_schema=False)
async def read_root() -> Dict:
    return {
        "Status": "We are trading!!!"
    }

@router.get("/internal/")
async def read_internal() -> Dict:
    return {
        "Status": "We are trading internally!!!"
    }
