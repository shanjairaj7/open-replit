from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from json_db import JsonDBSession, get_db
from routes.auth import get_current_active_user, AuthUserResponse # Import AuthUserResponse and get_current_active_user
import os # Import os module

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/{user_id}", response_model=AuthUserResponse)
def get_user_by_id(
    user_id: int,
    db_session: JsonDBSession = Depends(get_db),
    current_user: AuthUserResponse = Depends(get_current_active_user) # Ensure user is authenticated
):
    """Get user details by ID."""
    user = db_session.db.find_one("users", id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return AuthUserResponse(**user)

@router.get("/", response_model=List[AuthUserResponse])
def get_all_users(
    db_session: JsonDBSession = Depends(get_db),
    current_user: AuthUserResponse = Depends(get_current_active_user) # Ensure user is authenticated
):
    """Get all users (for admin purposes or for assigning tasks)."""
    users = db_session.db.find_all("users")
    return [AuthUserResponse(**user) for user in users]