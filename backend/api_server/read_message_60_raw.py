#!/usr/bin/env python3
"""
Read the actual raw Message 60 content to verify the XML structure
"""

import sys
import json

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


def extract_and_save_message_60():
    """Extract Message 60 and save it for manual inspection"""
    storage = AzureBlobStorage()
    conversation = storage.load_conversation_history("horizon-543-56f69")
    
    if len(conversation) < 60:
        print("❌ Message 60 not found")
        return
    
    message_60 = conversation[59]  # 0-indexed
    content = message_60.get('content', '')
    
    # Save the raw content to a file for inspection
    output_file = '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/message_60_raw_content.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("MESSAGE 60 RAW CONTENT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Role: {message_60.get('role')}\n")
        f.write(f"Content length: {len(content)} characters\n\n")
        f.write("CONTENT:\n")
        f.write("-" * 20 + "\n")
        f.write(content)
    
    print(f"📄 Message 60 content saved to: {output_file}")
    print(f"📊 Content length: {len(content)} characters")
    
    # Show first 2000 characters for immediate inspection
    print(f"\n📋 First 2000 characters:")
    print("-" * 50)
    print(content[:2000])
    
    if len(content) > 2000:
        print("\n📋 Last 1000 characters:")
        print("-" * 50)
        print(content[-1000:])
    
    return output_file


if __name__ == "__main__":
    extract_and_save_message_60()