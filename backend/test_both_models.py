"""
Test both GPT-4.1 and DeepSeek models using the updated base_test_azure_hybrid.py configuration
"""
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to enable imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "api_server"))

def test_model_switching():
    """Test that both models can be selected and work properly"""
    
    print("=" * 60)
    print("TESTING BOTH GPT-4.1 AND DEEPSEEK MODELS")
    print("=" * 60)
    
    # Test GPT-4.1 (default)
    print("\n🧪 Testing GPT-4.1 (default model)...")
    os.environ.pop("MODEL_TYPE", None)  # Clear any existing setting
    
    try:
        # Import after clearing environment
        from api_server.base_test_azure_hybrid import azure_client, model_name, endpoint
        
        print(f"Model: {model_name}")
        print(f"Endpoint: {endpoint}")
        
        response = azure_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'GPT-4.1 working!'"},
            ],
            max_tokens=50
        )
        
        print(f"✅ GPT-4.1 Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ GPT-4.1 Error: {e}")
    
    # Test DeepSeek
    print("\n🧪 Testing DeepSeek model...")
    os.environ["MODEL_TYPE"] = "deepseek"
    
    # Clear imports to reload with new environment
    if 'api_server.base_test_azure_hybrid' in sys.modules:
        del sys.modules['api_server.base_test_azure_hybrid']
    
    try:
        from api_server.base_test_azure_hybrid import azure_client, model_name, endpoint
        
        print(f"Model: {model_name}")
        print(f"Endpoint: {endpoint}")
        
        response = azure_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'DeepSeek working!'"},
            ],
            max_tokens=50
        )
        
        print(f"✅ DeepSeek Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ DeepSeek Error: {e}")
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_model_switching()