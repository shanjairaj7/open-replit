#!/usr/bin/env python3
"""
Detailed search for update_file content in assistant messages
"""

import json
from cloud_storage import AzureBlobStorage

def detailed_search():
    """Search for any update_file content in assistant messages"""
    
    project_id = "emergency-update-main-todo-component-0829-114405"
    file_name = "conversation_history_streaming.json"
    
    try:
        storage = AzureBlobStorage()
        content = storage.download_file(project_id, file_name)
        conversation_data = json.loads(content)
        streaming_chunks = conversation_data.get('conversation_streaming_chunks', [])
        
        print(f"🔍 Detailed search through {len(streaming_chunks)} chunks...")
        print()
        
        # Check every assistant message for any code-like content
        for i, chunk in enumerate(streaming_chunks):
            if chunk.get('type') == 'assistant_message':
                message = chunk.get('data', {}).get('content', '')
                
                # Check for various patterns that might indicate leaked code
                code_indicators = [
                    '<action',           # XML action tags
                    'action type=',      # Action type declarations
                    'filePath=',         # File path attributes
                    'import ',           # Import statements
                    'export default',    # Export statements
                    'function ',         # Function declarations
                    'const ',            # Const declarations
                    'className="',       # React className
                    'onClick=',          # React onClick
                    '{',                 # Code blocks
                    '}',                 # Code blocks
                    '*** Update File:',  # V4A header
                    '@@',                # V4A context markers
                    '+ ',                # V4A additions (with space)
                    '- ',                # V4A deletions (with space)
                ]
                
                found_indicators = []
                for indicator in code_indicators:
                    if indicator in message:
                        found_indicators.append(indicator)
                
                if found_indicators:
                    print(f"🚨 CHUNK #{i+1}: Assistant message contains code-like content")
                    print(f"   Timestamp: {chunk.get('timestamp')}")
                    print(f"   Indicators found: {found_indicators}")
                    print(f"   Message length: {len(message)} chars")
                    print(f"   Message: '{message}'")
                    print("-" * 60)
        
        print("✅ Search complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    detailed_search()