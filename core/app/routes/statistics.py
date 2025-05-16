from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/")
async def statistics() -> Dict:
    return {
        "stat": "Work in progress"
    }

