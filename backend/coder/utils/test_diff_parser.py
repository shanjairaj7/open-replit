#!/usr/bin/env python3
"""
Comprehensive test suite for the diff parser functionality
Tests various search/replace scenarios with real files
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to import diff_parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diff_parser import DiffParser

def print_test_header(test_name):
    """Print a formatted test header"""
    print(f"\n{'='*60}")
    print(f" TEST: {test_name}")
    print(f"{'='*60}")

def print_result(success, message):
    """Print test result with color"""
    if success:
        print(f"✅ PASS: {message}")
    else:
        print(f"❌ FAIL: {message}")

def test_parse_diff_content():
    """Test parsing of diff content into search/replace pairs"""
    print_test_header("Parse Diff Content")
    
    # Test 1: Single search/replace block
    content1 = """<diff>
------- SEARCH
def old_function():
    return "old"
=======
def new_function():
    return "new"
+++++++ REPLACE
</diff>"""
    
    pairs = DiffParser.parse_diff_content(content1)
    expected_search = 'def old_function():\n    return "old"'
    expected_replace = 'def new_function():\n    return "new"'
    
    success = (len(pairs) == 1 and 
               pairs[0][0] == expected_search and 
               pairs[0][1] == expected_replace)
    print_result(success, f"Single diff block parsing - Found {len(pairs)} pairs")
    if not success:
        print(f"  Expected search: {repr(expected_search)}")
        print(f"  Got search: {repr(pairs[0][0] if pairs else 'None')}")
    
    # Test 2: Multiple search/replace blocks
    content2 = """<diff>
------- SEARCH
import old_module
=======
import new_module
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
OLD_CONSTANT = 42
=======
NEW_CONSTANT = 100
+++++++ REPLACE
</diff>"""
    
    pairs = DiffParser.parse_diff_content(content2)
    success = len(pairs) == 2
    print_result(success, f"Multiple diff blocks - Found {len(pairs)} pairs")
    
    # Test 3: Legacy format (no diff blocks)
    content3 = """def simple_function():
    return "This is legacy format"
"""
    
    pairs = DiffParser.parse_diff_content(content3)
    success = len(pairs) == 1 and pairs[0][0] is None
    print_result(success, f"Legacy format (no diff) - Detected as full replacement")
    
    # Test 4: Malformed diff block (should fall back to legacy)
    content4 = """<diff>
This is malformed
</diff>"""
    
    pairs = DiffParser.parse_diff_content(content4)
    success = len(pairs) == 1 and pairs[0][0] is None
    print_result(success, f"Malformed diff block - Falls back to legacy format")
    
    # Test 5: Empty search/replace
    content5 = """<diff>
------- SEARCH
OLD_LINE
=======

+++++++ REPLACE
</diff>"""
    
    pairs = DiffParser.parse_diff_content(content5)
    success = len(pairs) == 1 and pairs[0][1] == ""
    print_result(success, f"Empty replacement (deletion) - Correctly parsed")

def test_apply_search_replace():
    """Test applying search/replace operations"""
    print_test_header("Apply Search/Replace")
    
    # Test 1: Successful replacement
    original = """def hello():
    print("Hello")
    
def goodbye():
    print("Goodbye")"""
    
    search = """def hello():
    print("Hello")"""
    
    replace = """def hello():
    print("Hello, World!")"""
    
    result, success = DiffParser.apply_search_replace(original, search, replace)
    expected = """def hello():
    print("Hello, World!")
    
def goodbye():
    print("Goodbye")"""
    
    print_result(success and result == expected, "Basic replacement")
    
    # Test 2: Search text not found
    result, success = DiffParser.apply_search_replace(original, "not_found", "replacement")
    print_result(not success and result == original, "Search text not found - Original unchanged")
    
    # Test 3: Legacy format (None search)
    result, success = DiffParser.apply_search_replace(original, None, "complete replacement")
    print_result(success and result == "complete replacement", "Legacy format - Full replacement")
    
    # Test 4: Replace only first occurrence
    original_dup = """value = 1
value = 2
value = 3"""
    
    result, success = DiffParser.apply_search_replace(original_dup, "value = 1", "value = 100")
    expected_dup = """value = 100
value = 2
value = 3"""
    
    print_result(success and result == expected_dup, "First occurrence only replaced")

def test_process_update_file():
    """Test complete update file processing"""
    print_test_header("Process Update File")
    
    # Original file content
    original_content = """import os
import sys

class OldClass:
    def __init__(self):
        self.value = 42
    
    def old_method(self):
        return "old"

def helper_function():
    return OldClass()
"""
    
    # Update with multiple search/replace blocks
    update_content = """<diff>
------- SEARCH
class OldClass:
=======
class NewClass:
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    def old_method(self):
        return "old"
=======
    def new_method(self):
        return "new"
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
    return OldClass()
=======
    return NewClass()
+++++++ REPLACE
</diff>"""
    
    final_content, successes, failures = DiffParser.process_update_file(original_content, update_content)
    
    print(f"Successes: {len(successes)}")
    for s in successes:
        print(f"  ✓ {s}")
    
    print(f"Failures: {len(failures)}")
    for f in failures:
        print(f"  ✗ {f}")
    
    # Check if all replacements worked
    success = (len(successes) == 3 and len(failures) == 0 and
               "NewClass" in final_content and
               "new_method" in final_content and
               "OldClass" not in final_content)
    
    print_result(success, "Multiple replacements processed correctly")

def test_with_real_files():
    """Test with actual files using the backend boilerplate"""
    print_test_header("Real File Testing with Backend Boilerplate")
    
    # Create a temporary test file
    test_dir = tempfile.mkdtemp(prefix="diff_parser_test_")
    test_file = os.path.join(test_dir, "test_service.py")
    
    try:
        # Create initial file content
        initial_content = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db_config import get_db

router = APIRouter()

@router.get("/test")
def test_endpoint(db: Session = Depends(get_db)):
    return {"status": "ok", "message": "Test endpoint"}

@router.post("/create")
def create_item(data: dict, db: Session = Depends(get_db)):
    # TODO: Implement creation logic
    return {"created": True}
"""
        
        # Write initial content
        with open(test_file, 'w') as f:
            f.write(initial_content)
        
        print(f"Created test file: {test_file}")
        
        # Test 1: Update a single function
        update1 = """<diff>
------- SEARCH
@router.get("/test")
def test_endpoint(db: Session = Depends(get_db)):
    return {"status": "ok", "message": "Test endpoint"}
=======
@router.get("/test")
def test_endpoint(db: Session = Depends(get_db)):
    # Enhanced endpoint with logging
    print("Test endpoint called")
    return {"status": "ok", "message": "Enhanced test endpoint", "version": "2.0"}
+++++++ REPLACE
</diff>"""
        
        with open(test_file, 'r') as f:
            current_content = f.read()
        
        final_content, successes, failures = DiffParser.process_update_file(current_content, update1)
        
        # Write back the updated content
        with open(test_file, 'w') as f:
            f.write(final_content)
        
        success = len(successes) == 1 and len(failures) == 0 and "Enhanced test endpoint" in final_content
        print_result(success, "Updated single function in real file")
        
        # Test 2: Multiple updates
        update2 = """<diff>
------- SEARCH
from db_config import get_db
=======
from db_config import get_db
from models.auth_models import UserResponse
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
@router.post("/create")
def create_item(data: dict, db: Session = Depends(get_db)):
    # TODO: Implement creation logic
    return {"created": True}
=======
@router.post("/create")
def create_item(data: dict, db: Session = Depends(get_db)):
    # Full implementation
    new_item = {"id": 1, "data": data}
    db.add(new_item)  # Simulated
    db.commit()  # Simulated
    return {"created": True, "item": new_item}
+++++++ REPLACE
</diff>"""
        
        with open(test_file, 'r') as f:
            current_content = f.read()
        
        final_content, successes, failures = DiffParser.process_update_file(current_content, update2)
        
        with open(test_file, 'w') as f:
            f.write(final_content)
        
        success = (len(successes) == 2 and len(failures) == 0 and 
                  "UserResponse" in final_content and 
                  "Full implementation" in final_content)
        print_result(success, "Multiple updates applied successfully")
        
        # Test 3: Failed search (text not found)
        update3 = """<diff>
------- SEARCH
def non_existent_function():
    pass
=======
def new_function():
    return "new"
+++++++ REPLACE
</diff>"""
        
        with open(test_file, 'r') as f:
            current_content = f.read()
        
        final_content, successes, failures = DiffParser.process_update_file(current_content, update3)
        
        success = len(failures) == 1 and "not found" in failures[0]
        print_result(success, "Correctly reported search failure")
        
        # Test 4: Mixed success and failure
        update4 = """<diff>
------- SEARCH
router = APIRouter()
=======
router = APIRouter(prefix="/api/v2")
+++++++ REPLACE
</diff>
<diff>
------- SEARCH
NONEXISTENT = True
=======
EXISTENT = False
+++++++ REPLACE
</diff>"""
        
        with open(test_file, 'r') as f:
            current_content = f.read()
        
        final_content, successes, failures = DiffParser.process_update_file(current_content, update4)
        
        success = len(successes) == 1 and len(failures) == 1
        print_result(success, "Mixed success/failure handled correctly")
        
        # Display final file content
        print("\nFinal file content preview:")
        print("-" * 40)
        with open(test_file, 'r') as f:
            lines = f.readlines()[:15]
            for i, line in enumerate(lines, 1):
                print(f"{i:3}: {line}", end='')
        print("-" * 40)
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

def test_edge_cases():
    """Test edge cases and special scenarios"""
    print_test_header("Edge Cases")
    
    # Test 1: Whitespace preservation
    original = """    def indented_function():
        return "value"
"""
    
    update = """<diff>
------- SEARCH
    def indented_function():
        return "value"
=======
    def indented_function():
        # Comment added
        return "new_value"
+++++++ REPLACE
</diff>"""
    
    final, successes, failures = DiffParser.process_update_file(original, update)
    success = len(successes) == 1 and '    def indented_function():' in final
    print_result(success, "Whitespace/indentation preserved")
    
    # Test 2: Empty file handling
    empty_original = ""
    update = """<diff>
------- SEARCH
OLD
=======
NEW
+++++++ REPLACE
</diff>"""
    
    final, successes, failures = DiffParser.process_update_file(empty_original, update)
    success = len(failures) == 1
    print_result(success, "Empty file handled correctly")
    
    # Test 3: Large block replacement
    large_original = "\n".join([f"line_{i}" for i in range(100)])
    search_block = "\n".join([f"line_{i}" for i in range(10, 20)])
    replace_block = "REPLACED_BLOCK"
    
    update = f"""<diff>
------- SEARCH
{search_block}
=======
{replace_block}
+++++++ REPLACE
</diff>"""
    
    final, successes, failures = DiffParser.process_update_file(large_original, update)
    success = len(successes) == 1 and "REPLACED_BLOCK" in final
    print_result(success, "Large block replacement")
    
    # Test 4: Special characters in search
    original_special = """def function():
    return "string with 'quotes' and \"double quotes\""
"""
    
    update_special = """<diff>
------- SEARCH
    return "string with 'quotes' and \"double quotes\""
=======
    return 'updated string with special chars: $@#%'
+++++++ REPLACE
</diff>"""
    
    final, successes, failures = DiffParser.process_update_file(original_special, update_special)
    success = len(successes) == 1 and "special chars" in final
    print_result(success, "Special characters handled")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print(" DIFF PARSER TEST SUITE")
    print("="*60)
    
    test_parse_diff_content()
    test_apply_search_replace()
    test_process_update_file()
    test_with_real_files()
    test_edge_cases()
    
    print("\n" + "="*60)
    print(" TEST SUITE COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()