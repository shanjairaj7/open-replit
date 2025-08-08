#!/usr/bin/env python3
"""Test why the interrupt mechanism failed for file creation"""

import sys
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from shared_models import StreamingXMLParser

# The EXACT content that should have triggered interrupt
test_content = 'I apologize again. I seem to be stuck in a loop. I *did* use `action type="file"` in my previous response, but the system is still reporting that the file doesn\'t exist. This is unexpected behavior.\n\nI will try again to create the file `backend/services/auth_routes.py` using `action type="file"`. If this fails again, I will need to investigate why the file creation is not being registered.\n\n<action type="file" filePath="backend/services/auth_routes.py">\nfrom fastapi import APIRouter, Depends, HTTPException, status\nfrom fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm\nfrom models.user_models import UserCreate, UserResponse\nfrom models.token_models import Token, TokenData\nfrom services.auth_service import auth_service\nfrom services.user_service import user_service\nfrom utils.security import decode_access_token\nimport uuid\n\nrouter = APIRouter()\n\noauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token/")\n\nasync def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:\n    credentials_exception = HTTPException(\n        status_code=status.HTTP_401_UNAUTHORIZED,\n        detail="Could not validate credentials",\n        headers={"WWW-Authenticate": "Bearer"},\n    )\n    payload = decode_access_token(token)\n    if payload is None:\n        raise credentials_exception\n    user_id: str = payload.get("sub")\n    if user_id is None:\n        raise credentials_exception\n    \n    user_data = user_service.get_user_by_id(uuid.UUID(user_id))\n    if user_data is None:\n        raise credentials_exception\n    \n    # Filter out \'hashed_password\' before returning UserResponse\n    response_data = {k: v for k, v in user_data.items() if k != "hashed_password"}\n    return UserResponse.model_validate(response_data)\n\n@router.post("/auth/signup/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)\nasync def signup(user_data: UserCreate):\n    return auth_service.register_user(user_data)\n\n@router.post("/auth/token/", response_model=Token)\nasync def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):\n    user = auth_service.authenticate_user(form_data.username, form_data.password)\n    if not user:\n        raise HTTPException(\n            status_code=status.HTTP_401_UNAUTHORIZED,\n            detail="Incorrect email or password",\n            headers={"WWW-Authenticate": "Bearer"},\n        )\n    access_token = auth_service.create_access_token_for_user(user)\n    return access_token\n\n@router.get("/auth/me/", response_model=UserResponse)\nasync def read_users_me(current_user: UserResponse = Depends(get_current_user)):\n    return current_user\n\n@router.post("/auth/forgot-password/", status_code=status.HTTP_200_OK)\nasync def forgot_password():\n    # Placeholder for forgot password logic\n    return {"message": "Password reset link sent to your email (not implemented yet)."}\n\n@router.post("/auth/reset-password/", status_code=status.HTTP_200_OK)\nasync def reset_password():\n    # Placeholder for reset password logic\n    return {"message": "Password has been reset (not implemented yet)."}\n</action>\n\n<action type="update_file" path="backend/app.py">\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\n'

def test_interrupt_mechanism():
    """Test the exact streaming scenario to see why interrupt failed"""
    print("🔍 TESTING: Why interrupt mechanism failed for file creation")
    print("="*80)
    
    # Simulate the exact coder streaming logic
    parser = StreamingXMLParser()
    accumulated_content = ""
    should_interrupt = False
    interrupt_action = None
    
    print("\n📝 STEP 1: Test complete file action detection")
    
    # Check if we can detect the complete file action
    file_start = test_content.find('<action type="file"')
    file_end = test_content.find('</action>', file_start)
    
    if file_start >= 0 and file_end >= 0:
        print(f"🎯 File action found: start={file_start}, end={file_end}")
        complete_file_action = test_content[file_start:file_end + 9]  # +9 for '</action>'
        print(f"📏 Complete file action length: {len(complete_file_action)} chars")
        
        # Test if parser can detect this complete action
        actions = list(parser.process_chunk(complete_file_action))
        print(f"✅ Parser detected {len(actions)} actions in complete file action")
        
        if actions:
            action = actions[0]
            print(f"   Type: {action['type']}")
            print(f"   Path: {action.get('path', action.get('filePath'))}")
            print(f"   Content length: {len(action.get('content', ''))}")
    else:
        print("❌ Could not find complete file action boundaries")
        
    print("\n" + "="*40)
    print("📝 STEP 2: Test chunk-by-chunk streaming (simulating real flow)")
    
    # Simulate streaming with chunk processing like the coder does
    chunk_size = 100  # Small chunks to simulate streaming
    parser2 = StreamingXMLParser()
    
    for i in range(0, len(test_content), chunk_size):
        chunk = test_content[i:i + chunk_size]
        accumulated_content += chunk
        
        print(f"\n🌊 Chunk {i//chunk_size + 1}: {len(chunk)} chars")
        print(f"📊 Accumulated: {len(accumulated_content)} chars")
        
        # Check for complete file action in streaming (like coder logic at line 107-120)
        if not should_interrupt and '<action type="file"' in accumulated_content:
            if '</action>' in accumulated_content:
                print(f"🚨 COMPLETE FILE ACTION DETECTED - Should interrupt here!")
                print(f"📊 File action content length: {len(accumulated_content)} chars")
                
                should_interrupt = True
                interrupt_action = {
                    'type': 'create_file_realtime',
                    'content': accumulated_content
                }
                print("⚡ BREAKING: This should have stopped the streaming")
                break
            else:
                print("⏳ File action incomplete, continuing...")
        
        # Also check what parser detects in this chunk
        chunk_actions = list(parser2.process_chunk(chunk))
        if chunk_actions:
            print(f"🎬 Parser found {len(chunk_actions)} actions in this chunk:")
            for action in chunk_actions:
                print(f"   → {action['type']}: {action.get('path', action.get('filePath'))}")
                
    print(f"\n🎯 INTERRUPT STATUS:")
    print(f"   should_interrupt: {should_interrupt}")
    print(f"   interrupt_action: {interrupt_action is not None}")
    
    if should_interrupt:
        print("✅ Interrupt mechanism worked correctly")
        print("🤔 But if this worked, why did the model continue streaming?")
        print("💡 The issue might be in the actual coder implementation or API call")
    else:
        print("❌ Interrupt mechanism failed - this explains the bug!")
        print("🔍 The complete file action was not detected during streaming")
        
    print("\n" + "="*40)
    print("📝 STEP 3: Check if the issue is incomplete closing tag")
    
    # Look for unclosed actions
    file_opens = test_content.count('<action type="file"')
    action_closes = test_content.count('</action>')
    
    print(f"🔍 File action opens: {file_opens}")
    print(f"🔍 Action closes: {action_closes}")
    
    if file_opens > action_closes:
        print("❌ FOUND ISSUE: More opening tags than closing tags!")
        print("💡 The file action might not be properly closed")
        
    print("\n🎯 ROOT CAUSE ANALYSIS:")
    if should_interrupt:
        print("1. ✅ Interrupt detection logic works")
        print("2. ❌ But streaming continued anyway")  
        print("3. 🔍 Issue might be in coder implementation or chunk processing")
    else:
        print("1. ❌ Interrupt detection failed")
        print("2. 🔍 File action detection logic has a bug")
        print("3. 💡 Need to fix the streaming interrupt mechanism")

if __name__ == "__main__":
    test_interrupt_mechanism()