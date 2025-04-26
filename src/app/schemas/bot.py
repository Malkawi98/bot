from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class BotMessageRequest(BaseModel):
    message: str
    language: Optional[str] = "en"  # Default to English, can be 'ar' for Arabic
    session_data: Optional[Dict[str, Any]] = None

class QuickAction(BaseModel):
    label: str
    value: str
    icon: Optional[str] = None

class ProductInfo(BaseModel):
    id: str
    name: str
    price: float
    image_url: Optional[str] = None
    description: Optional[str] = None

class CouponInfo(BaseModel):
    code: str
    discount: float
    description: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = True

class OrderInfo(BaseModel):
    order_id: str
    status: str
    status_description: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[str] = None

class BotMessageResponse(BaseModel):
    reply: str
    quick_actions: Optional[List[QuickAction]] = None
    products: Optional[List[ProductInfo]] = None
    order_info: Optional[OrderInfo] = None
    coupons: Optional[List[Dict[str, Any]]] = None
    coupon: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    source: Optional[str] = None
    thinking_process: Optional[List[Dict[str, Any]]] = None
