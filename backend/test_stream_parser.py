#!/usr/bin/env python3
"""Test the StreamingXMLParser to see how it handles multiple action tags and real-time interrupts"""

from shared_models import StreamingXMLParser

def test_multiple_actions():
    """Test if parser can handle multiple action tags in a single chunk"""
    print("TEST 1: Multiple action tags in one chunk")
    print("="*60)
    
    parser = StreamingXMLParser()
    
    # Test content with multiple actions
    test_content = """Here's some text before actions.
    
<action type="read_file" path="test1.py"/>

<action type="run_command" command="python test.py" cwd="backend"/>

<action type="file" filePath="new_file.py">
def hello():
    print("Hello world")
</action>

<action type="update_file" path="existing.py">
# Updated content
def updated():
    pass
</action>

Some text after actions."""

    # Process the entire content at once
    actions = list(parser.process_chunk(test_content))
    
    print(f"Found {len(actions)} actions:")
    for i, action in enumerate(actions):
        print(f"\nAction {i+1}:")
        print(f"  Type: {action['type']}")
        print(f"  Path: {action.get('path', 'N/A')}")
        print(f"  Command: {action.get('command', 'N/A')}")
        print(f"  Content preview: {action.get('content', '')[:50]}...")


def test_streaming_interrupts():
    """Test if parser handles actions appearing in real-time streaming"""
    print("\n\nTEST 2: Streaming with interrupts")
    print("="*60)
    
    parser = StreamingXMLParser()
    
    # Simulate streaming chunks
    chunks = [
        "Starting to write some code...\n\n",
        "<action type=\"read_file\" ",
        "path=\"config.py\"/>",
        "\n\nNow let's run a command:\n",
        "<action type=\"run_command\" command=\"ls -la\" cwd=\"",
        "backend\"/>\n\n",
        "And create a file:\n<action type=\"file\" filePath=\"test.py\">",
        "import os\n\ndef main():\n    ",
        "print('Hello')\n</action>",
        "\n\nFinally update a file:\n",
        "<action type=\"update_file\" path=\"main.py\">",
        "# Updated main\nimport sys\n",
        "</action>\n\nDone!"
    ]
    
    all_actions = []
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}: {repr(chunk[:30])}...")
        actions = list(parser.process_chunk(chunk))
        
        if actions:
            print(f"  → Found {len(actions)} action(s)")
            for action in actions:
                print(f"     - {action['type']}: {action.get('path', action.get('command', 'N/A'))}")
                all_actions.append(action)
                
                # Simulate interrupt behavior
                if action['type'] in ['read_file', 'run_command']:
                    print(f"     🚨 INTERRUPT: Would stop streaming here for {action['type']}")
                    break
        else:
            print(f"  → No complete actions yet")
    
    print(f"\nTotal actions found: {len(all_actions)}")


def test_partial_actions():
    """Test how parser handles partial action tags"""
    print("\n\nTEST 3: Partial action tags")
    print("="*60)
    
    parser = StreamingXMLParser()
    
    # First chunk has incomplete action
    chunk1 = "Here's a partial action: <action type=\"file\" filePath=\"test.py\">"
    chunk2 = "def hello():\n    print('world')"
    chunk3 = "</action> And now it's complete!"
    
    print("Chunk 1:", repr(chunk1))
    actions1 = list(parser.process_chunk(chunk1))
    print(f"  Actions found: {len(actions1)}")
    
    print("\nChunk 2:", repr(chunk2))
    actions2 = list(parser.process_chunk(chunk2))
    print(f"  Actions found: {len(actions2)}")
    
    print("\nChunk 3:", repr(chunk3))
    actions3 = list(parser.process_chunk(chunk3))
    print(f"  Actions found: {len(actions3)}")
    if actions3:
        print(f"  Action type: {actions3[0]['type']}")
        print(f"  Content: {actions3[0]['content']}")


def test_early_detection_scenario():
    """Test the early detection scenario for update_file"""
    print("\n\nTEST 4: Early detection for update_file")
    print("="*60)
    
    # Simulate what happens in the coder
    accumulated = ""
    chunks = [
        "Let me update the file:\n\n",
        "<action type=\"update_file\"",
        " path=\"src/main.py\">",
        "\n# Updated content\n",
        "def new_function():\n    pass\n",
        "</action>"
    ]
    
    update_file_detected = False
    for i, chunk in enumerate(chunks):
        accumulated += chunk
        print(f"\nChunk {i+1}: {repr(chunk)}")
        print(f"Accumulated length: {len(accumulated)}")
        
        # Early detection logic from coder
        if not update_file_detected and '<action type="update_file"' in accumulated:
            update_file_detected = True
            print("  🚨 EARLY DETECTION: Found update_file action!")
            
            # Check for path
            import re
            path_match = re.search(r'path="([^"]*)"', accumulated)
            if path_match:
                print(f"  📍 Found path: {path_match.group(1)}")
                print("  → Would trigger read_file interrupt here!")
            else:
                print("  ⏳ Path not found yet, waiting...")


if __name__ == "__main__":
    test_multiple_actions()
    test_streaming_interrupts()
    test_partial_actions()
    test_early_detection_scenario()