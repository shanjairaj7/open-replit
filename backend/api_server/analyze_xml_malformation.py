#!/usr/bin/env python3
"""
Analyze the XML malformation in Message 60 that caused the file upload failures
"""

import sys
import re
from typing import List, Tuple

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


def get_message_60():
    """Get Message 60 content"""
    storage = AzureBlobStorage()
    conversation = storage.load_conversation_history("horizon-543-56f69")
    return conversation[59].get('content', '')


def find_unbalanced_tags(content: str):
    """Find specific unbalanced XML tags"""
    print("🔍 Analyzing XML tag balance...")
    
    # Find all opening and closing action tags with their positions
    opening_pattern = r'<action\s+[^>]*>'
    closing_pattern = r'</action>'
    
    openings = [(m.start(), m.group()) for m in re.finditer(opening_pattern, content)]
    closings = [(m.start(), m.group()) for m in re.finditer(closing_pattern, content)]
    
    print(f"📊 Found {len(openings)} opening tags and {len(closings)} closing tags")
    
    # Try to match opening and closing tags
    unmatched_openings = []
    matched_pairs = 0
    
    opening_stack = list(openings)  # Copy for manipulation
    
    for closing_pos, closing_tag in closings:
        # Find the most recent unmatched opening tag before this closing
        matched = False
        for i in range(len(opening_stack) - 1, -1, -1):
            opening_pos, opening_tag = opening_stack[i]
            if opening_pos < closing_pos:
                # This opening matches this closing
                opening_stack.pop(i)
                matched_pairs += 1
                matched = True
                break
        
        if not matched:
            print(f"⚠️  Unmatched closing tag at position {closing_pos}")
    
    # Remaining items in opening_stack are unmatched
    unmatched_openings = opening_stack
    
    print(f"📊 Matching results:")
    print(f"   Matched pairs: {matched_pairs}")
    print(f"   Unmatched openings: {len(unmatched_openings)}")
    
    return unmatched_openings


def analyze_problematic_sections(content: str, unmatched_openings: List[Tuple[int, str]]):
    """Analyze the sections around unmatched opening tags"""
    print(f"\n🔍 Analyzing {len(unmatched_openings)} problematic sections...")
    
    for i, (pos, tag) in enumerate(unmatched_openings[:5]):  # Show first 5
        print(f"\n❌ Unmatched opening #{i+1} at position {pos}:")
        print(f"   Tag: {tag}")
        
        # Show context around this position
        context_start = max(0, pos - 100)
        context_end = min(len(content), pos + 300)
        context = content[context_start:context_end]
        
        # Highlight the problematic tag
        highlight_pos = pos - context_start
        context_with_marker = (
            context[:highlight_pos] + 
            ">>>" + context[highlight_pos:highlight_pos + len(tag)] + "<<<" +
            context[highlight_pos + len(tag):]
        )
        
        print(f"   Context:")
        for line_num, line in enumerate(context_with_marker.split('\n')[:8]):  # Show max 8 lines
            print(f"     {line}")
        
        if len(context_with_marker.split('\n')) > 8:
            print("     ...")


def find_missing_closing_tags(content: str):
    """Find specific action types that are missing closing tags"""
    print(f"\n🔍 Finding action types with missing closings...")
    
    # Extract all action types from opening tags
    action_type_pattern = r'<action\s+type=["\']([^"\']+)["\']'
    action_types = re.findall(action_type_pattern, content)
    
    # Count by action type
    type_counts = {}
    for action_type in action_types:
        type_counts[action_type] = type_counts.get(action_type, 0) + 1
    
    # Count closing tags (all should be the same)
    closing_count = len(re.findall(r'</action>', content))
    
    print(f"📊 Action types and counts:")
    total_openings = 0
    for action_type, count in sorted(type_counts.items()):
        print(f"   {action_type}: {count} openings")
        total_openings += count
    
    print(f"   Total openings: {total_openings}")
    print(f"   Total closings: {closing_count}")
    print(f"   Missing closings: {total_openings - closing_count}")
    
    return type_counts, closing_count


def check_nested_or_overlapping_actions(content: str):
    """Check for nested or overlapping action tags that could confuse parser"""
    print(f"\n🔍 Checking for nested/overlapping actions...")
    
    # Find all action tag positions
    all_tags = []
    
    # Opening tags
    for match in re.finditer(r'<action\s+[^>]*>', content):
        all_tags.append((match.start(), match.end(), 'open', match.group()))
    
    # Closing tags  
    for match in re.finditer(r'</action>', content):
        all_tags.append((match.start(), match.end(), 'close', match.group()))
    
    # Sort by position
    all_tags.sort(key=lambda x: x[0])
    
    # Check for proper nesting
    open_stack = []
    issues = []
    
    for start_pos, end_pos, tag_type, tag_text in all_tags:
        if tag_type == 'open':
            open_stack.append((start_pos, tag_text))
        elif tag_type == 'close':
            if open_stack:
                open_stack.pop()
            else:
                issues.append(f"Closing tag without opening at position {start_pos}")
    
    if open_stack:
        issues.append(f"{len(open_stack)} unclosed opening tags")
    
    print(f"📊 Nesting analysis:")
    if issues:
        for issue in issues:
            print(f"   ⚠️  {issue}")
    else:
        print("   ✅ No nesting issues found")
    
    return len(issues) == 0


if __name__ == "__main__":
    print("🔍 Analyzing XML Malformation in Message 60")
    print("=" * 50)
    
    content = get_message_60()
    print(f"📝 Message 60 content: {len(content)} characters")
    
    # Find unbalanced tags
    unmatched_openings = find_unbalanced_tags(content)
    
    # Analyze problematic sections
    if unmatched_openings:
        analyze_problematic_sections(content, unmatched_openings)
    
    # Find missing closing tags by type
    type_counts, closing_count = find_missing_closing_tags(content)
    
    # Check nesting issues
    nesting_ok = check_nested_or_overlapping_actions(content)
    
    print(f"\n🎯 Root Cause Analysis:")
    print(f"   The XML parser failed because Message 60 has {len(unmatched_openings)} unclosed action tags")
    print(f"   This caused the StreamingXMLParser to get confused and not process all file actions")
    print(f"   Result: File creation actions were parsed but never executed")
    print(f"   The bug in _process_file_action() then hid this failure by always printing success")