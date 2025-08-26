#!/usr/bin/env python3
"""
Actually verify the XML structure properly by matching opening and closing tags correctly
"""

import re

def verify_xml_structure():
    """Properly verify XML structure"""
    with open('/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/message_60_raw_content.txt', 'r') as f:
        content = f.read()
    
    # Extract just the XML content (skip the header)
    xml_start = content.find('<action')
    if xml_start == -1:
        print("No actions found")
        return
    
    xml_content = content[xml_start:]
    
    print("🔍 Verifying XML structure properly...")
    
    # Count self-closing tags (these don't need closing tags)
    self_closing = re.findall(r'<action[^>]+/>', xml_content)
    print(f"📊 Self-closing action tags: {len(self_closing)}")
    
    # Count regular opening tags (these need closing tags)
    opening_tags = re.findall(r'<action[^>]+>', xml_content)
    # Remove self-closing from opening count
    regular_openings = [tag for tag in opening_tags if not tag.endswith('/>')]
    print(f"📊 Regular opening tags: {len(regular_openings)}")
    
    # Count closing tags
    closing_tags = re.findall(r'</action>', xml_content)
    print(f"📊 Closing tags: {len(closing_tags)}")
    
    # Check balance
    if len(regular_openings) == len(closing_tags):
        print("✅ XML is properly balanced!")
        return True
    else:
        print(f"❌ XML is unbalanced: {len(regular_openings)} openings vs {len(closing_tags)} closings")
        
        # Show the unmatched ones
        print(f"\nFirst few regular opening tags:")
        for i, tag in enumerate(regular_openings[:5]):
            print(f"  {i+1}. {tag}")
            
        return False

def find_write_file_actions():
    """Find all write_file actions and verify they're complete"""
    with open('/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/message_60_raw_content.txt', 'r') as f:
        content = f.read()
    
    print(f"\n🔍 Finding write_file actions...")
    
    # Find write_file actions with their content
    pattern = r'<action type="write_file" filePath="([^"]+)">(.*?)</action>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"📊 Found {len(matches)} complete write_file actions:")
    
    for i, (file_path, file_content) in enumerate(matches):
        content_length = len(file_content.strip())
        print(f"  {i+1}. {file_path} ({content_length} chars)")
        
        # Check if content looks valid
        if content_length == 0:
            print(f"      ⚠️  Empty content!")
        elif content_length < 100:
            print(f"      ⚠️  Very short content!")
        else:
            print(f"      ✅ Good content length")
    
    return matches

def analyze_missing_files():
    """Check which write_file actions might have failed"""
    write_files = find_write_file_actions()
    
    missing_files = [
        "frontend/src/pages/DealsPage.tsx",
        "frontend/src/pages/AuditLogPage.tsx", 
        "frontend/src/pages/ContactsPage.tsx",
        "frontend/src/components/Sidebar.tsx",
        "frontend/src/components/PageContainer.tsx",
        "frontend/src/api/crm_api.ts",
        "backend/routes/crm.py",
        "backend/routes/crm_models.py",
        "backend/routes/crm_schemas.py",
        "backend/test_crm_api.py"
    ]
    
    found_in_xml = {file_path for file_path, _ in write_files}
    
    print(f"\n🎯 Checking missing files against XML content:")
    
    for missing_file in missing_files:
        if missing_file in found_in_xml:
            print(f"  ✅ {missing_file} - FOUND in XML")
        else:
            print(f"  ❌ {missing_file} - NOT found in XML")
            
    print(f"\n📊 Summary:")
    print(f"  Files in XML: {len(found_in_xml)}")
    print(f"  Missing files that should exist: {len(missing_files)}")
    print(f"  Missing files found in XML: {len(found_in_xml.intersection(missing_files))}")

if __name__ == "__main__":
    print("🔍 Properly Verifying Message 60 XML Structure")
    print("=" * 50)
    
    xml_valid = verify_xml_structure()
    write_file_matches = find_write_file_actions()
    analyze_missing_files()
    
    if xml_valid and write_file_matches:
        print(f"\n🤔 If XML is valid and write_file actions exist, the failure must be elsewhere:")
        print(f"   1. Parser issue extracting the actions correctly")
        print(f"   2. File processing bug (which we already found)")
        print(f"   3. Azure connection issue during processing")
        print(f"   4. Exception in file processing that was caught/hidden")