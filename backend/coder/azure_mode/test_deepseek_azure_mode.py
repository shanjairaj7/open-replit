#!/usr/bin/env python3
"""
Test script to verify DeepSeek-R1 works with Azure mode
"""

import sys
from pathlib import Path

# Add parent directories to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from coder.azure_mode.base_azure import BoilerplatePersistentGroq

def test_deepseek_azure_mode():
    """Test DeepSeek-R1 through Azure mode"""
    print("🚀 Testing DeepSeek-R1 with Azure Mode")
    print("=" * 60)
    
    # Create a simple test project
    test_request = "Create a simple Python function that calculates factorial"
    
    try:
        # Initialize the Azure mode with DeepSeek
        print("📝 Initializing Azure mode...")
        agent = BoilerplatePersistentGroq(
            project_name="test-deepseek-factorial"
        )
        
        print(f"✅ Azure mode initialized")
        print(f"🤖 Model: {agent.model}")
        print(f"📍 Endpoint: {agent.client.base_url if hasattr(agent.client, 'base_url') else 'Azure Endpoint'}")
        print(f"📁 Project: {agent.project_name}")
        
        # Test a simple completion
        print("\n📨 Sending test request...")
        print(f"Request: {test_request}")
        print("-" * 40)
        
        # Call the coder function (imported in base_azure.py)
        from coder.azure_mode.index_fixed_azure import coder
        
        # Create a simple test conversation
        messages = [
            {"role": "user", "content": test_request}
        ]
        
        # Run the coder (note: function signature is coder(messages, self))
        result = coder(messages, agent)
        
        print("-" * 40)
        print("✅ Test completed successfully!")
        
        # Check if result contains code
        if "def" in result and "factorial" in result.lower():
            print("✅ Factorial function generated correctly")
        else:
            print("⚠️  Result may not contain expected factorial function")
        
        # Display token usage if available
        if hasattr(agent, 'token_usage'):
            print(f"\n💰 Token Usage:")
            print(f"  • Total tokens: {agent.token_usage.get('total_tokens', 0)}")
            print(f"  • Prompt tokens: {agent.token_usage.get('prompt_tokens', 0)}")
            print(f"  • Completion tokens: {agent.token_usage.get('completion_tokens', 0)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streaming_directly():
    """Test streaming directly with the Azure client"""
    print("\n" + "=" * 60)
    print("🚀 Direct Streaming Test with DeepSeek-R1")
    print("=" * 60)
    
    from coder.azure_mode.base_azure import azure_client, deployment
    
    try:
        print(f"Model: {deployment}")
        print("Sending streaming request...")
        
        response = azure_client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2? Answer in one word."}
            ],
            stream=True,
            stream_options={"include_usage": True},
            max_tokens=50
        )
        
        print("Response: ", end='')
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    print(delta.content, end='', flush=True)
            
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = chunk.usage
        
        print()
        if 'usage' in locals():
            print(f"Tokens: {usage.total_tokens}")
        
        print("✅ Direct streaming test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 DeepSeek-R1 Azure Mode Test Suite\n")
    
    # Run direct streaming test first (simpler)
    test1_passed = test_streaming_directly()
    
    # Run full Azure mode test
    test2_passed = test_deepseek_azure_mode()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Direct Streaming: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Azure Mode Integration: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! DeepSeek-R1 is working in Azure mode!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")