from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.core.db.database import get_db
from app.core.bot_settings import get_bot_settings_model, update_bot_settings
from app.models.bot_settings import BotSettings
from pydantic import BaseModel

router = APIRouter(tags=["bot_settings"])


class QuickAction(BaseModel):
    label: str
    value: str
    icon: Optional[str] = None


class AdvancedSettings(BaseModel):
    response_time: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    max_message_length: Optional[int] = None


class BotSettingsUpdate(BaseModel):
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    fallback_message: Optional[str] = None
    quick_actions: Optional[List[QuickAction]] = None
    advanced_settings: Optional[AdvancedSettings] = None


class BotSettingsResponse(BaseModel):
    id: int
    bot_name: str
    welcome_message: str
    fallback_message: str
    quick_actions: List[QuickAction]
    advanced_settings: Dict[str, Any]


@router.get("/bot-settings", response_model=BotSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """
    Get the current bot settings
    """
    try:
        # Try to get settings from database
        settings = get_bot_settings_model(db)
        
        # Convert to response model
        return BotSettingsResponse(
            id=settings.id,
            bot_name=settings.bot_name,
            welcome_message=settings.welcome_message,
            fallback_message=settings.fallback_message,
            quick_actions=settings.quick_actions or [],
            advanced_settings=settings.advanced_settings or {}
        )
    except Exception as e:
        # If database connection fails, use file-based fallback
        print(f"Error getting bot settings from database: {e}. Using file-based fallback.")
        from app.core.bot_settings import get_bot_settings_from_file
        
        # Get settings from file
        file_settings = get_bot_settings_from_file()
        
        # Convert to response model
        return BotSettingsResponse(
            id=1,  # Default ID for file-based settings
            bot_name=file_settings.get("bot_name", ""),
            welcome_message=file_settings.get("welcome_message", ""),
            fallback_message=file_settings.get("fallback_message", ""),
            quick_actions=file_settings.get("quick_actions", []),
            advanced_settings=file_settings.get("advanced_settings", {})
        )


@router.put("/bot-settings", response_model=BotSettingsResponse)
def update_settings(settings_update: BotSettingsUpdate, db: Session = Depends(get_db)):
    """
    Update bot settings
    """
    try:
        # Try to update settings in database
        # Get current settings
        current_settings = get_bot_settings_model(db)
        
        # Prepare quick actions and advanced settings
        quick_actions = None
        if settings_update.quick_actions:
            quick_actions = [action.dict() for action in settings_update.quick_actions]
            
        advanced_settings = None
        if settings_update.advanced_settings:
            advanced_settings = settings_update.advanced_settings.dict()
        
        # Update settings
        success = update_bot_settings(
            db=db,
            bot_name=settings_update.bot_name,
            welcome_message=settings_update.welcome_message,
            fallback_message=settings_update.fallback_message,
            quick_actions=quick_actions,
            advanced_settings=advanced_settings
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update bot settings")
        
        # Get updated settings
        updated_settings = get_bot_settings_model(db)
        
        # Convert to response model
        return BotSettingsResponse(
            id=updated_settings.id,
            bot_name=updated_settings.bot_name,
            welcome_message=updated_settings.welcome_message,
            fallback_message=updated_settings.fallback_message,
            quick_actions=updated_settings.quick_actions or [],
            advanced_settings=updated_settings.advanced_settings or {}
        )
    except Exception as e:
        # If database connection fails, use file-based fallback
        print(f"Error updating bot settings in database: {e}. Using file-based fallback.")
        from app.core.bot_settings import update_bot_settings as file_update_bot_settings, get_bot_settings_from_file
        
        # Update settings in file
        settings_dict = {}
        if settings_update.bot_name is not None:
            settings_dict["bot_name"] = settings_update.bot_name
        if settings_update.welcome_message is not None:
            settings_dict["welcome_message"] = settings_update.welcome_message
        if settings_update.fallback_message is not None:
            settings_dict["fallback_message"] = settings_update.fallback_message
        if settings_update.quick_actions is not None:
            settings_dict["quick_actions"] = [action.dict() for action in settings_update.quick_actions]
        if settings_update.advanced_settings is not None:
            settings_dict["advanced_settings"] = settings_update.advanced_settings.dict()
        
        # Update file-based settings
        success = file_update_bot_settings(None, **settings_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update bot settings in file")
        
        # Get updated settings from file
        file_settings = get_bot_settings_from_file()
        
        # Convert to response model
        return BotSettingsResponse(
            id=1,  # Default ID for file-based settings
            bot_name=file_settings.get("bot_name", ""),
            welcome_message=file_settings.get("welcome_message", ""),
            fallback_message=file_settings.get("fallback_message", ""),
            quick_actions=file_settings.get("quick_actions", []),
            advanced_settings=file_settings.get("advanced_settings", {})
        )
