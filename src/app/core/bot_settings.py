"""
Bot settings utility module for reading and writing bot configuration from database
with file-based fallback for local development
"""
from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path
from fastapi import Depends
from sqlalchemy.orm import Session
import logging

from app.core.db.database import get_db
from app.crud.crud_bot_settings import get_or_create_default_settings as db_get_settings, update_bot_settings as db_update_settings
from app.models.bot_settings import BotSettings

# Set up logging
logger = logging.getLogger(__name__)

# Path for fallback JSON file
BOT_SETTINGS_FILE = Path(__file__).parent.parent.parent / "data" / "bot_settings.json"

# Create data directory if it doesn't exist
os.makedirs(BOT_SETTINGS_FILE.parent, exist_ok=True)

# Default settings
DEFAULT_SETTINGS = {
    "bot_name": "E-Commerce Support Bot",
    "welcome_message": "Hello! I'm your support assistant. How can I help you today?",
    "fallback_message": "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
    "quick_actions": [
        {"label": "Track Order", "value": "Track my order"},
        {"label": "Return Item", "value": "I want to return an item"},
        {"label": "Talk to Human", "value": "I want to talk to a human agent"}
    ],
    "advanced_settings": {
        "response_time": "immediate",
        "language": "en",
        "tone": "friendly",
        "max_message_length": 500
    }
}


def get_bot_settings_from_file() -> Dict[str, Any]:
    """
    Read bot settings from the JSON file
    
    Returns:
        Dict[str, Any]: The bot settings
    """
    try:
        if BOT_SETTINGS_FILE.exists():
            with open(BOT_SETTINGS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default settings file
            with open(BOT_SETTINGS_FILE, 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=4)
            return DEFAULT_SETTINGS
    except Exception as e:
        logger.error(f"Error reading bot settings file: {e}")
        return DEFAULT_SETTINGS


def get_bot_settings(db: Session = None) -> Dict[str, Any]:
    """
    Read bot settings from the database with file fallback
    
    Args:
        db: Database session (optional)
    
    Returns:
        Dict[str, Any]: The bot settings
    """
    try:
        if db is not None:
            # Get or create default settings from database
            settings = db_get_settings(db)
            
            # Convert to dictionary format
            return {
                "bot_name": settings.bot_name,
                "welcome_message": settings.welcome_message,
                "fallback_message": settings.fallback_message,
                "quick_actions": settings.quick_actions or [],
                "advanced_settings": settings.advanced_settings or {}
            }
        else:
            # Fallback to file-based settings
            return get_bot_settings_from_file()
    except Exception as e:
        logger.error(f"Error getting bot settings from database: {e}")
        # Fallback to file-based settings
        return get_bot_settings_from_file()


def save_bot_settings_to_file(settings: Dict[str, Any]) -> bool:
    """
    Save bot settings to the JSON file
    
    Args:
        settings (Dict[str, Any]): The bot settings to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(BOT_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving bot settings to file: {e}")
        return False


def save_bot_settings(settings: Dict[str, Any], db: Session = None) -> bool:
    """
    Save bot settings to the database with file fallback
    
    Args:
        settings (Dict[str, Any]): The bot settings to save
        db: Database session (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if db is not None:
            # Get current settings from database
            db_settings = db_get_settings(db)
            
            # Update settings in database
            updated = db_update_settings(
                db=db,
                bot_settings_id=db_settings.id,
                bot_name=settings.get("bot_name"),
                welcome_message=settings.get("welcome_message"),
                fallback_message=settings.get("fallback_message"),
                quick_actions=settings.get("quick_actions"),
                advanced_settings=settings.get("advanced_settings")
            )
            
            success = updated is not None
            
            # Also save to file as backup
            save_bot_settings_to_file(settings)
            
            return success
        else:
            # Fallback to file-based settings
            return save_bot_settings_to_file(settings)
    except Exception as e:
        logger.error(f"Error saving bot settings to database: {e}")
        # Fallback to file-based settings
        return save_bot_settings_to_file(settings)


def update_bot_settings(
    bot_name: Optional[str] = None,
    welcome_message: Optional[str] = None,
    fallback_message: Optional[str] = None,
    quick_actions: Optional[List[Dict[str, str]]] = None,
    advanced_settings: Optional[Dict[str, Any]] = None,
    db: Session = None
) -> bool:
    """
    Update specific bot settings with file fallback
    
    Args:
        bot_name (Optional[str]): The bot name
        welcome_message (Optional[str]): The welcome message
        fallback_message (Optional[str]): The fallback message
        quick_actions (Optional[List[Dict[str, str]]]): The quick actions
        advanced_settings (Optional[Dict[str, Any]]): Advanced settings
        db: Database session (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"Core update_bot_settings called with DB: {db is not None}")
    print(f"Advanced settings: {advanced_settings}")
    
    try:
        if db is not None:
            # Get current settings from database
            db_settings = db_get_settings(db)
            print(f"Retrieved current settings from DB, ID: {db_settings.id}")
            
            # Update settings in database
            updated = db_update_settings(
                db=db,
                bot_settings_id=db_settings.id,
                bot_name=bot_name,
                welcome_message=welcome_message,
                fallback_message=fallback_message,
                quick_actions=quick_actions,
                advanced_settings=advanced_settings
            )
            
            success = updated is not None
            print(f"DB update success: {success}")
            
            # Also update file-based settings
            if success:
                current_settings = get_bot_settings_from_file()
                if bot_name is not None:
                    current_settings["bot_name"] = bot_name
                if welcome_message is not None:
                    current_settings["welcome_message"] = welcome_message
                if fallback_message is not None:
                    current_settings["fallback_message"] = fallback_message
                if quick_actions is not None:
                    current_settings["quick_actions"] = quick_actions
                if advanced_settings is not None:
                    if "advanced_settings" not in current_settings:
                        current_settings["advanced_settings"] = {}
                    current_settings["advanced_settings"].update(advanced_settings)
                save_bot_settings_to_file(current_settings)
                print("Updated file-based settings")
            
            return success
        else:
            # Fallback to file-based settings
            current_settings = get_bot_settings_from_file()
            if bot_name is not None:
                current_settings["bot_name"] = bot_name
            if welcome_message is not None:
                current_settings["welcome_message"] = welcome_message
            if fallback_message is not None:
                current_settings["fallback_message"] = fallback_message
            if quick_actions is not None:
                current_settings["quick_actions"] = quick_actions
            if advanced_settings is not None:
                if "advanced_settings" not in current_settings:
                    current_settings["advanced_settings"] = {}
                current_settings["advanced_settings"].update(advanced_settings)
            return save_bot_settings_to_file(current_settings)
    except Exception as e:
        logger.error(f"Error updating bot settings: {e}")
        # Fallback to file-based settings
        current_settings = get_bot_settings_from_file()
        if bot_name is not None:
            current_settings["bot_name"] = bot_name
        if welcome_message is not None:
            current_settings["welcome_message"] = welcome_message
        if fallback_message is not None:
            current_settings["fallback_message"] = fallback_message
        if quick_actions is not None:
            current_settings["quick_actions"] = quick_actions
        if advanced_settings is not None:
            if "advanced_settings" not in current_settings:
                current_settings["advanced_settings"] = {}
            current_settings["advanced_settings"].update(advanced_settings)
        return save_bot_settings_to_file(current_settings)


class FileBotSettings:
    """
    A class that mimics the BotSettings database model but uses file-based storage
    """
    def __init__(self, settings: Dict[str, Any]):
        self.id = 1  # Default ID
        self.bot_name = settings.get("bot_name", DEFAULT_SETTINGS["bot_name"])
        self.welcome_message = settings.get("welcome_message", DEFAULT_SETTINGS["welcome_message"])
        self.fallback_message = settings.get("fallback_message", DEFAULT_SETTINGS["fallback_message"])
        self.quick_actions = settings.get("quick_actions", DEFAULT_SETTINGS["quick_actions"])
        self.advanced_settings = settings.get("advanced_settings", DEFAULT_SETTINGS["advanced_settings"])


def get_bot_settings_model(db: Session = None) -> BotSettings:
    """
    Get the bot settings model directly with file fallback
    
    Args:
        db: Database session (optional)
        
    Returns:
        BotSettings or FileBotSettings: The bot settings model
    """
    try:
        if db is not None:
            return db_get_settings(db)
        else:
            # Fallback to file-based settings
            settings = get_bot_settings_from_file()
            return FileBotSettings(settings)
    except Exception as e:
        logger.error(f"Error getting bot settings model: {e}")
        # Fallback to file-based settings
        settings = get_bot_settings_from_file()
        return FileBotSettings(settings)
