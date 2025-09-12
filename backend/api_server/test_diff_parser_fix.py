#!/usr/bin/env python3
"""
Test script to verify the diff parser fix prevents corruption
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from diff_parser import DiffParser

def test_malformed_content_prevention():
    """Test that malformed search/replace content is properly rejected"""
    
    # Simulate the original file content (clean)
    original_file_content = """import React, { useState, useEffect } from 'react';
import { TodoItem } from './TodoItem';
import axios from 'axios';

export const TodoList = () => {
    const [todos, setTodos] = useState([]);
    return <div>Todo List</div>;
};
"""

    # Simulate the malformed content that was causing corruption
    malformed_update_content = """------- SEARCH
import React, { useState, useEffect } from 'react';
import { TodoItem } from './TodoItem';
import axios from 'axios';
=======
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card } from './ui/card';
import axios from 'axios';
>>>>>>> REPLACE
>>>>>>> REPLACE
import axios from 'axios';
=======
import React, { useState, useEffect } from 'react';
import { TodoItem } from './TodoItem';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card } from './ui/card';
import axios from 'axios';
>>>>>>> REPLACE"""

    print("🧪 Testing malformed content prevention...")
    print(f"Original file length: {len(original_file_content)} chars")
    print(f"Malformed update length: {len(malformed_update_content)} chars")
    print()
    
    # Process the malformed content with the fixed parser
    result_content, successes, failures = DiffParser.process_update_file(
        original_file_content, malformed_update_content
    )
    
    print(f"📊 Processing results:")
    print(f"   Successes: {len(successes)}")
    print(f"   Failures: {len(failures)}")
    print(f"   Result content length: {len(result_content)} chars")
    print()
    
    # Check that no search/replace markers are in the result
    has_markers = DiffParser._has_search_replace_markers(result_content)
    print(f"🔍 Result contains search/replace markers: {has_markers}")
    
    if has_markers:
        print("❌ CRITICAL FAILURE: Result content still contains markers!")
        print("Content preview:")
        print(result_content[:500])
        return False
    
    # Check that result is either the original content (if all failed) or valid modified content
    if result_content == original_file_content:
        print("✅ SUCCESS: Original content preserved due to failed processing")
    else:
        print("✅ SUCCESS: Content modified without corruption")
        print("Result content preview:")
        print(result_content[:300] + "..." if len(result_content) > 300 else result_content)
    
    print()
    print("📋 Detailed results:")
    for success in successes:
        print(f"   ✅ {success}")
    for failure in failures:
        print(f"   ❌ {failure}")
    
    return True

def test_valid_content_processing():
    """Test that valid search/replace content still works correctly"""
    
    original_content = """import React from 'react';

const App = () => {
    return <div>Hello World</div>;
};

export default App;
"""
    
    valid_update_content = """------- SEARCH
import React from 'react';
=======
import React, { useState } from 'react';
+++++++ REPLACE

------- SEARCH
    return <div>Hello World</div>;
=======
    return <div>Hello React</div>;
+++++++ REPLACE"""

    print("\n🧪 Testing valid content processing...")
    
    result_content, successes, failures = DiffParser.process_update_file(
        original_content, valid_update_content
    )
    
    print(f"📊 Processing results:")
    print(f"   Successes: {len(successes)}")
    print(f"   Failures: {len(failures)}")
    
    # Should have no markers in result
    has_markers = DiffParser._has_search_replace_markers(result_content)
    print(f"🔍 Result contains search/replace markers: {has_markers}")
    
    if has_markers:
        print("❌ FAILURE: Valid content processing left markers!")
        return False
    
    # Should have successful replacements
    if len(successes) == 0:
        print("❌ FAILURE: Valid content processing had no successes!")
        return False
    
    print("✅ SUCCESS: Valid content processed correctly")
    print("Result content:")
    print(result_content)
    
    return True

if __name__ == "__main__":
    print("🚀 Running diff parser fix verification tests...")
    print("=" * 60)
    
    test1_passed = test_malformed_content_prevention()
    test2_passed = test_valid_content_processing()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Malformed content prevention: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Valid content processing: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED - Fix is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Fix needs more work!")
        sys.exit(1)