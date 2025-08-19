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
                    # Check if this could possibly be <action
                    remaining = self.buffer[i:].lower()
                    if '<action'.startswith(remaining):
                        # Might be start of <action but not enough chars yet
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Not a potential <action tag, include the character
                        result += self.buffer[i]
                        i += 1
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
                    # Check if this could possibly be </action>
                    remaining = self.buffer[i:].lower()
                    if '</action>'.startswith(remaining):
                        # Might be closing tag but not enough chars yet
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Not a potential </action> tag, include the character
                        result += self.buffer[i]
                        i += 1
                else:
                    # Content inside action tag, include it
                    result += self.buffer[i]
                    i += 1
        
        # Clear buffer since we processed everything
        self.buffer = ""
        return result

def test_fragmentation_scenarios():
    """Test various stream fragmentation patterns that could break XML filtering"""
    
    scenarios = [
        {
            "name": "Normal case",
            "chunks": ['<action type="test">content</action>'],
            "expected": "content"
        },
        {
            "name": "Split opening tag",
            "chunks": ['<act', 'ion type="test">content</action>'],
            "expected": "content"
        },
        {
            "name": "Split closing tag", 
            "chunks": ['<action type="test">content</act', 'ion>'],
            "expected": "content"
        },
        {
            "name": "Split in middle of content",
            "chunks": ['<action type="test">con', 'tent</action>'],
            "expected": "content"
        },
        {
            "name": "Character by character",
            "chunks": list('<action type="test">content</action>'),
            "expected": "content"
        },
        {
            "name": "Multiple tags",
            "chunks": ['<action type="a">first</action><action type="b">second</action>'],
            "expected": "firstsecond"
        },
        {
            "name": "Mixed content with splits",
            "chunks": ['Hello <act', 'ion type="test">wor', 'ld</action> end'],
            "expected": "Hello world end"
        },
        {
            "name": "Complex attributes split",
            "chunks": ['<action type="todo_create" id="test"', ' priority="high">content</act', 'ion>'],
            "expected": "content"
        },
        {
            "name": "Self-closing tag",
            "chunks": ['<action type="test"/>'],
            "expected": ""
        },
        {
            "name": "Self-closing with content around",
            "chunks": ['Before <action type="test"/> After'],
            "expected": "Before  After"
        },
        {
            "name": "Nested-like patterns (not real nesting)",
            "chunks": ['<action type="outer">content with <something> inside</action>'],
            "expected": "content with <something> inside"
        },
        {
            "name": "Very fragmented opening",
            "chunks": ['<', 'a', 'c', 't', 'i', 'o', 'n', ' ', 't', 'y', 'p', 'e', '=', '"', 't', 'e', 's', 't', '"', '>', 'content', '<', '/', 'a', 'c', 't', 'i', 'o', 'n', '>'],
            "expected": "content"
        },
        {
            "name": "Empty action tag",
            "chunks": ['<action type="test"></action>'],
            "expected": ""
        },
        {
            "name": "Action tag with newlines",
            "chunks": ['<action type="test">\ncontent with\nnewlines\n</action>'],
            "expected": "\ncontent with\nnewlines\n"
        },
        {
            "name": "Partial '<' at end",
            "chunks": ['content <'],
            "expected": "content "
        },
        {
            "name": "False alarm - not action tag",
            "chunks": ['<div>content</div>'],
            "expected": "<div>content</div>"
        }
    ]
    
    print("🧪 Testing XML filtering with various fragmentation scenarios...")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        filter = StreamingXMLFilter()
        result = ""
        
        # Process all chunks
        for chunk in scenario["chunks"]:
            filtered = filter.process_chunk(chunk)
            result += filtered
        
        # Check result
        success = result == scenario["expected"]
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"{status} {scenario['name']}")
        print(f"    Input chunks: {scenario['chunks']}")
        print(f"    Expected: {repr(scenario['expected'])}")
        print(f"    Got:      {repr(result)}")
        
        if success:
            passed += 1
        else:
            failed += 1
            # Show detailed diff for failures
            print(f"    Buffer state: {repr(filter.buffer)}")
            print(f"    Inside tag: {filter.inside_action_tag}")
        
        print()
    
    print("=" * 80)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("❌ XML filtering needs improvement to handle all fragmentation patterns!")
    else:
        print("✅ XML filtering handles all fragmentation patterns correctly!")

if __name__ == "__main__":
    test_fragmentation_scenarios()