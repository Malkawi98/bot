from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

# Import templates from the centralized configuration
from app.core.template_config import templates
router = APIRouter(tags=["auth-ui"])

@router.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login page for the admin dashboard
    """
    return templates.TemplateResponse(request, "login.html")
