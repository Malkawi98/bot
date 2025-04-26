from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CouponBase(BaseModel):
    code: str
    discount: float
    description: Optional[str] = None
    is_active: Optional[bool] = True
    expires_at: Optional[datetime] = None

class CouponCreate(CouponBase):
    pass

class CouponUpdate(BaseModel):
    code: Optional[str] = None
    discount: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class CouponRead(CouponBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True