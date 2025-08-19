#!/usr/bin/env python3

class StreamingXMLFilter:
    """Smart filter to exclude XML action tags from streaming content"""
    
    def __init__(self):
        self.buffer = ""
        self.inside_action_tag = False
        self.pending_output = ""
    
    def process_chunk(self, content: str) -> str:
        """
        Process a streaming chunk and return filtered content.
        Filters out XML action tags but keeps content inside them.
        """
        self.buffer += content
        result = ""
        
        # Process the buffer looking for complete patterns
        i = 0
        while i < len(self.buffer):
            if not self.inside_action_tag:
                # Look for start of action tag
                if self.buffer[i:].startswith('<action'):
                    # Found opening action tag, find the end
                    tag_end = self.buffer.find('>', i)
                    if tag_end == -1:
                        # Tag not complete, keep remaining in buffer
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Skip the opening tag completely
                        self.inside_action_tag = True
                        i = tag_end + 1
                elif self.buffer[i] == '<' and len(self.buffer[i:]) < 7:
                    # Might be start of <action but not enough chars yet
                    self.buffer = self.buffer[i:]
                    return result
                else:
                    # Regular character, add to result
                    result += self.buffer[i]
                    i += 1
            else:
                # We're inside action tag, look for closing tag
                if self.buffer[i:].startswith('</action>'):
                    # Found complete closing tag
                    self.inside_action_tag = False
                    i += 9  # Skip '</action>'
                elif self.buffer[i] == '<' and len(self.buffer[i:]) < 9:
                    # Might be closing tag but not enough chars yet
                    self.buffer = self.buffer[i:]
                    return result
                else:
                    # Content inside action tag, include it
                    result += self.buffer[i]
                    i += 1
        
        # Clear buffer since we processed everything
        self.buffer = ""
        return result

def test_character_by_character():
    """Test with character-by-character streaming like the real API"""
    print("🧪 Testing character-by-character streaming...")
    
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
    
    # Test with mixed content
    print("\n🧪 Testing mixed content...")
    filter2 = StreamingXMLFilter()
    
    mixed_input = 'Hello <action type="test">action content</action> world!'
    mixed_filtered = ""
    
    for char in mixed_input:
        filtered = filter2.process_chunk(char)
        mixed_filtered += filtered
    
    print(f"Input: {repr(mixed_input)}")
    print(f"Output: {repr(mixed_filtered)}")
    print(f"Expected: {repr('Hello action content world!')}")
    
    success2 = mixed_filtered == "Hello action content world!"
    print(f"✅ Mixed test {'PASSED' if success2 else 'FAILED'}")

if __name__ == "__main__":
    test_character_by_character()