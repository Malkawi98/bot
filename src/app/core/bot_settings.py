"""
Bot settings utility module for reading and writing bot configuration
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Path to the bot settings JSON file
BOT_SETTINGS_FILE = Path(__file__).parent.parent / "data" / "bot_settings.json"

def get_bot_settings() -> Dict[str, Any]:
    """
    Read bot settings from the JSON file
    
    Returns:
        Dict[str, Any]: The bot settings
    """
    if not os.path.exists(BOT_SETTINGS_FILE):
        # Return default settings if file doesn't exist
        return {
            "bot_name": "E-Commerce Support Bot",
            "welcome_message": "Hello! I'm your support assistant. How can I help you today?",
            "fallback_message": "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
            "quick_actions": [
                {"label": "Track Order", "value": "Track my order!"},
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
    
    try:
        with open(BOT_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading bot settings: {e}")
        # Return default settings if there's an error
        return {
            "bot_name": "E-Commerce Support Bot",
            "welcome_message": "Hello! I'm your support assistant. How can I help you today?",
            "fallback_message": "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
            "quick_actions": [],
            "advanced_settings": {}
        }

def save_bot_settings(settings: Dict[str, Any]) -> bool:
    """
    Save bot settings to the JSON file
    
    Args:
        settings (Dict[str, Any]): The bot settings to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(BOT_SETTINGS_FILE), exist_ok=True)
        
        with open(BOT_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving bot settings: {e}")
        return False

def update_bot_settings(
    bot_name: Optional[str] = None,
    welcome_message: Optional[str] = None,
    fallback_message: Optional[str] = None,
    quick_actions: Optional[List[Dict[str, str]]] = None,
    advanced_settings: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update specific bot settings
    
    Args:
        bot_name (Optional[str]): The bot name
        welcome_message (Optional[str]): The welcome message
        fallback_message (Optional[str]): The fallback message
        quick_actions (Optional[List[Dict[str, str]]]): The quick actions
        advanced_settings (Optional[Dict[str, Any]]): Advanced settings
        
    Returns:
        bool: True if successful, False otherwise
    """
    current_settings = get_bot_settings()
    
    if bot_name is not None:
        current_settings["bot_name"] = bot_name
    
    if welcome_message is not None:
        current_settings["welcome_message"] = welcome_message
    
    if fallback_message is not None:
        current_settings["fallback_message"] = fallback_message
    
    if quick_actions is not None:
        current_settings["quick_actions"] = quick_actions
    
    if advanced_settings is not None:
        # Update only the provided advanced settings
        if "advanced_settings" not in current_settings:
            current_settings["advanced_settings"] = {}
        
        for key, value in advanced_settings.items():
            current_settings["advanced_settings"][key] = value
    
    return save_bot_settings(current_settings)
