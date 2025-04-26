from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.db.database import Base
from typing import List, Optional
from datetime import datetime


class Product(Base):
    """Product model for e-commerce items."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    stock_quantity = Column(Integer, default=0)
    image_url = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())
    
    # For multilingual support
    language = Column(String(10), default="en")
    
    # For product alternatives
    alternative_to_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    alternatives = relationship("Product", 
                               foreign_keys=[alternative_to_id],
                               backref="alternative_to",
                               remote_side=[id])
