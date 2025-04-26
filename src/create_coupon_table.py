#!/usr/bin/env python
"""
Script to directly create the coupons table in the database.
This bypasses Alembic migrations and creates the table directly using SQLAlchemy.
"""
from app.core.db.database import Base, get_db
from app.models.coupon import Coupon
from datetime import datetime, timedelta

def create_coupon_table():
    """Create the coupons table and insert sample data."""
    # Get a database session
    db = next(get_db())
    
    try:
        # Create all tables (including coupons)
        Base.metadata.create_all(bind=db.get_bind())
        print("Tables created successfully.")
        
        # Check if coupons table has any data
        result = db.query(Coupon).first()
        
        if result:
            print("Coupons already exist in the database.")
            return
            
        # Insert sample coupons
        sample_coupons = [
            {
                "code": "WELCOME10",
                "discount": 10.0,
                "description": "Welcome discount for new customers",
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=30)
            },
            {
                "code": "SUMMER25",
                "discount": 25.0,
                "description": "Summer sale discount",
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=60)
            },
            {
                "code": "FREESHIP",
                "discount": 5.0,
                "description": "Free shipping coupon",
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=15)
            }
        ]
        
        for coupon_data in sample_coupons:
            # Create a new Coupon instance
            coupon = Coupon()
            
            # Set attributes manually
            coupon.code = coupon_data["code"]
            coupon.discount = coupon_data["discount"]
            coupon.description = coupon_data["description"]
            coupon.is_active = coupon_data["is_active"]
            coupon.expires_at = coupon_data["expires_at"]
            
            db.add(coupon)
        
        db.commit()
        
        print("Sample coupons added successfully.")
        
        # Verify the data was inserted
        coupons = db.query(Coupon).all()
        print(f"Added {len(coupons)} coupons:")
        for coupon in coupons:
            print(f"Code: {coupon.code}, Discount: {coupon.discount}%, Description: {coupon.description}")
        
    except Exception as e:
        print(f"Error creating coupons table: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    create_coupon_table()
