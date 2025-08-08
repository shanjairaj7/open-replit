#!/usr/bin/env python3
"""Test live streaming with actual model to see the exact bug"""

import sys
sys.path.append('/Users/shanjairaj/Documents/forks/bolt.diy/backend')

from test_groq_local import BoilerplatePersistentGroq
from shared_models import StreamingXMLParser
import os

def test_live_streaming_bug():
    """Test with real model streaming to see exact interrupt behavior"""
    print("🔍 TESTING: Live streaming with model to debug interrupt bug")
    print("="*80)
    
    # Use existing project
    project_id = "want-crm-web-application-0808-070236"
    # groq_key = os.getenv('GROQ_API_KEY')
    
    # if not groq_key:
    #     print("❌ GROQ_API_KEY not found in environment")
    #     return
        
    print(f"🎯 Using project: {project_id}")
    # print(f"🔑 API key: {groq_key[:10]}...")
    
    # Create instance
    agent = BoilerplatePersistentGroq(project_id=project_id)
    
    # Create a simple test prompt that should trigger file creation + update
    test_prompt = """
    Please do the following in sequence:
    1. Create a new file called `backend/services/test_routes.py` with a simple FastAPI router
    2. Update the `backend/app.py` file to import this new router
    
    Use the appropriate action tags and make sure both actions are in the same response.
    """
    
    print(f"\n📤 Sending test prompt...")
    print(f"Prompt: {test_prompt}")
    
    # Prepare messages
    messages = [
        {"role": "system", "content": agent._get_system_prompt()},
        {"role": "user", "content": test_prompt}
    ]
    
    print(f"\n🌊 Starting streaming completion...")
    
    try:
        # Create streaming response
        completion = agent.client.chat.completions.create(
            model=agent.model,
            messages=messages,
            temperature=0.1,
            max_tokens=4000,
            stream=True,
            stream_options={"include_usage": "true"}
        )
        
        # Simulate exact coder logic
        parser = StreamingXMLParser()
        accumulated_content = ""
        should_interrupt = False
        interrupt_action = None
        
        # Early detection state
        update_file_detected = False
        update_file_buffer = ""
        update_file_validated = False
        
        chunk_count = 0
        
        print(f"🔍 Processing streaming chunks with exact coder logic...")
        
        for chunk in completion:
            chunk_count += 1
            
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                accumulated_content += content
                
                # EXACT coder logic from lines 100-120
                print(f"\n[CHUNK {chunk_count}] Testing coder detection logic...")
                
                # Early detection: Check for update_file action start (line 100)
                if not update_file_detected and '<action type="update_file"' in accumulated_content:
                    update_file_detected = True
                    update_file_buffer = accumulated_content
                    print(f"🚨 EARLY DETECTION - Found update_file action! update_file_detected=True")
                
                # Early detection: Check for complete file creation action (line 107) 
                print(f"🔍 File action check: not update_file_detected = {not update_file_detected}")
                if not update_file_detected and '<action type="file"' in accumulated_content:
                    print(f"🔍 File action found, checking completion...")
                    if '</action>' in accumulated_content:
                        print(f"🚨 COMPLETE FILE ACTION DETECTED - Should interrupt!")
                        should_interrupt = True
                        interrupt_action = {
                            'type': 'create_file_realtime', 
                            'content': accumulated_content
                        }
                        print(f"⚡ BREAKING from streaming...")
                        break
                    else:
                        print(f"⏳ File action incomplete, continuing...")
                else:
                    if update_file_detected:
                        print(f"❌ File action detection SKIPPED - update_file_detected=True")
                    if '<action type="file"' not in accumulated_content:
                        print(f"ℹ️ No file action found yet")
                        
        print(f"\n\n🎯 STREAMING COMPLETE")
        print(f"📊 Total chunks: {chunk_count}")
        print(f"📏 Final content length: {len(accumulated_content)} chars")
        print(f"🚨 Interrupt triggered: {should_interrupt}")
        print(f"🔍 update_file_detected: {update_file_detected}")
        
        if not should_interrupt and '<action type="file"' in accumulated_content and '</action>' in accumulated_content:
            print(f"\n❌ BUG CONFIRMED!")
            print(f"   File action was complete but interrupt failed")
            print(f"   Reason: update_file_detected prevented file action processing")
            
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live_streaming_bug()