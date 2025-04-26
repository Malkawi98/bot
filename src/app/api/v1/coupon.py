from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.db.database import get_db
from app.schemas.coupon import CouponCreate, CouponRead, CouponUpdate
from app.crud.crud_coupon import (
    create_coupon, 
    get_coupon_by_code, 
    get_all_coupons, 
    get_coupon_by_id,
    update_coupon,
    delete_coupon
)

router = APIRouter(prefix="/coupon", tags=["coupon"])

@router.post("/", response_model=CouponRead)
def create_coupon_api(coupon: CouponCreate, db: Session = Depends(get_db)):
    db_coupon = get_coupon_by_code(db, coupon.code)
    if db_coupon:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    return create_coupon(db, coupon)

@router.get("/", response_model=List[CouponRead])
def list_coupons_api(db: Session = Depends(get_db)):
    return get_all_coupons(db)

@router.get("/{code}", response_model=CouponRead)
def get_coupon_api(code: str, db: Session = Depends(get_db)):
    coupon = get_coupon_by_code(db, code)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return coupon

@router.get("/id/{coupon_id}", response_model=CouponRead)
def get_coupon_by_id_api(coupon_id: int, db: Session = Depends(get_db)):
    coupon = get_coupon_by_id(db, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return coupon

@router.put("/{coupon_id}", response_model=CouponRead)
def update_coupon_api(coupon_id: int, coupon_data: CouponUpdate, db: Session = Depends(get_db)):
    # Check if coupon exists
    existing_coupon = get_coupon_by_id(db, coupon_id)
    if not existing_coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    # If code is being updated, check if it already exists
    if coupon_data.code and coupon_data.code != existing_coupon.code:
        code_exists = get_coupon_by_code(db, coupon_data.code)
        if code_exists:
            raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    updated_coupon = update_coupon(db, coupon_id, coupon_data.model_dump(exclude_unset=True))
    return updated_coupon

@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon_api(coupon_id: int, db: Session = Depends(get_db)):
    coupon_exists = get_coupon_by_id(db, coupon_id)
    if not coupon_exists:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    delete_success = delete_coupon(db, coupon_id)
    if not delete_success:
        raise HTTPException(status_code=500, detail="Failed to delete coupon")
    return None