from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Change template directory for Docker compatibility
templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["auth-ui"])

@router.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login page for the admin dashboard
    """
    return templates.TemplateResponse(request, "login.html")
