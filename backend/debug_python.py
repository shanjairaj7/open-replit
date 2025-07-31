#!/usr/bin/env python3
import sys
import os
import subprocess

print("🔍 Python Environment Debug")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

print("\n🔍 Current directory:")
print(f"Current working directory: {os.getcwd()}")

print("\n🔍 Environment variables:")
api_key = os.getenv('GROQ_API_KEY')
if api_key:
    print(f"GROQ_API_KEY: {'*' * len(api_key[:-4]) + api_key[-4:]}")
else:
    print("GROQ_API_KEY: Not set")

print("\n🔍 Trying to import groq:")
try:
    import groq
    print(f"✅ groq imported successfully: {groq.__version__}")
except ImportError as e:
    print(f"❌ groq import failed: {e}")
    print("Need to install groq package")

print("\n🔍 Checking if virtual env is activated:")
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("✅ Virtual environment is active")
else:
    print("❌ Virtual environment is not active")

print("\n🔍 Installed packages:")
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                          capture_output=True, text=True, timeout=10)
    print(result.stdout)
except Exception as e:
    print(f"Failed to get pip list: {e}")