from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/", include_in_schema=False)
async def statistics() -> Dict:
    return {
        "stat": "Work in progress"
    }

