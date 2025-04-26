from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.coupon import Coupon
from app.crud.crud_coupon import get_all_coupons, get_coupon_by_code

# In-memory store of assigned coupons (session_id -> coupon_code)
# In a production environment, this would be stored in a database
user_coupon_assignments: Dict[str, str] = {}

class CouponService:
    def __init__(self, db: Session):
        self.db = db
        
    @staticmethod
    def has_received_coupon(session_id: str) -> bool:
        """Check if a user has already received a coupon in this session"""
        return session_id in user_coupon_assignments
    
    @staticmethod
    def get_assigned_coupon(session_id: str) -> Optional[str]:
        """Get the coupon code assigned to this user"""
        return user_coupon_assignments.get(session_id)
    
    @staticmethod
    def assign_coupon_to_user(session_id: str, coupon_code: str) -> None:
        """Assign a coupon to a user"""
        user_coupon_assignments[session_id] = coupon_code
    
    def get_active_coupons(self) -> List[Coupon]:
        """
        Get all active coupons that haven't expired
        """
        all_coupons = get_all_coupons(self.db)
        now = datetime.utcnow()
        
        # Filter for active coupons that haven't expired
        active_coupons = [
            coupon for coupon in all_coupons 
            if coupon.is_active and (coupon.expires_at is None or coupon.expires_at > now)
        ]
        
        return active_coupons
    
    def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        """
        Get a coupon by its code if it's active and hasn't expired
        """
        coupon = get_coupon_by_code(self.db, code)
        now = datetime.utcnow()
        
        if coupon and coupon.is_active and (coupon.expires_at is None or coupon.expires_at > now):
            return coupon
        
        return None
        
    def request_coupon(self, session_id: str, requested_code: str) -> dict:
        """
        Request a specific coupon for a user
        
        Returns a dict with:
        - success: Whether the request was successful
        - coupon: The coupon object if successful
        - message: A message explaining the result
        - already_assigned: Whether the user already had a coupon assigned
        - assigned_code: The code of the previously assigned coupon (if any)
        """
        # Check if user already has a coupon
        if self.has_received_coupon(session_id):
            assigned_code = self.get_assigned_coupon(session_id)
            assigned_coupon = self.get_coupon_by_code(assigned_code)
            
            if assigned_coupon:
                return {
                    "success": False,
                    "coupon": self.format_coupon_for_display(assigned_coupon),
                    "message": "already_assigned",
                    "already_assigned": True,
                    "assigned_code": assigned_code
                }
            else:
                # The previously assigned coupon is no longer valid
                # We'll allow them to get a new one by continuing
                pass
        
        # Check if the requested coupon exists and is valid
        coupon = self.get_coupon_by_code(requested_code)
        if not coupon:
            return {
                "success": False,
                "coupon": None,
                "message": "invalid_coupon",
                "already_assigned": False,
                "assigned_code": None
            }
        
        # Assign the coupon to the user
        self.assign_coupon_to_user(session_id, coupon.code)
        
        return {
            "success": True,
            "coupon": self.format_coupon_for_display(coupon),
            "message": "success",
            "already_assigned": False,
            "assigned_code": coupon.code
        }
    
    def format_coupon_for_display(self, coupon: Coupon) -> dict:
        """
        Format a coupon as structured data for the AI to generate a response
        """
        return {
            "code": coupon.code,
            "discount": coupon.discount,
            "description": coupon.description or "",
            "expires_at": coupon.expires_at.strftime("%Y-%m-%d") if coupon.expires_at else None,
            "is_active": coupon.is_active
        }
    
    def format_coupons_list(self, coupons: List[Coupon]) -> dict:
        """
        Format a list of coupons as structured data for the AI to generate a response
        """
        formatted_coupons = [self.format_coupon_for_display(coupon) for coupon in coupons]
        
        return {
            "coupons": formatted_coupons,
            "count": len(formatted_coupons),
            "has_coupons": len(formatted_coupons) > 0
        }
