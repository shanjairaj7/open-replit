"""
Test DeepSeek R1 model via OpenAI package with Azure endpoint
"""
import os
from openai import AzureOpenAI

def test_deepseek_azure():
    """Test DeepSeek R1 model through Azure using OpenAI package"""
    
    # Azure DeepSeek endpoint configuration - using base endpoint like GPT-4.1
    endpoint = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com"
    model_name = "DeepSeek-R1-0528"
    api_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
    api_version = "2024-05-01-preview"  # DeepSeek specific API version
    
    print(f"Testing DeepSeek R1 model: {model_name}")
    print(f"Endpoint: {endpoint}")
    print(f"API Version: {api_version}")
    
    try:
        # Create Azure OpenAI client (same pattern as GPT-4.1)
        client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
        )
        print("✅ Azure OpenAI client created successfully")
        
        # Test basic completion
        print("\n🧪 Testing basic completion...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! Can you tell me a joke about programming?"},
            ],
            max_tokens=2048
        )
        
        print("✅ Response received:")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Usage: {response.usage}")
        
        # Test multi-turn conversation
        print("\n🧪 Testing multi-turn conversation...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful coding assistant."},
                {"role": "user", "content": "Write a simple Python function to calculate factorial."},
            ],
            max_tokens=1500
        )
        
        print("✅ Multi-turn response:")
        print(f"Content: {response.choices[0].message.content[:200]}...")
        
        # Test with different parameters
        print("\n🧪 Testing with different parameters...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Explain machine learning in one sentence."},
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print("✅ Parameter test response:")
        print(f"Content: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing DeepSeek: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DEEPSEEK R1 AZURE INTEGRATION TEST")
    print("=" * 60)
    
    success = test_deepseek_azure()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS: DeepSeek Azure integration working!")
    else:
        print("❌ FAILED: DeepSeek Azure integration has issues")
    print("=" * 60)