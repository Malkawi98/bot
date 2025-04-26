#!/usr/bin/env python
"""
Script to initialize the database tables for the E-Commerce Support Bot.
This creates all the necessary tables in the database.
"""
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent.parent
sys.path.append(str(src_path))

from sqlalchemy import create_engine
from app.core.db.database import Base
from app.models.product import Product  # Import all models to ensure they're registered

# Create a direct connection to the database
DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
engine = create_engine(DATABASE_URL)

def init_db():
    """Initialize the database by creating all tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Successfully created database tables.")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == "__main__":
    init_db()
