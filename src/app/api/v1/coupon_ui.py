from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.db.database import get_db
from app.api.deps import get_current_user
import os

router = APIRouter(tags=["coupon-ui"])

# Set up templates
templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_path)

@router.get("/coupon-management", response_class=HTMLResponse)
async def coupon_management_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Render the coupon management page."""
    # For development purposes, authentication is temporarily disabled
    # In production, uncomment the following line:
    # current_user = Depends(get_current_user)
    
    return templates.TemplateResponse(
        "coupon_management.html",
        {"request": request}
    )

@router.get("/coupon-test", response_class=HTMLResponse)
async def coupon_test_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Render the coupon test page for testing the coupon API."""
    
    return templates.TemplateResponse(
        "coupon_test.html",
        {"request": request}
    )
