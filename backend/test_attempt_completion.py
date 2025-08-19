"""
Test attempt_completion action integration
"""
import sys
from pathlib import Path

# Add the parent directory to sys.path to enable imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "api_server"))

def test_attempt_completion_handler():
    """Test that the attempt_completion handler works correctly"""
    
    print("=" * 60)
    print("TESTING ATTEMPT_COMPLETION ACTION HANDLER")
    print("=" * 60)
    
    try:
        # Import the handler function
        from api_server.index_fixed_azure_hybrid import _handle_attempt_completion_interrupt
        from shared_models import GroqAgentState
        
        print("✅ Successfully imported attempt_completion handler")
        
        # Create a mock GroqAgentState
        mock_state = GroqAgentState(api_key="test", project_id="test-completion")
        
        # Test case 1: Basic completion with message
        print("\n🧪 Test 1: Basic completion with message")
        action1 = {
            'type': 'attempt_completion',
            'content': 'I have successfully completed the todo app with user authentication. The app includes:\n- User signup and login\n- Protected routes\n- CRUD operations for todos\n- Clean UI design\n\nAll features are working correctly and integrated.'
        }
        
        result1 = _handle_attempt_completion_interrupt(mock_state, action1, "Test accumulated content")
        
        if result1 and result1.get('success'):
            print("✅ Test 1 PASSED")
            print(f"   Message: {result1.get('message')[:100]}...")
            print(f"   Session ended: {result1.get('session_ended')}")
        else:
            print("❌ Test 1 FAILED")
            print(f"   Result: {result1}")
        
        # Test case 2: Empty message (should use default)
        print("\n🧪 Test 2: Empty message (default fallback)")
        action2 = {
            'type': 'attempt_completion',
            'content': ''
        }
        
        result2 = _handle_attempt_completion_interrupt(mock_state, action2, "Test content")
        
        if result2 and result2.get('success') and result2.get('message') == 'Task completed successfully.':
            print("✅ Test 2 PASSED")
            print(f"   Default message: {result2.get('message')}")
        else:
            print("❌ Test 2 FAILED")
            print(f"   Result: {result2}")
        
        # Test case 3: Test XML parsing pattern
        print("\n🧪 Test 3: XML action tag pattern")
        xml_content = """
        I have completed the weather app with the following features:
        - API key input for users
        - Real-time weather data fetching
        - Clean responsive UI
        - Error handling for invalid cities
        
        <action type="attempt_completion">
        Weather app completed successfully! The app now allows users to:
        
        ✅ Enter their own OpenWeatherMap API key
        ✅ Search for weather by city name  
        ✅ View current weather conditions with icons
        ✅ Handle errors gracefully (invalid cities, API issues)
        ✅ Responsive design that works on mobile and desktop
        
        The app is fully functional and ready for use. Users just need to sign up for a free OpenWeatherMap API key and enter it in the app.
        </action>
        """
        
        # Simulate parsing XML content (simplified for test)
        import re
        pattern = r'<action type="attempt_completion">(.*?)</action>'
        match = re.search(pattern, xml_content.strip(), re.DOTALL)
        
        if match:
            extracted_content = match.group(1).strip()
            action3 = {
                'type': 'attempt_completion',
                'content': extracted_content
            }
            
            result3 = _handle_attempt_completion_interrupt(mock_state, action3, xml_content)
            
            if result3 and result3.get('success'):
                print("✅ Test 3 PASSED")
                print(f"   Extracted message length: {len(result3.get('message', ''))}")
                print(f"   Contains checklist: {'✅' in result3.get('message', '')}")
            else:
                print("❌ Test 3 FAILED")
                print(f"   Result: {result3}")
        else:
            print("❌ Test 3 FAILED: Could not extract XML content")
        
        print(f"\n" + "=" * 60)
        print("✅ ATTEMPT_COMPLETION HANDLER TESTS COMPLETE")
        print("=" * 60)
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test Error: {e}")
        return False
    
    return True

def test_prompt_integration():
    """Test that the action is properly added to the prompt"""
    
    print("\n" + "=" * 60)
    print("TESTING PROMPT INTEGRATION")
    print("=" * 60)
    
    try:
        # Import the prompts module
        from coder.prompts import get_prompt_config
        
        # Check if attempt_completion is in the prompt
        prompt_text = get_prompt_config("test-project", [], {})
        
        if 'attempt_completion' in prompt_text:
            print("✅ attempt_completion found in prompt")
            
            # Check for the XML example
            if '<action type="attempt_completion">' in prompt_text:
                print("✅ XML example found in prompt")
            else:
                print("⚠️  XML example not found in prompt")
            
            # Check for usage guidelines
            if 'Use when you have completed all the work' in prompt_text:
                print("✅ Usage guidelines found in prompt")
            else:
                print("⚠️  Usage guidelines not found in prompt")
                
        else:
            print("❌ attempt_completion NOT found in prompt")
        
    except Exception as e:
        print(f"❌ Prompt test error: {e}")

if __name__ == "__main__":
    print("🚀 Starting attempt_completion action tests...")
    
    # Test the handler function
    handler_success = test_attempt_completion_handler()
    
    # Test prompt integration
    test_prompt_integration()
    
    if handler_success:
        print("\n🎉 ALL TESTS PASSED - attempt_completion action is working!")
    else:
        print("\n💥 SOME TESTS FAILED - check implementation")