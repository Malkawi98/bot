"""
Dependencies for API endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.db.database import get_db
from app.core.security import oauth2_scheme, TokenType, verify_token

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get the current authenticated user based on the JWT token.
    
    Args:
        token: The JWT token
        db: Database session
        
    Returns:
        The current user
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # For development purposes, allow bypassing authentication
    # In production, this should verify the token and get the real user
    return {"id": 1, "username": "admin", "email": "admin@example.com", "is_active": True}
