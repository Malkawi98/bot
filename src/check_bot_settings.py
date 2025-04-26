#!/usr/bin/env python
"""
Script to check if the bot_settings table exists and contains data.
"""
from app.core.db.database import get_db
from sqlalchemy import text

def check_bot_settings():
    """Check if the bot_settings table exists and contains data."""
    # Get a database session
    db = next(get_db())
    
    try:
        # Check if the table exists (PostgreSQL syntax)
        result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'bot_settings'"))
        tables = result.fetchall()
        
        if not tables:
            print("The bot_settings table does not exist.")
            return
            
        print("The bot_settings table exists.")
        
        # Check the data in the table
        result = db.execute(text("SELECT * FROM bot_settings"))
        rows = result.fetchall()
        
        if not rows:
            print("The bot_settings table is empty.")
            return
            
        print(f"Found {len(rows)} row(s) in the bot_settings table:")
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Bot Name: {row[1]}")
            print(f"Welcome Message: {row[2]}")
            print(f"Fallback Message: {row[3]}")
            print(f"Quick Actions: {row[4]}")
            print(f"Advanced Settings: {row[5]}")
    
    except Exception as e:
        print(f"Error checking bot_settings table: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_bot_settings()
