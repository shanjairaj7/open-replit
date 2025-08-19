#!/usr/bin/env python3
"""
Test assistant message buffering logic for action tag detection.
"""

import sys
import os

# Test the buffering logic with simulated streaming chunks

def test_assistant_buffering():
    """Test assistant message buffering to detect action tags"""
    
    print("🧪 Testing assistant message buffering logic")
    
    # Test case 1: Normal assistant message without action tags
    print("\n📝 Test 1: Normal assistant message (should be streamed after buffer delay)")
    
    assistant_buffer = ""
    assistant_chunks_processed = 0
    assistant_buffer_delay = 5  # Smaller for testing
    has_action_tags = False
    buffered_content_streamed = False
    streamed_messages = []
    
    def mock_emit_stream(event_type, content, metadata=None):
        streamed_messages.append({"type": event_type, "content": content})
        print(f"  📤 STREAMED: {event_type} - '{content}'")
    
    # Simulate streaming chunks of a normal message
    chunks = ["I'll help you ", "create a ", "simple ", "calculator ", "application."]
    
    for i, chunk in enumerate(chunks):
        assistant_buffer += chunk
        assistant_chunks_processed += 1
        
        # Check for action tags
        if '<action' in assistant_buffer and not has_action_tags:
            has_action_tags = True
            print(f"  🚫 Action tag detected in assistant message")
        
        # Buffer logic
        if not has_action_tags:
            if assistant_chunks_processed == assistant_buffer_delay and not buffered_content_streamed:
                print(f"  ✅ Buffer delay reached ({assistant_buffer_delay} chunks) - flushing buffered content")
                mock_emit_stream("assistant_message", assistant_buffer)
                buffered_content_streamed = True
            elif assistant_chunks_processed > assistant_buffer_delay:
                print(f"  📤 Streaming current chunk: '{chunk}'")
                mock_emit_stream("assistant_message", chunk)
            else:
                print(f"  🔄 Buffering chunk {assistant_chunks_processed}/{assistant_buffer_delay}: '{chunk}'")
    
    # Handle remaining content
    if assistant_buffer and not has_action_tags and not buffered_content_streamed:
        print(f"  💫 Flushing remaining buffered content")
        mock_emit_stream("assistant_message", assistant_buffer)
    
    print(f"  ✅ Test 1 complete: {len(streamed_messages)} messages streamed")
    
    # Test case 2: Assistant message with action tags (should not be streamed)
    print("\n📝 Test 2: Assistant message with action tags (should not be streamed)")
    
    assistant_buffer = ""
    assistant_chunks_processed = 0
    has_action_tags = False
    buffered_content_streamed = False
    streamed_messages = []
    
    # Simulate streaming chunks of message with action tags
    chunks = ["I'll create ", "a file for ", "you. <action ", 'type="file"', ">content</action>"]
    
    for i, chunk in enumerate(chunks):
        assistant_buffer += chunk
        assistant_chunks_processed += 1
        
        # Check for action tags
        if '<action' in assistant_buffer and not has_action_tags:
            has_action_tags = True
            print(f"  🚫 Action tag detected in chunk {assistant_chunks_processed} - assistant content will not be streamed")
        
        # Buffer logic
        if not has_action_tags:
            if assistant_chunks_processed == assistant_buffer_delay and not buffered_content_streamed:
                print(f"  ✅ Buffer delay reached - flushing buffered content")
                mock_emit_stream("assistant_message", assistant_buffer)
                buffered_content_streamed = True
            elif assistant_chunks_processed > assistant_buffer_delay:
                mock_emit_stream("assistant_message", chunk)
            else:
                print(f"  🔄 Buffering chunk {assistant_chunks_processed}/{assistant_buffer_delay}: '{chunk}'")
        else:
            print(f"  🚫 Discarding chunk {assistant_chunks_processed}: '{chunk}' (contains action tags)")
    
    # Handle remaining content
    if has_action_tags:
        print(f"  🚫 Discarded {len(assistant_buffer)} chars of assistant content containing action tags")
    elif assistant_buffer and not buffered_content_streamed:
        mock_emit_stream("assistant_message", assistant_buffer)
    
    print(f"  ✅ Test 2 complete: {len(streamed_messages)} messages streamed (should be 0)")
    
    # Test case 3: Action tags detected early (within buffer window)
    print("\n📝 Test 3: Action tags detected in 2nd chunk (should not stream anything)")
    
    assistant_buffer = ""
    assistant_chunks_processed = 0
    has_action_tags = False
    buffered_content_streamed = False
    streamed_messages = []
    
    # Simulate action tag appearing early
    chunks = ["Let me ", "<action type=", '"file">content', '</action>', " for you."]
    
    for i, chunk in enumerate(chunks):
        assistant_buffer += chunk
        assistant_chunks_processed += 1
        
        # Check for action tags
        if '<action' in assistant_buffer and not has_action_tags:
            has_action_tags = True
            print(f"  🚫 Action tag detected in chunk {assistant_chunks_processed} - early detection working")
        
        # Buffer logic (same as above)
        if not has_action_tags:
            if assistant_chunks_processed == assistant_buffer_delay and not buffered_content_streamed:
                mock_emit_stream("assistant_message", assistant_buffer)
                buffered_content_streamed = True
            elif assistant_chunks_processed > assistant_buffer_delay:
                mock_emit_stream("assistant_message", chunk)
            else:
                print(f"  🔄 Buffering chunk {assistant_chunks_processed}/{assistant_buffer_delay}: '{chunk}'")
        else:
            print(f"  🚫 Discarding chunk {assistant_chunks_processed}: '{chunk}' (contains action tags)")
    
    print(f"  ✅ Test 3 complete: {len(streamed_messages)} messages streamed (should be 0)")
    
    print(f"\n🎉 All assistant buffering tests completed!")

if __name__ == "__main__":
    test_assistant_buffering()