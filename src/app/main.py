from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api import router as api_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.auth_ui import router as auth_ui_router
from app.api.v1.rag import router as rag_router
from app.api.v1.vector_store import router as vector_store_router
from app.api.v1.bot_settings import router as bot_settings_router
from app.api.v1.vector_store_debug import router as vector_store_debug_router
from app.api.v1.product_ui import router as product_ui_router
from app.api.v1.bot import router as bot_router
from app.api.v1.coupon import router as coupon_router
from app.api.v1.coupon_ui import router as coupon_ui_router
from app.api.v1.order import router as order_router
from app.core.config import settings
from app.core.setup import create_application

# Create the main application
app = create_application(router=api_router, settings=settings)

# Mount static files directory
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include UI routers directly at the root level
app.include_router(dashboard_router)
app.include_router(auth_ui_router)
app.include_router(product_ui_router)
app.include_router(coupon_ui_router)

# Include the RAG API router
app.include_router(rag_router, prefix="/api/v1")

# Include the Vector Store API router
app.include_router(vector_store_router, prefix="/api/v1")

# Include the Vector Store Debug API router
app.include_router(vector_store_debug_router, prefix="/api/v1")

# Include the Bot Settings API router
app.include_router(bot_settings_router, prefix="/api/v1")

# Include the Bot API router
app.include_router(bot_router, prefix="/api/v1")

# Include the Coupon API router
app.include_router(coupon_router, prefix="/api/v1")

# Include the Order API router
app.include_router(order_router, prefix="/api/v1")

# Add favicon route
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(static_dir / 'favicon.ico')
