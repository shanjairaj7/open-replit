#!/usr/bin/env python3
"""
Investigate the StreamingXMLParser to understand how bulk file actions 
are processed and where the failure might have occurred
"""

import sys
import json
import re
from typing import List, Dict, Any

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


def load_horizon_conversation():
    """Load the actual conversation from horizon-543-56f69"""
    storage = AzureBlobStorage()
    project_id = "horizon-543-56f69"
    
    conversation = storage.load_conversation_history(project_id)
    return conversation


def extract_message_60_content():
    """Extract Message 60 content to analyze the bulk actions"""
    conversation = load_horizon_conversation()
    
    if len(conversation) < 60:
        print("❌ Message 60 not found")
        return None
    
    message_60 = conversation[59]  # 0-indexed
    content = message_60.get('content', '')
    
    print(f"📝 Message 60 details:")
    print(f"   Role: {message_60.get('role')}")
    print(f"   Content length: {len(content)} characters")
    
    return content


def analyze_action_structure(content: str):
    """Analyze the structure of actions in the content"""
    print("\n🔍 Analyzing action structure...")
    
    # Find all action tags
    action_pattern = r'<action\s+type=["\']([^"\']+)["\'][^>]*>(.*?)</action>'
    actions = re.findall(action_pattern, content, re.DOTALL | re.IGNORECASE)
    
    print(f"📊 Found {len(actions)} actions in Message 60:")
    
    action_analysis = []
    for i, (action_type, action_content) in enumerate(actions):
        # Extract filePath if present
        filepath_match = re.search(r'filePath=["\'](.*?)["\']', content[content.find(action_content)-100:content.find(action_content)+100])
        file_path = filepath_match.group(1) if filepath_match else "Unknown"
        
        analysis = {
            "index": i + 1,
            "type": action_type,
            "file_path": file_path,
            "content_length": len(action_content),
            "content_preview": action_content[:100].replace('\n', ' ').strip() + ("..." if len(action_content) > 100 else "")
        }
        action_analysis.append(analysis)
        
        print(f"   {i+1}. {action_type}: {file_path} ({len(action_content)} chars)")
    
    return action_analysis


def check_for_malformed_actions(content: str):
    """Check for malformed or incomplete actions"""
    print("\n🔍 Checking for malformed actions...")
    
    # Check for unclosed action tags
    opening_actions = re.findall(r'<action[^>]*>', content)
    closing_actions = re.findall(r'</action>', content)
    
    print(f"📊 Action tag balance:")
    print(f"   Opening tags: {len(opening_actions)}")
    print(f"   Closing tags: {len(closing_actions)}")
    
    if len(opening_actions) != len(closing_actions):
        print("⚠️  Unbalanced action tags detected!")
        return False
    
    # Check for nested actions (not allowed)
    nested_pattern = r'<action[^>]*>.*?<action[^>]*>.*?</action>.*?</action>'
    nested_matches = re.findall(nested_pattern, content, re.DOTALL)
    
    if nested_matches:
        print(f"⚠️  Found {len(nested_matches)} potentially nested actions!")
        for match in nested_matches[:2]:  # Show first 2
            print(f"     {match[:200]}...")
        return False
    
    # Check for actions with missing filePath
    actions_without_filepath = []
    action_pattern = r'<action\s+type=["\']write_file["\'][^>]*>(.*?)</action>'
    for match in re.finditer(action_pattern, content, re.DOTALL | re.IGNORECASE):
        action_tag = match.group(0)
        if 'filePath=' not in action_tag:
            actions_without_filepath.append(action_tag[:200] + "...")
    
    if actions_without_filepath:
        print(f"⚠️  Found {len(actions_without_filepath)} write_file actions without filePath!")
        for action in actions_without_filepath[:2]:
            print(f"     {action}")
        return False
    
    print("✅ No malformed actions detected")
    return True


def simulate_streaming_parser():
    """Simulate how the StreamingXMLParser would process Message 60"""
    print("\n🧪 Simulating StreamingXMLParser processing...")
    
    content = extract_message_60_content()
    if not content:
        return
    
    # Try to import the actual parser
    try:
        sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
        from diff_parser import StreamingXMLParser
        
        parser = StreamingXMLParser()
        
        # Process the content in chunks like streaming would
        chunk_size = 1000
        all_actions = []
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            actions = list(parser.process_chunk(chunk))
            all_actions.extend(actions)
            
            if actions:
                print(f"   Chunk {i//chunk_size + 1}: Found {len(actions)} actions")
        
        # Final flush
        final_actions = list(parser.process_chunk(""))
        all_actions.extend(final_actions)
        
        print(f"📊 Streaming parser results:")
        print(f"   Total actions found: {len(all_actions)}")
        
        # Analyze action types
        action_types = {}
        file_actions = []
        
        for action in all_actions:
            action_type = action.get('type', 'unknown')
            action_types[action_type] = action_types.get(action_type, 0) + 1
            
            if action_type == 'write_file':
                file_actions.append(action)
        
        print(f"   Action breakdown: {action_types}")
        
        # Check if any file actions have missing data
        problematic_actions = []
        for action in file_actions:
            if not action.get('filePath'):
                problematic_actions.append("Missing filePath")
            if not action.get('content'):
                problematic_actions.append("Missing content")
        
        if problematic_actions:
            print(f"⚠️  Found {len(problematic_actions)} problematic file actions")
            return False
        else:
            print("✅ All file actions have required data")
            return True
            
    except ImportError as e:
        print(f"❌ Could not import StreamingXMLParser: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in parser simulation: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_memory_or_resource_constraints():
    """Check if the bulk action processing might have hit memory/resource limits"""
    print("\n🔍 Checking for resource constraints...")
    
    content = extract_message_60_content()
    if not content:
        return
    
    # Calculate total memory usage if all actions were processed at once
    action_pattern = r'<action\s+type=["\']write_file["\'][^>]*>(.*?)</action>'
    actions = re.findall(action_pattern, content, re.DOTALL | re.IGNORECASE)
    
    total_content_size = sum(len(action_content) for action_content in actions)
    message_size = len(content)
    
    print(f"📊 Resource usage analysis:")
    print(f"   Message 60 size: {message_size:,} characters ({message_size/1024/1024:.1f} MB)")
    print(f"   Total file content: {total_content_size:,} characters ({total_content_size/1024/1024:.1f} MB)")
    print(f"   Number of files: {len(actions)}")
    print(f"   Average file size: {total_content_size//len(actions) if actions else 0:,} characters")
    
    # Check if any individual file is unusually large
    large_files = []
    for i, action_content in enumerate(actions):
        if len(action_content) > 50000:  # > 50KB
            large_files.append((i+1, len(action_content)))
    
    if large_files:
        print(f"📋 Large files found:")
        for file_num, size in large_files:
            print(f"   File {file_num}: {size:,} characters ({size/1024:.1f} KB)")
    
    # Memory concerns
    if total_content_size > 1024 * 1024:  # > 1MB
        print("⚠️  Large total content size might cause memory issues")
        return False
    
    if len(actions) > 20:
        print("⚠️  Large number of concurrent actions might cause resource issues")
        return False
    
    print("✅ Resource usage within reasonable limits")
    return True


if __name__ == "__main__":
    print("🔍 Investigating StreamingXMLParser and Bulk Action Processing")
    print("=" * 70)
    
    # Extract Message 60 content
    content = extract_message_60_content()
    
    if content:
        # Run all analyses
        action_analysis = analyze_action_structure(content)
        malformed_ok = check_for_malformed_actions(content)
        parser_ok = simulate_streaming_parser()
        resource_ok = check_memory_or_resource_constraints()
        
        print("\n📊 Investigation Summary:")
        print(f"   Action structure: {'✅' if action_analysis else '❌'}")
        print(f"   Well-formed XML: {'✅' if malformed_ok else '❌'}")
        print(f"   Parser simulation: {'✅' if parser_ok else '❌'}")
        print(f"   Resource usage: {'✅' if resource_ok else '❌'}")
        
        if all([action_analysis, malformed_ok, parser_ok, resource_ok]):
            print("\n🤔 The bulk actions were well-formed and should have worked.")
            print("   This suggests the failure was in the execution phase, not parsing.")
            print("   Possible causes:")
            print("   1. Network timeout during bulk Azure uploads")
            print("   2. Azure API rate limiting")
            print("   3. Temporary Azure service degradation") 
            print("   4. Memory pressure during bulk processing")
            print("   5. Exception handling swallowing the real error")
        else:
            print("\n🚨 Found structural issues that could explain the failure")
    else:
        print("❌ Could not load Message 60 content for analysis")