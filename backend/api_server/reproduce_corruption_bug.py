#!/usr/bin/env python3
"""
Script to reproduce the exact search/replace corruption bug.
This will demonstrate how the DiffParser is leaving ======= artifacts in files.
"""

import sys
import os
import re
from typing import List, Tuple

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from diff_parser import DiffParser

def test_corruption_reproduction():
    """Reproduce the exact corruption bug from the conversation history"""
    
    print("🔍 Testing Search/Replace Corruption Bug Reproduction")
    print("=" * 60)
    
    # Simulate a file content similar to backend/app.py
    original_file_content = '''"""
Modal.com Compatible FastAPI Backend - Production Ready Boilerplate
Main application file with dynamic configuration for mass deployment
"""

import os
import modal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "AI-powered backend service")

# Create FastAPI app with dynamic configuration
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0"
)
'''
    
    # Simulate the problematic search/replace content that caused corruption
    problematic_update_content = '''<action type="update_file" path="backend/app.py">
------- SEARCH
# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
=======
# Dynamic configuration for production deployment  
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
+++++++ REPLACE
</action>'''
    
    print("📄 Original File Content:")
    print("-" * 40)
    print(original_file_content[:400] + "...")
    
    print("\n🔧 Problematic Update Content:")  
    print("-" * 40)
    print(problematic_update_content)
    
    # Test the current DiffParser implementation
    print("\n🧪 Testing Current DiffParser Implementation...")
    print("-" * 40)
    
    try:
        # Extract just the search/replace content (without action tags)
        search_replace_content = problematic_update_content.split('<action type="update_file"')[1]
        search_replace_content = search_replace_content.split('</action>')[0]
        search_replace_content = search_replace_content.split('\n', 1)[1]  # Remove first line with path
        
        print(f"📋 Processing search/replace content:")
        print(f"Content length: {len(search_replace_content)} chars")
        print(f"Content preview: {search_replace_content[:200]}...")
        
        # Use DiffParser to process the update
        final_content, successes, failures = DiffParser.process_update_file(
            original_file_content, search_replace_content
        )
        
        print(f"\n📊 Results:")
        print(f"✅ Successes: {len(successes)}")
        for success in successes:
            print(f"   • {success}")
            
        print(f"❌ Failures: {len(failures)}")  
        for failure in failures:
            print(f"   • {failure[:100]}...")
        
        print(f"\n📄 Final File Content:")
        print("-" * 40)
        print(final_content[:500] + "..." if len(final_content) > 500 else final_content)
        
        # Check for corruption artifacts
        corruption_artifacts = []
        if "=======" in final_content:
            corruption_artifacts.append("Found ======= separator in final content")
        if "------- SEARCH" in final_content:
            corruption_artifacts.append("Found SEARCH marker in final content")
        if "+++++++ REPLACE" in final_content:
            corruption_artifacts.append("Found REPLACE marker in final content")
            
        if corruption_artifacts:
            print(f"\n🚨 CORRUPTION DETECTED:")
            for artifact in corruption_artifacts:
                print(f"   ❌ {artifact}")
        else:
            print(f"\n✅ No corruption artifacts detected")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_regex_patterns():
    """Test the regex patterns to see why they're failing"""
    
    print("\n🔬 Testing Regex Patterns in Detail")
    print("=" * 60)
    
    # Test content with the exact problematic format
    test_content = '''------- SEARCH
# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
=======
# Dynamic configuration for production deployment  
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
+++++++ REPLACE'''
    
    print("🧪 Test Content:")
    print("-" * 30)
    print(test_content)
    
    # Test the patterns from DiffParser
    print(f"\n🔍 Testing Current Regex Patterns:")
    
    # Pattern 1 from _parse_direct_search_replace
    pattern1 = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n\+{7}\s*REPLACE'
    matches1 = re.findall(pattern1, test_content, re.DOTALL)
    
    print(f"Pattern 1 matches: {len(matches1)}")
    for i, (search, replace) in enumerate(matches1):
        print(f"  Match {i+1}:")
        print(f"    Search: '{search[:50]}...'")
        print(f"    Replace: '{replace[:50]}...'")
    
    # Pattern 2 from _parse_direct_search_replace  
    pattern2 = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)(?=\n-------\s*SEARCH|\Z)'
    matches2 = re.findall(pattern2, test_content, re.DOTALL)
    
    print(f"\nPattern 2 matches: {len(matches2)}")
    for i, (search, replace) in enumerate(matches2):
        print(f"  Match {i+1}:")
        print(f"    Search: '{search[:50]}...'")  
        print(f"    Replace: '{replace[:50]}...'")
    
    # Test a corrected pattern
    print(f"\n🔧 Testing Corrected Pattern:")
    corrected_pattern = r'-------\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n\+{7}\s*REPLACE'
    corrected_matches = re.findall(corrected_pattern, test_content, re.DOTALL)
    
    print(f"Corrected pattern matches: {len(corrected_matches)}")
    for i, (search, replace) in enumerate(corrected_matches):
        print(f"  Match {i+1}:")
        print(f"    Search: '{search}'")
        print(f"    Replace: '{replace}'")

def test_apply_search_replace():
    """Test the apply_search_replace method with problematic data"""
    
    print("\n🧪 Testing apply_search_replace Method")
    print("=" * 60)
    
    # Original file content  
    file_content = '''# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "AI-powered backend service")'''
    
    # Test with exact search text that should match
    search_text = '''# Dynamic configuration for production deployment
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")'''
    
    replace_text = '''# Dynamic configuration for production deployment  
APP_NAME = os.getenv("MODAL_APP_NAME", "backend-api")
APP_TITLE = os.getenv("APP_TITLE", "AI Generated Backend")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")'''
    
    print("📄 File Content:")
    print(file_content)
    
    print(f"\n🔍 Search Text:")
    print(f"'{search_text}'")
    
    print(f"\n🔄 Replace Text:")
    print(f"'{replace_text}'")
    
    # Test the replacement
    result_content, success = DiffParser.apply_search_replace(file_content, search_text, replace_text)
    
    print(f"\n📊 Results:")
    print(f"Success: {success}")
    print(f"Result Content:")
    print("-" * 30)
    print(result_content)
    
    # Check for problems
    if "=======" in result_content:
        print(f"\n🚨 CORRUPTION: Found ======= in result!")
    if search_text in result_content and success:
        print(f"\n⚠️ WARNING: Original search text still in result (may indicate incomplete replacement)")

def main():
    """Run all corruption reproduction tests"""
    
    test_corruption_reproduction()
    test_regex_patterns() 
    test_apply_search_replace()
    
    print(f"\n🎯 CONCLUSION:")
    print(f"The corruption is likely caused by:")
    print(f"1. Regex patterns not matching the full search/replace blocks correctly")
    print(f"2. Partial content being processed, leaving artifacts like '======='")
    print(f"3. Multiple search/replace blocks not being handled properly")
    print(f"4. Error handling that continues processing even when patterns fail")

if __name__ == "__main__":
    main()