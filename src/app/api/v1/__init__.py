from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
# from app.api.v1.posts import router as posts_router
# from .tiers import router as tiers_router
from .users import router as users_router
from .rag import router as rag_router
from .rag_ui import router as rag_ui_router
from .bot import router as bot_router
from .bot_settings import router as bot_settings_router
from .dashboard import router as dashboard_router
from .dashboard_api import router as dashboard_api_router
from .auth_ui import router as auth_ui_router

router = APIRouter(prefix="/v1")
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(users_router)
# router.include_router(posts_router)
# router.include_router(tiers_router)
router.include_router(rag_router)
router.include_router(rag_ui_router)
router.include_router(bot_router)
router.include_router(bot_settings_router)
router.include_router(dashboard_router)
router.include_router(dashboard_api_router)
router.include_router(auth_ui_router)
