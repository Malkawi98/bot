from sqlalchemy import Column, String, Integer, Text, JSON
from app.core.db.database import Base


class BotSettings(Base):
    """
    Model for storing bot configuration settings
    """
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True, index=True)
    bot_name = Column(String(255), nullable=False, default="E-Commerce Support Bot")
    welcome_message = Column(Text, nullable=False, default="Hello! I'm your support assistant. How can I help you today?")
    fallback_message = Column(Text, nullable=False, default="I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?")
    quick_actions = Column(JSON, nullable=True)
    
    # Additional configuration options can be added here
    advanced_settings = Column(JSON, nullable=True)
