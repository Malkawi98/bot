from sqlalchemy.orm import Session
from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate, CouponUpdate
from typing import Optional, List, Dict, Any

def create_coupon(db: Session, coupon: CouponCreate) -> Coupon:
    # Create a new Coupon instance
    db_coupon = Coupon()
    
    # Set attributes manually
    db_coupon.code = coupon.code
    db_coupon.discount = coupon.discount
    db_coupon.description = coupon.description
    db_coupon.is_active = coupon.is_active
    db_coupon.expires_at = coupon.expires_at
    
    db.add(db_coupon)
    db.commit()
    db.refresh(db_coupon)
    return db_coupon

def get_coupon_by_code(db: Session, code: str) -> Optional[Coupon]:
    return db.query(Coupon).filter(Coupon.code == code).first()

def get_all_coupons(db: Session) -> List[Coupon]:
    return db.query(Coupon).all()

def get_coupon_by_id(db: Session, coupon_id: int) -> Optional[Coupon]:
    return db.query(Coupon).filter(Coupon.id == coupon_id).first()

def update_coupon(db: Session, coupon_id: int, coupon_data: Dict[str, Any]) -> Optional[Coupon]:
    db_coupon = get_coupon_by_id(db, coupon_id)
    if db_coupon:
        # Update attributes if they are provided in the coupon_data
        if 'code' in coupon_data and coupon_data['code'] is not None:
            db_coupon.code = coupon_data['code']
        if 'discount' in coupon_data and coupon_data['discount'] is not None:
            db_coupon.discount = coupon_data['discount']
        if 'description' in coupon_data and coupon_data['description'] is not None:
            db_coupon.description = coupon_data['description']
        if 'is_active' in coupon_data and coupon_data['is_active'] is not None:
            db_coupon.is_active = coupon_data['is_active']
        if 'expires_at' in coupon_data and coupon_data['expires_at'] is not None:
            db_coupon.expires_at = coupon_data['expires_at']
        
        db.commit()
        db.refresh(db_coupon)
    return db_coupon

def delete_coupon(db: Session, coupon_id: int) -> bool:
    db_coupon = get_coupon_by_id(db, coupon_id)
    if db_coupon:
        db.delete(db_coupon)
        db.commit()
        return True
    return False