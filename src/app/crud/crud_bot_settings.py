from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from app.models.bot_settings import BotSettings


def get_bot_settings(db: Session) -> Optional[BotSettings]:
    """
    Get the bot settings from the database.
    If no settings exist, return None.
    
    Args:
        db: Database session
        
    Returns:
        BotSettings object or None
    """
    return db.query(BotSettings).first()


def create_bot_settings(
    db: Session,
    bot_name: str,
    welcome_message: str,
    fallback_message: str,
    quick_actions: Optional[List[Dict[str, str]]] = None,
    advanced_settings: Optional[Dict[str, Any]] = None
) -> BotSettings:
    """
    Create new bot settings in the database
    
    Args:
        db: Database session
        bot_name: Name of the bot
        welcome_message: Welcome message to display
        fallback_message: Fallback message when bot doesn't understand
        quick_actions: List of quick action buttons
        advanced_settings: Additional configuration options
        
    Returns:
        BotSettings object
    """
    db_settings = BotSettings(
        bot_name=bot_name,
        welcome_message=welcome_message,
        fallback_message=fallback_message,
        quick_actions=quick_actions or [],
        advanced_settings=advanced_settings or {}
    )
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings


def update_bot_settings(
    db: Session,
    bot_settings_id: int,
    bot_name: Optional[str] = None,
    welcome_message: Optional[str] = None,
    fallback_message: Optional[str] = None,
    quick_actions: Optional[List[Dict[str, str]]] = None,
    advanced_settings: Optional[Dict[str, Any]] = None
) -> Optional[BotSettings]:
    """
    Update existing bot settings
    
    Args:
        db: Database session
        bot_settings_id: ID of the settings to update
        bot_name: Name of the bot
        welcome_message: Welcome message to display
        fallback_message: Fallback message when bot doesn't understand
        quick_actions: List of quick action buttons
        advanced_settings: Additional configuration options
        
    Returns:
        Updated BotSettings object or None if not found
    """
    print(f"Updating bot settings with ID {bot_settings_id}")
    print(f"Advanced settings: {advanced_settings}")
    
    db_settings = db.query(BotSettings).filter(BotSettings.id == bot_settings_id).first()
    if not db_settings:
        print(f"No bot settings found with ID {bot_settings_id}")
        return None
    
    update_data = {}
    if bot_name is not None:
        update_data["bot_name"] = bot_name
    if welcome_message is not None:
        update_data["welcome_message"] = welcome_message
    if fallback_message is not None:
        update_data["fallback_message"] = fallback_message
    if quick_actions is not None:
        update_data["quick_actions"] = quick_actions
    
    if advanced_settings is not None:
        # Merge with existing advanced settings
        current_advanced = db_settings.advanced_settings or {}
        print(f"Current advanced settings: {current_advanced}")
        current_advanced.update(advanced_settings)
        update_data["advanced_settings"] = current_advanced
        print(f"Updated advanced settings: {current_advanced}")
    
    print(f"Updating with data: {update_data}")
    
    try:
        for key, value in update_data.items():
            setattr(db_settings, key, value)
        
        db.commit()
        db.refresh(db_settings)
        print("Update successful!")
        return db_settings
    except Exception as e:
        print(f"Error updating bot settings: {e}")
        db.rollback()
        return None


def get_or_create_default_settings(db: Session) -> BotSettings:
    """
    Get the bot settings or create default ones if they don't exist
    
    Args:
        db: Database session
        
    Returns:
        BotSettings object
    """
    db_settings = get_bot_settings(db)
    if db_settings:
        return db_settings
    
    # Create default settings
    return create_bot_settings(
        db=db,
        bot_name="E-Commerce Support Bot",
        welcome_message="Hello! I'm your support assistant. How can I help you today?",
        fallback_message="I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
        quick_actions=[
            {"label": "Track Order", "value": "Track my order!"},
            {"label": "Return Item", "value": "I want to return an item"},
            {"label": "Talk to Human", "value": "I want to talk to a human agent"}
        ],
        advanced_settings={
            "response_time": "immediate",
            "language": "en",
            "tone": "friendly",
            "max_message_length": 500
        }
    )
