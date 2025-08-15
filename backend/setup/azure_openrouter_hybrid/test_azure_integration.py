#!/usr/local/bin/python3.13
"""
Test script for Azure OpenAI hybrid integration with gpt-4o-mini
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Set Azure mode
os.environ["USE_AZURE_MODE"] = "true"

def test_azure_gpt4o_mini():
    """Test Azure integration with gpt-4o-mini"""
    try:
        from setup.azure_openrouter_hybrid.base_test_azure_hybrid import BoilerplatePersistentGroq
        
        print("🧪 Testing Azure OpenAI with gpt-4o-mini...")
        
        # Create test project
        test_project_id = "test-azure-gpt4o-mini"
        groq = BoilerplatePersistentGroq(project_id=test_project_id)
        
        print(f"✅ Client initialized successfully!")
        print(f"   - Client type: {type(groq.client).__name__}")
        print(f"   - Model: {groq.model}")
        print(f"   - Azure mode: {groq.is_azure_mode}")
        
        # Test basic message
        test_message = [
            {"role": "user", "content": "Hello! Please respond with a simple greeting and confirm you're working."}
        ]
        
        print("\n🚀 Testing message generation...")
        response = groq._process_update_request_with_interrupts(test_message[0]["content"])
        
        print("✅ Response generated successfully!")
        if response:
            print(f"Response length: {len(str(response))} characters")
            print("Response preview:")
            print("-" * 50)
            print(str(response)[:300] + "..." if len(str(response)) > 300 else str(response))
            print("-" * 50)
        else:
            print("Response completed (no return value expected)")
        
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openrouter_fallback():
    """Test OpenRouter fallback when Azure mode is disabled"""
    try:
        # Disable Azure mode
        os.environ["USE_AZURE_MODE"] = "false"
        
        # Reload module to pick up new environment variable
        if 'setup.azure_openrouter_hybrid.base_test_azure_hybrid' in sys.modules:
            del sys.modules['setup.azure_openrouter_hybrid.base_test_azure_hybrid']
        
        from setup.azure_openrouter_hybrid.base_test_azure_hybrid import BoilerplatePersistentGroq
        
        print("\n🧪 Testing OpenRouter fallback...")
        
        # Create test project
        test_project_id = "test-openrouter-fallback"
        groq = BoilerplatePersistentGroq(project_id=test_project_id)
        
        print(f"✅ OpenRouter fallback initialized!")
        print(f"   - Client type: {type(groq.client).__name__}")
        print(f"   - Model: {groq.model}")
        print(f"   - Azure mode: {groq.is_azure_mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter fallback test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Azure-OpenRouter Hybrid Integration Test Suite")
    print("=" * 60)
    
    # Test Azure mode
    azure_success = test_azure_gpt4o_mini()
    
    # Test OpenRouter fallback
    openrouter_success = test_openrouter_fallback()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Azure gpt-4o-mini: {'✅ PASS' if azure_success else '❌ FAIL'}")
    print(f"   OpenRouter fallback: {'✅ PASS' if openrouter_success else '❌ FAIL'}")
    
    if azure_success and openrouter_success:
        print("\n🎉 All tests passed! Hybrid system is working correctly.")
        print("\n💡 Usage Instructions:")
        print("   - Set USE_AZURE_MODE=true to use Azure OpenAI (gpt-4o-mini)")
        print("   - Set USE_AZURE_MODE=false to use OpenRouter (qwen/qwen3-coder)")
        print("   - Default is OpenRouter mode if not specified")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)