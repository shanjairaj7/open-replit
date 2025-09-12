"""
Unified encryption/decryption utility for secure data transmission
between frontend and backend. Uses AES-256-GCM for authenticated encryption.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import secrets

# Shared secret - in production, this should be in environment variables
# and different for each deployment
ENCRYPTION_KEY = os.getenv('HORIZON_ENCRYPTION_KEY', 'horizon-2024-secure-key-change-this-in-production')
SALT_LENGTH = 32
NONCE_LENGTH = 12
TAG_LENGTH = 16
ITERATIONS = 100000

class CryptoUtils:
    """Handles encryption and decryption of sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or ENCRYPTION_KEY
        print(f"[CryptoUtils] Initialized with key length: {len(self.encryption_key)}")
    
    def _derive_key(self, salt: bytes) -> bytes:
        """Derive a 256-bit key from the password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(self.encryption_key.encode())
    
    def encrypt(self, data: Union[str, Dict, Any]) -> str:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: String or JSON-serializable object to encrypt
            
        Returns:
            Base64 encoded string containing salt:nonce:ciphertext:tag
        """
        try:
            # Convert data to bytes
            if isinstance(data, str):
                plaintext = data.encode('utf-8')
            else:
                plaintext = json.dumps(data).encode('utf-8')
            
            # Generate random salt and nonce
            salt = secrets.token_bytes(SALT_LENGTH)
            nonce = secrets.token_bytes(NONCE_LENGTH)
            
            # Derive key from password and salt
            key = self._derive_key(salt)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt the data
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Get the authentication tag
            tag = encryptor.tag
            
            # Combine salt, nonce, ciphertext, and tag
            combined = salt + nonce + ciphertext + tag
            
            # Return base64 encoded
            encrypted = base64.b64encode(combined).decode('utf-8')
            
            print(f"[CryptoUtils] Encrypted {len(plaintext)} bytes -> {len(encrypted)} chars")
            return encrypted
            
        except Exception as e:
            print(f"[CryptoUtils] Encryption error: {str(e)}")
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: str) -> Union[str, Dict]:
        """
        Decrypt data encrypted with encrypt()
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Original data (string or parsed JSON)
        """
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data)
            
            # Extract components
            salt = combined[:SALT_LENGTH]
            nonce = combined[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
            tag = combined[-TAG_LENGTH:]
            ciphertext = combined[SALT_LENGTH + NONCE_LENGTH:-TAG_LENGTH]
            
            # Derive key from password and salt
            key = self._derive_key(salt)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Decode from bytes
            decoded = plaintext.decode('utf-8')
            
            # Try to parse as JSON, otherwise return as string
            try:
                data = json.loads(decoded)
                print(f"[CryptoUtils] Decrypted {len(encrypted_data)} chars -> JSON object")
                return data
            except json.JSONDecodeError:
                print(f"[CryptoUtils] Decrypted {len(encrypted_data)} chars -> string")
                return decoded
                
        except Exception as e:
            print(f"[CryptoUtils] Decryption error: {str(e)}")
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_env_vars(self, env_vars: Dict[str, str]) -> str:
        """
        Encrypt environment variables dictionary
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            Encrypted base64 string
        """
        return self.encrypt(env_vars)
    
    def decrypt_env_vars(self, encrypted_env: str) -> Dict[str, str]:
        """
        Decrypt environment variables
        
        Args:
            encrypted_env: Encrypted environment variables string
            
        Returns:
            Dictionary of environment variables
        """
        decrypted = self.decrypt(encrypted_env)
        if not isinstance(decrypted, dict):
            raise ValueError("Decrypted data is not a dictionary")
        return decrypted
    
    def encrypt_api_key(self, key_name: str, key_value: str) -> str:
        """
        Encrypt a single API key with metadata
        
        Args:
            key_name: Name of the API key (e.g., 'STRIPE_SECRET_KEY')
            key_value: The actual key value
            
        Returns:
            Encrypted base64 string
        """
        data = {
            'key_name': key_name,
            'key_value': key_value,
            'encrypted_at': os.popen('date').read().strip()
        }
        return self.encrypt(data)
    
    def decrypt_api_key(self, encrypted_key: str) -> Dict[str, str]:
        """
        Decrypt an API key
        
        Args:
            encrypted_key: Encrypted API key string
            
        Returns:
            Dictionary with key_name and key_value
        """
        return self.decrypt(encrypted_key)


# Singleton instance for easy import
crypto = CryptoUtils()

# Convenience functions
def encrypt_data(data: Union[str, Dict]) -> str:
    """Encrypt data using the default crypto instance"""
    return crypto.encrypt(data)

def decrypt_data(encrypted_data: str) -> Union[str, Dict]:
    """Decrypt data using the default crypto instance"""
    return crypto.decrypt(encrypted_data)

def encrypt_env(env_vars: Dict[str, str]) -> str:
    """Encrypt environment variables"""
    return crypto.encrypt_env_vars(env_vars)

def decrypt_env(encrypted_env: str) -> Dict[str, str]:
    """Decrypt environment variables"""
    return crypto.decrypt_env_vars(encrypted_env)


if __name__ == "__main__":
    # Test the encryption/decryption
    print("\n=== Testing CryptoUtils ===\n")
    
    # Test 1: Simple string
    test_string = "sk_test_51234567890abcdefghijklmnop"
    print(f"Original string: {test_string}")
    encrypted = encrypt_data(test_string)
    print(f"Encrypted: {encrypted[:50]}...")
    decrypted = decrypt_data(encrypted)
    print(f"Decrypted: {decrypted}")
    assert decrypted == test_string
    print("✓ String encryption test passed\n")
    
    # Test 2: Environment variables
    test_env = {
        "STRIPE_SECRET_KEY": "sk_test_51234567890",
        "STRIPE_PUBLISHABLE_KEY": "pk_test_98765432100",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "OPENAI_API_KEY": "sk-proj-1234567890abcdef"
    }
    print(f"Original env vars: {list(test_env.keys())}")
    encrypted_env = encrypt_env(test_env)
    print(f"Encrypted env: {encrypted_env[:50]}...")
    decrypted_env = decrypt_env(encrypted_env)
    print(f"Decrypted env keys: {list(decrypted_env.keys())}")
    assert decrypted_env == test_env
    print("✓ Environment variables encryption test passed\n")
    
    # Test 3: API key with metadata
    encrypted_key = crypto.encrypt_api_key("STRIPE_SECRET_KEY", "sk_live_actualkey123")
    print(f"Encrypted API key: {encrypted_key[:50]}...")
    decrypted_key = crypto.decrypt_api_key(encrypted_key)
    print(f"Decrypted: {decrypted_key['key_name']} = {decrypted_key['key_value'][:10]}...")
    print("✓ API key encryption test passed\n")
    
    print("=== All tests passed! ===")