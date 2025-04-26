from pydantic import BaseModel
from typing import Optional

class CouponRequestModel(BaseModel):
    coupon_code: str
    language: Optional[str] = "en"
    
class CouponResponseModel(BaseModel):
    success: bool
    message: str
    coupon_code: Optional[str] = None
    discount: Optional[float] = None
    description: Optional[str] = None
    expires_at: Optional[str] = None
    already_assigned: bool = False
    assigned_code: Optional[str] = None
