#!/usr/bin/env python3
"""
Test script to validate the read-before-update system
"""

import os
import subprocess
import sys


def main():
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable is required")
        return

    # Test message that tries to update a file without reading it first
    test_message = """Update the NoteEditor.tsx file to add a new feature - add a character counter that shows at the bottom of the text area. Just add this simple feature without reading the file first."""

    print("🔧 Testing read-before-update validation...")
    print(f"📝 Test message: {test_message}")
    print("🎯 Expected: System should stop generation and require reading file first")
    
    # Run the update command
    cmd = [
        "python3", 
        "test_groq_project_update.py", 
        "--project-id", "place-just-write-notes-0801",
        "--message", test_message
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        print(f"\n✅ Command completed with return code: {result.returncode}")
    except Exception as e:
        print(f"❌ Error running command: {e}")

if __name__ == "__main__":
    main()