from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return FileResponse("static/dashboard.html")

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page():
    return FileResponse("static/login.html")
    
