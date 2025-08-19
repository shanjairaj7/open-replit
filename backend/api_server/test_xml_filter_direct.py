#!/usr/bin/env python3

# Test the StreamingXMLFilter directly
import sys
sys.path.append('.')

from index_fixed_azure_hybrid import StreamingXMLFilter

def test_xml_filter_direct():
    """Test the StreamingXMLFilter with simulated streaming chunks"""
    print("🧪 Testing StreamingXMLFilter directly...")
    
    filter = StreamingXMLFilter()
    
    # Simulate streaming chunks as the AI model would send them
    chunks = [
        "I'll create a ",
        "<action type=\"todo_create\" id=\"test\">",
        "Create a todo item",
        "</action>",
        " for you."
    ]
    
    print("Input chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}] {repr(chunk)}")
    
    print("\nFiltered output:")
    all_filtered = ""
    for i, chunk in enumerate(chunks):
        filtered = filter.process_chunk(chunk)
        if filtered:
            print(f"  [{i+1}] {repr(filtered)}")
            all_filtered += filtered
        else:
            print(f"  [{i+1}] (filtered out)")
    
    print(f"\nFinal result: {repr(all_filtered)}")
    expected = "I'll create a Create a todo item for you."
    print(f"Expected: {repr(expected)}")
    
    success = all_filtered == expected
    print(f"✅ Test {'PASSED' if success else 'FAILED'}")

def test_character_by_character():
    """Test with character-by-character streaming like the real API"""
    print("\n🧪 Testing character-by-character streaming...")
    
    filter = StreamingXMLFilter()
    
    # Simulate the exact streaming pattern from the AI
    input_text = '<action type="todo_create" id="test">Create todo</action>'
    
    print(f"Input text: {repr(input_text)}")
    print("Character by character filtering:")
    
    all_filtered = ""
    for i, char in enumerate(input_text):
        filtered = filter.process_chunk(char)
        if filtered:
            print(f"  [{i+1:02d}] {repr(char)} -> {repr(filtered)}")
            all_filtered += filtered
        else:
            print(f"  [{i+1:02d}] {repr(char)} -> (filtered)")
    
    print(f"\nFinal result: {repr(all_filtered)}")
    print(f"Expected: {repr('Create todo')}")
    
    success = all_filtered == "Create todo"
    print(f"✅ Test {'PASSED' if success else 'FAILED'}")

if __name__ == "__main__":
    test_xml_filter_direct()
    test_character_by_character()