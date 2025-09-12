"""
Test script to verify encryption/decryption compatibility between
frontend JavaScript and backend Python implementations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.crypto_utils import CryptoUtils, encrypt_data, decrypt_data, encrypt_env, decrypt_env

def test_compatibility():
    """Test that backend can decrypt frontend-encrypted data and vice versa"""
    
    print("\n" + "="*50)
    print("CRYPTO COMPATIBILITY TEST")
    print("="*50 + "\n")
    
    # Test data that would come from frontend
    test_cases = [
        {
            "name": "Simple API Key",
            "data": "sk_test_1234567890abcdefghijklmnop",
            "type": "string"
        },
        {
            "name": "Environment Variables",
            "data": {
                "STRIPE_SECRET_KEY": "sk_test_51234567890",
                "STRIPE_PUBLISHABLE_KEY": "pk_test_98765432100",
                "DATABASE_URL": "postgresql://user:pass@localhost/db",
                "OPENAI_API_KEY": "sk-proj-1234567890abcdef"
            },
            "type": "dict"
        },
        {
            "name": "Complex JSON Structure",
            "data": {
                "api_keys": {
                    "stripe": {
                        "test": "sk_test_xxx",
                        "live": "sk_live_xxx"
                    },
                    "openai": "sk-proj-xxx"
                },
                "config": {
                    "debug": True,
                    "port": 3000,
                    "features": ["auth", "payments", "analytics"]
                }
            },
            "type": "dict"
        }
    ]
    
    print("Backend Python Implementation Test")
    print("-" * 40)
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        data = test_case['data']
        
        # Encrypt
        encrypted = encrypt_data(data)
        print(f"  Original: {str(data)[:50]}...")
        print(f"  Encrypted: {encrypted[:50]}...")
        
        # Decrypt
        decrypted = decrypt_data(encrypted)
        print(f"  Decrypted: {str(decrypted)[:50]}...")
        
        # Verify
        if test_case['type'] == 'string':
            assert decrypted == data, f"Mismatch: {decrypted} != {data}"
        else:
            assert decrypted == data, f"Mismatch in dict comparison"
        
        print(f"  ✓ Test passed!")
    
    print("\n" + "="*50)
    print("FRONTEND COMPATIBILITY STRINGS")
    print("="*50 + "\n")
    
    print("Copy these encrypted strings to test in the browser console:\n")
    
    # Generate test strings for frontend
    test_env = {
        "STRIPE_SECRET_KEY": "sk_test_51H3gGKEcXKLcRqYp5QW8vW3U",
        "STRIPE_PUBLISHABLE_KEY": "pk_test_51H3gGKEcXKLcRqYpKXu8zR9J",
        "OPENAI_API_KEY": "sk-proj-abcdef1234567890",
        "DATABASE_URL": "postgresql://admin:secretpass@db.example.com:5432/myapp"
    }
    
    encrypted_env = encrypt_env(test_env)
    
    print("// Test in browser console:")
    print("// 1. Open the app and open browser console")
    print("// 2. Copy and paste this code:\n")
    
    print(f"""
const testEncryptedEnv = "{encrypted_env}";

// Import the crypto utils (adjust path as needed)
import('src/utils/cryptoUtils.js').then(async (module) => {{
    const {{ decryptEnv, encryptEnv }} = module;
    
    console.log('Testing backend-encrypted data...');
    const decrypted = await decryptEnv(testEncryptedEnv);
    console.log('Decrypted:', decrypted);
    
    // Test round-trip
    console.log('\\nTesting round-trip encryption...');
    const testData = {{
        MY_API_KEY: 'test_key_123',
        MY_SECRET: 'super_secret_value'
    }};
    
    const encrypted = await encryptEnv(testData);
    console.log('Frontend encrypted:', encrypted);
    console.log('\\nCopy the encrypted string above and test it in Python with:');
    console.log('from utils.crypto_utils import decrypt_env');
    console.log('decrypt_env("PASTE_ENCRYPTED_STRING_HERE")');
}});
""")
    
    print("\n" + "="*50)
    print("BACKEND DECRYPTION TEST")
    print("="*50 + "\n")
    
    print("To test frontend-encrypted data in Python:")
    print("1. Run the JavaScript code above in browser console")
    print("2. Copy the encrypted string from 'Frontend encrypted:'")
    print("3. Run this Python code:\n")
    
    print("""
from utils.crypto_utils import decrypt_env

# Paste the encrypted string from browser here
encrypted_from_frontend = "PASTE_ENCRYPTED_STRING_HERE"
decrypted = decrypt_env(encrypted_from_frontend)
print("Decrypted from frontend:", decrypted)
""")
    
    print("\n" + "="*50)
    print("ALL BACKEND TESTS PASSED!")
    print("="*50 + "\n")

if __name__ == "__main__":
    # Test if cryptography is installed
    try:
        import cryptography
        print(f"✓ cryptography library installed (version {cryptography.__version__})")
    except ImportError:
        print("⚠ cryptography library not installed!")
        print("Run: pip install cryptography")
        sys.exit(1)
    
    test_compatibility()