"""Authentication utilities for the application."""

from fastapi import Request, HTTPException, status
from typing import Dict, Any, Optional

def get_authenticated_user(request: Request, test_session: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get the authenticated user from the session.
    
    Args:
        request: FastAPI request object
        test_session: Optional test session for testing
        
    Returns:
        Dict[str, Any]: User information including id, email, name, and profile_picture
        
    Raises:
        HTTPException: If user is not authenticated
    """
    # For test mode
    if test_session and test_session.get("user"):
        return test_session["user"]
    
    # Check both user object and user_id
    user = request.session.get("user")
    user_id = request.session.get("user_id")
    
    # If neither exists, user is not authenticated
    if not user and not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # If we have user_id but no user object, create minimal user object
    if not user and user_id:
        user = {"id": user_id}
    
    # If we have user object but no id, or id is empty
    if not user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in session"
        )
    
    return user 