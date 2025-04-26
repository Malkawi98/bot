from sqlalchemy.orm import Session
from app.core.db.database import sync_session
from app.models.coupon import Coupon
from app.services.graph_service.nodes import action_node
from datetime import datetime, timedelta
import sqlalchemy as sa

def setup_test_coupon(db: Session, code: str = "TESTCOUPON"):
    # Remove if exists
    db.execute(sa.text(f"DELETE FROM coupons WHERE code = '{code}'"))
    db.commit()
    
    # Add test coupon - Method 1: Using SQL directly
    db.execute(
        sa.text("""
        INSERT INTO coupons (code, discount, description, is_active, created_at, expires_at)
        VALUES (:code, :discount, :description, :is_active, :created_at, :expires_at)
        """),
        {
            "code": code,
            "discount": 15.0,
            "description": "Test 15% off coupon",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }
    )
    db.commit()
    
    # Verify the coupon was created
    result = db.execute(sa.text(f"SELECT * FROM coupons WHERE code = '{code}'")).first()
    if result:
        print(f"Created test coupon with code '{code}'")
    else:
        print(f"Failed to create test coupon with code '{code}'")
    return result

def test_coupon_lookup():
    with sync_session() as db:
        # Setup
        print("Setting up test coupon...")
        setup_test_coupon(db, "TESTCOUPON")
        
        # Test found - prepare a state with coupon_query intent
        print("Testing coupon lookup for existing coupon...")
        state = {
            "user_message": "Do you have a coupon code TESTCOUPON?",
            "intent": "coupon_query", 
            "db": db,
            "messages": []
        }
        result = action_node(state)
        print("Test found:", result)
        
        # Test not found
        print("Testing coupon lookup for non-existing coupon...")
        state = {
            "user_message": "Do you have a coupon code NOCODE?",
            "intent": "coupon_query", 
            "db": db,
            "messages": []
        }
        result = action_node(state)
        print("Test not found:", result)

if __name__ == "__main__":
    test_coupon_lookup() 