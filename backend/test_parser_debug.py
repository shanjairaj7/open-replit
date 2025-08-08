#!/usr/bin/env python3
"""Test the exact model response to find the parser error"""

from shared_models import StreamingXMLParser
from pathlib import Path
import os
import sys
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

# EXACT model response from Message 18
test_content = """<action type="file" filePath="backend/services/auth_routes.py">
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models.user_models import UserCreate, UserResponse
from models.token_models import Token, TokenData
from services.auth_service import auth_service
from services.user_service import user_service
from utils.security import decode_access_token
import uuid

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token/")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user_data = user_service.get_user_by_id(uuid.UUID(user_id))
    if user_data is None:
        raise credentials_exception
    
    # Filter out 'hashed_password' before returning UserResponse
    response_data = {k: v for k, v in user_data.items() if k != "hashed_password"}
    return UserResponse.model_validate(response_data)

@router.post("/auth/signup/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    return auth_service.register_user(user_data)

@router.post("/auth/token/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token_for_user(user)
    return access_token

@router.get("/auth/me/", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@router.post("/auth/forgot-password/", status_code=status.HTTP_200_OK)
async def forgot_password():
    # Placeholder for forgot password logic
    return {"message": "Password reset link sent to your email (not implemented yet)."}

@router.post("/auth/reset-password/", status_code=status.HTTP_200_OK)
async def reset_password():
    # Placeholder for reset password logic
    return {"message": "Password has been reset (not implemented yet)."}
</action>

<action type="update_file" path="backend/app.py">
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services."""

def test_parser():
    """Test parsing this exact content"""
    print("Testing StreamingXMLParser with exact model response...")
    print("="*80)
    
    parser = StreamingXMLParser()
    actions = list(parser.process_chunk(test_content))
    
    print(f"Found {len(actions)} actions:")
    for i, action in enumerate(actions):
        print(f"\nAction {i+1}:")
        print(f"  Type: {action['type']}")
        print(f"  Path: {action.get('path', 'N/A')}")
        print(f"  Content length: {len(action.get('content', ''))}")
        print(f"  Content preview: {action.get('content', '')[:100]}...")

def test_file_creation_handler():
    """Test the _handle_create_file_realtime function"""
    print("\n" + "="*80)
    print("Testing _handle_create_file_realtime function...")
    
    # Create a mock GroqAgentState
    class MockState:
        def __init__(self):
            self.api_base_url = "http://localhost:8000/api" 
            self.project_id = "want-crm-web-application-0808-070236"  # Use real existing project
            
        def _remove_backticks_from_content(self, content):
            return content.strip()
            
        def _write_file_via_api(self, file_path, content):
            print(f"MOCK API CALL: PUT {self.api_base_url}/projects/{self.project_id}/files/{file_path}")
            print(f"Content length: {len(content)} chars")
            print(f"Content preview: {content[:100]}...")
            return {"success": True, "python_errors": "", "typescript_errors": ""}
    
    state = MockState()
    
    # Import the function
    from test_groq_local import BoilerplatePersistentGroq
    mock_instance = BoilerplatePersistentGroq("fake-key", project_id="want-crm-web-application-0808-070236")
    
    # Test the action
    action = {
        'type': 'create_file_realtime',
        'content': test_content
    }
    
    result = mock_instance._handle_create_file_realtime(action)
    print(f"Result: {result}")

if __name__ == "__main__":
    test_parser()
    test_file_creation_handler()