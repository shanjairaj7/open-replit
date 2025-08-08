#!/usr/bin/env python3
"""Debug the exact parsing issue with the model's response"""

import sys
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from shared_models import StreamingXMLParser

# EXACT content from the JSON coder call log
test_content = 'I apologize again. I seem to be stuck in a loop. I *did* use `action type="file"` in my previous response, but the system is still reporting that the file doesn\'t exist. This is unexpected behavior.\n\nI will try again to create the file `backend/services/auth_routes.py` using `action type="file"`. If this fails again, I will need to investigate why the file creation is not being registered.\n\n<action type="file" filePath="backend/services/auth_routes.py">\nfrom fastapi import APIRouter, Depends, HTTPException, status\nfrom fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm\nfrom models.user_models import UserCreate, UserResponse\nfrom models.token_models import Token, TokenData\nfrom services.auth_service import auth_service\nfrom services.user_service import user_service\nfrom utils.security import decode_access_token\nimport uuid\n\nrouter = APIRouter()\n\noauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token/")\n\nasync def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:\n    credentials_exception = HTTPException(\n        status_code=status.HTTP_401_UNAUTHORIZED,\n        detail="Could not validate credentials",\n        headers={"WWW-Authenticate": "Bearer"},\n    )\n    payload = decode_access_token(token)\n    if payload is None:\n        raise credentials_exception\n    user_id: str = payload.get("sub")\n    if user_id is None:\n        raise credentials_exception\n    \n    user_data = user_service.get_user_by_id(uuid.UUID(user_id))\n    if user_data is None:\n        raise credentials_exception\n    \n    # Filter out \'hashed_password\' before returning UserResponse\n    response_data = {k: v for k, v in user_data.items() if k != "hashed_password"}\n    return UserResponse.model_validate(response_data)\n\n@router.post("/auth/signup/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)\nasync def signup(user_data: UserCreate):\n    return auth_service.register_user(user_data)\n\n@router.post("/auth/token/", response_model=Token)\nasync def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):\n    user = auth_service.authenticate_user(form_data.username, form_data.password)\n    if not user:\n        raise HTTPException(\n            status_code=status.HTTP_401_UNAUTHORIZED,\n            detail="Incorrect email or password",\n            headers={"WWW-Authenticate": "Bearer"},\n        )\n    access_token = auth_service.create_access_token_for_user(user)\n    return access_token\n\n@router.get("/auth/me/", response_model=UserResponse)\nasync def read_users_me(current_user: UserResponse = Depends(get_current_user)):\n    return current_user\n\n@router.post("/auth/forgot-password/", status_code=status.HTTP_200_OK)\nasync def forgot_password():\n    # Placeholder for forgot password logic\n    return {"message": "Password reset link sent to your email (not implemented yet)."}\n\n@router.post("/auth/reset-password/", status_code=status.HTTP_200_OK)\nasync def reset_password():\n    # Placeholder for reset password logic\n    return {"message": "Password has been reset (not implemented yet)."}\n</action>\n\n<action type="update_file" path="backend/app.py">\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\n'

def debug_exact_issue():
    """Test the exact content to see what actions are detected and how coder processes them"""
    print("🔍 DEBUGGING: Analyzing exact model response that caused the issue...")
    print("="*80)
    
    print("\n📝 STEP 1: Parse complete content")
    parser = StreamingXMLParser()
    actions = list(parser.process_chunk(test_content))
    
    print(f"\n🎯 FOUND {len(actions)} ACTIONS:")
    for i, action in enumerate(actions, 1):
        print(f"\nAction {i}:")
        print(f"  Type: {action['type']}")
        path = action.get('path') or action.get('filePath')
        print(f"  Path: {path}")
        print(f"  Content length: {len(action.get('content', ''))}")
        if 'auth_routes.py' in str(path):
            print(f"  ⭐ This is the auth_routes.py action!")
        
    print("\n" + "="*80)
    print("📝 STEP 2: Simulate coder early detection logic")
    
    # Check what the early detection would find
    update_file_pos = test_content.find('<action type="update_file"')
    file_pos = test_content.find('<action type="file"')
    
    print(f"🔍 'file' action position: {file_pos}")
    print(f"🔍 'update_file' action position: {update_file_pos}")
    
    if update_file_pos >= 0:
        print(f"\n⚠️  Early detection would trigger at position {update_file_pos}")
        
        # Extract the path from update_file 
        import re
        update_content = test_content[update_file_pos:update_file_pos+100]
        print(f"🔍 Update content snippet: {repr(update_content)}")
        path_match = re.search(r'(?:path|filePath)="([^"]*)"', update_content)
        if path_match:
            detected_path = path_match.group(1)
            print(f"🎯 Early detection would see path: {detected_path}")
            
            if detected_path == "backend/app.py":
                print("✅ Correctly detected backend/app.py for update_file")
            else:
                print(f"❌ Wrong path detected: {detected_path}")
        else:
            print("❌ No path found in update_file action")
                
    print("\n" + "="*80) 
    print("📝 STEP 3: Check if coder would create read_file interrupt")
    
    # Simulate the coder logic from lines 100-157 in coder/index.py
    accumulated_content = test_content
    update_file_detected = False
    
    # Early detection: Check for update_file action start
    if not update_file_detected and '<action type="update_file"' in accumulated_content:
        update_file_detected = True
        print(f"🚨 EARLY DETECTION - Found update_file action, checking for path...")
        
        # Look for path attribute - this mimics the exact coder logic from line 130
        path_match = re.search(r'(?:path|filePath)="([^"]*)"', accumulated_content)
        if path_match:
            file_path = path_match.group(1)
            print(f"🎯 Found file path in update_file: {file_path}")
            
            # This would check if file was previously read
            # For this test, assume it wasn't read
            print(f"🚨 INTERRUPT REQUIRED - File '{file_path}' needs to be read first!")
            print("⚡ This would create read_file interrupt action")
            print(f"🔍 ERROR SOURCE: When read_file fails, coder/index.py:263 sends error for '{file_path}'")
        else:
            print("⏳ File path not yet available in update_file action")
            
    print("\n" + "="*80)
    print("📝 STEP 4: The REAL issue analysis")
    
    file_actions = [a for a in actions if a['type'] == 'file']
    update_actions = [a for a in actions if a['type'] == 'update_file']
    
    print(f"🎯 File creation actions: {len(file_actions)}")
    for action in file_actions:
        path = action.get('path') or action.get('filePath')
        print(f"   → Create: {path}")
        
    print(f"🎯 Update file actions: {len(update_actions)}")
    for action in update_actions:
        path = action.get('path') or action.get('filePath')
        print(f"   → Update: {path}")
        
    print("\n🔍 ROOT CAUSE HYPOTHESIS:")
    print("1. Model generates TWO actions: 'file' (auth_routes.py) + 'update_file' (app.py)")
    print("2. Coder's early detection sees 'update_file' for app.py") 
    print("3. Coder creates read_file interrupt for app.py (not auth_routes.py!)")
    print("4. But the error message says 'Cannot update auth_routes.py' - WRONG FILE!")
    print("5. This suggests the error message is coming from the wrong place")

if __name__ == "__main__":
    debug_exact_issue()