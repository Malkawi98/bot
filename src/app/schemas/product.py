from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class ProductBase(BaseModel):
    """Base product schema with common attributes."""
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    stock_quantity: int = 0
    image_url: Optional[str] = None
    category: Optional[str] = None
    language: str = "en"
    alternative_to_id: Optional[int] = None


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating an existing product."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    language: Optional[str] = None
    alternative_to_id: Optional[int] = None


class ProductInDB(ProductBase):
    """Schema for a product as stored in the database."""
    id: int
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProductResponse(ProductInDB):
    """Schema for product response with alternatives."""
    alternatives: Optional[List["ProductResponse"]] = []

    class Config:
        from_attributes = True
        
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Handle the case when alternatives is None or a Product object instead of a list
        if hasattr(obj, '__dict__'):
            # Create a copy of the object's data
            data = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            
            # Always set alternatives to a list
            if not isinstance(data.get('alternatives'), list):
                data['alternatives'] = []
            elif data.get('alternatives') is None:
                data['alternatives'] = []
                
            # Use the parent's model_validate with our modified data
            return super().model_validate(data, *args, **kwargs)
        return super().model_validate(obj, *args, **kwargs)


# This is needed for the self-referencing type
ProductResponse.model_rebuild()


class ProductList(BaseModel):
    """Schema for a list of products."""
    total: int
    products: List[ProductResponse]
