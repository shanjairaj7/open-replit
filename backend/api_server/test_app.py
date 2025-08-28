"""
Test Modal app with proper configuration and secret handling
"""
import os
import modal

# Use a shorter app name for testing
TEST_APP_NAME = "test-emergency-proj"
SECRET_NAME = f"{TEST_APP_NAME}-secrets"

print(f"🚀 Testing Modal app: {TEST_APP_NAME}")
print(f"📋 Using secret: {SECRET_NAME}")

# Modal app configuration
modal_app = modal.App(TEST_APP_NAME)
app = modal_app

# Modal image with dependencies from requirements.txt
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", "/root")
)

@modal_app.function(image=image)
def test_imports():
    """Test if all the problematic imports work now"""
    try:
        from passlib.context import CryptContext
        from jose import jwt, JWTError
        from fastapi import FastAPI
        from pydantic import EmailStr, BaseModel
        import bcrypt
        
        print("✅ All imports successful!")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        test_hash = pwd_context.hash("test_password")
        print(f"✅ Password hashing works: {test_hash[:20]}...")
        return {"status": "success", "message": "All imports and functionality work"}
    except Exception as e:
        print(f"❌ Import/functionality failed: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    with app.run():
        print("Testing imports and functionality...")
        result = test_imports.remote()
        print("Result:", result)