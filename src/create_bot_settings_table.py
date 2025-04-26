#!/usr/bin/env python
"""
Script to directly create the bot_settings table in the database.
This bypasses Alembic migrations and creates the table directly using SQLAlchemy.
"""
from app.core.db.database import Base, get_db
from app.models.bot_settings import BotSettings
import json
from sqlalchemy import text

def create_bot_settings_table():
    """Create the bot_settings table and insert default data."""
    # Get a database session
    db = next(get_db())
    
    try:
        # Create all tables (including bot_settings)
        Base.metadata.create_all(bind=db.get_bind())
        print("Tables created successfully.")
        
        # Check if bot_settings table has any data
        result = db.query(BotSettings).first()
        
        if result:
            print("Bot settings already exist in the database.")
            return
            
        # Insert default bot settings
        default_quick_actions = [
            {"label": "Return Policy", "value": "What's your return policy?"},
            {"label": "Shipping Info", "value": "How long does shipping take?"},
            {"label": "Product Help", "value": "Tell me about your products"}
        ]
        
        # Create a new BotSettings instance
        bot_settings = BotSettings()
        
        # Set attributes manually
        bot_settings.bot_name = "E-Commerce Support Bot"
        bot_settings.welcome_message = "Hello! I'm your support assistant. How can I help you today?"
        bot_settings.fallback_message = "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?"
        bot_settings.quick_actions = default_quick_actions
        bot_settings.advanced_settings = {"enable_debug": False, "max_tokens": 500}
        
        db.add(bot_settings)
        db.commit()
        
        print("Default bot settings added successfully.")
        
        # Verify the data was inserted
        result = db.query(BotSettings).first()
        if result:
            print(f"Bot Name: {result.bot_name}")
            print(f"Welcome Message: {result.welcome_message}")
            print(f"Quick Actions: {result.quick_actions}")
        
    except Exception as e:
        print(f"Error creating bot_settings table: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    create_bot_settings_table()
