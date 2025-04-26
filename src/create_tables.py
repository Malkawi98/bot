#!/usr/bin/env python3

import os
import sys

# Add the src directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.db.database import Base, sync_engine

# Import all models to register them with the Base metadata
from app.models.product import Product
from app.models.coupon import Coupon
from app.models.user import User
from app.models.post import Post
from app.models.bot_settings import BotSettings
from app.models.tier import Tier
# Import any other models you have

def create_all_tables():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=sync_engine)
    print("Database tables created!")

if __name__ == "__main__":
    create_all_tables() 