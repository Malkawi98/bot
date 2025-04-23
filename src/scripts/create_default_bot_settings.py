#!/usr/bin/env python3
"""
Script to create default bot settings in the database
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.bot_settings import BotSettings


async def create_default_bot_settings():
    """Create default bot settings if they don't exist"""
    # Create async engine
    engine = create_async_engine(settings.sqlalchemy_async_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create default quick actions
    default_quick_actions = [
        {"label": "Track Order", "value": "Track my order!"},
        {"label": "Return Item", "value": "I want to return an item"},
        {"label": "Talk to Human", "value": "I want to talk to a human agent"}
    ]

    async with async_session() as session:
        # Check if bot settings already exist
        result = await session.execute(select(BotSettings))
        existing_settings = result.scalars().first()

        if not existing_settings:
            # Create default bot settings
            bot_settings = BotSettings(
                bot_name="E-Commerce Support Bot",
                welcome_message="Hello! I'm your support assistant. How can I help you today?",
                fallback_message="I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
                quick_actions=default_quick_actions,
                advanced_settings={
                    "response_time": "immediate",
                    "language": "en",
                    "tone": "friendly",
                    "max_message_length": 500
                }
            )
            session.add(bot_settings)
            await session.commit()
            print("Default bot settings created successfully")
        else:
            print("Bot settings already exist, no changes made")


def main():
    """Run the async function to create default bot settings"""
    asyncio.run(create_default_bot_settings())


if __name__ == "__main__":
    main()
