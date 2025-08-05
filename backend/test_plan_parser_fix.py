#!/usr/bin/env python3
"""
Test script to verify the regex-based plan parser handles malformed XML correctly.
Tests with actual problematic XML from the Airbnb project that had malformed file tags.
"""

import re
import xml.etree.ElementTree as ET

# The actual problematic XML from the Airbnb project with malformed file tag
PROBLEMATIC_XML = """<plan>
  <overview>Build a simplified Airbnb clone with property listings, search, and booking functionality</overview>
  
  <steps>
    <step id="1" name="Backend Models and Database" priority="high" dependencies="">
      <description>Set up database models for properties, users, and bookings</description>
      <files>
        <file path="backend/models/__init__.py">Initialize models package</file>
        <file path="backend/models/base.py">Base model with common fields</file>
        <file path="backend/models/user.py">User model with authentication fields</file>
        <file path="backend/models/property.py">Property listing model</file>
        <file path="backend/models/booking.py">Booking model with dates and status</file>
        <file path="backend/database.py">Database connection and session management</file>
      </files>
    </step>
    
    <step id="2" name="Backend API Core" priority="high" dependencies="1">
      <description>Create FastAPI application structure and core endpoints</description>
      <files>
        <file path="backend/main.py">FastAPI app initialization and configuration</file>
        <file path="backend/config.py">Application configuration and settings</file>
        <file path="backend/dependencies.py">Shared dependencies for endpoints</file>
        <file path="backend/schemas/user.py">Pydantic schemas for user data</file>
        <file path="backend/schemas/property.py">Pydantic schemas for property data</file>
        <file path="backend/schemas/booking.py">Pydantic schemas for booking data</file>
      </files>
    </step>
    
    <step id="3" name="Frontend Services and API" priority="high" dependencies="2">
      <description>Create API client services for frontend</description>
      <files>
        <file path="frontend/src/services/api.ts">Base API configuration with axios</file>
        <file path="frontend/src/services/authService.ts">Authentication API calls</file>
        <frontend/src/services/propertyService.ts>Property listing and search API</file>
        <file path="frontend/src/services/bookingService.ts">Booking management API</file>
        <file path="frontend/src/types/index.ts">TypeScript interfaces for all entities</file>
      </files>
    </step>
  </steps>
  
  <file_tree>
backend/
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── property.py
│   └── booking.py
├── schemas/
│   ├── user.py
│   ├── property.py
│   └── booking.py
├── routes/
│   ├── auth.py
│   ├── properties.py
│   └── bookings.py
├── main.py
├── config.py
├── database.py
└── dependencies.py
frontend/
├── src/
│   ├── services/
│   │   ├── api.ts
│   │   ├── authService.ts
│   │   ├── propertyService.ts
│   │   └── bookingService.ts
│   ├── types/
│   │   └── index.ts
│   ├── components/
│   │   ├── PropertyCard.tsx
│   │   ├── SearchBar.tsx
│   │   ├── BookingForm.tsx
│   │   └── Layout.tsx
│   └── pages/
│       ├── Home.tsx
│       ├── PropertyDetail.tsx
│       └── MyBookings.tsx
  </file_tree>
</plan>"""


def test_xml_parser_fails():
    """Test that the current XML parser fails on malformed XML"""
    print("=== Testing XML Parser (Expected to Fail) ===\n")
    
    try:
        # Extract plan XML from response
        plan_match = re.search(r'<plan>(.*?)</plan>', PROBLEMATIC_XML, re.DOTALL)
        if not plan_match:
            print("❌ No <plan> tags found")
            return
        
        plan_content = f"<plan>{plan_match.group(1)}</plan>"
        
        # Try the current approach with escaping
        import html
        plan_content = html.escape(plan_content, quote=False).replace("&lt;", "<").replace("&gt;", ">")
        
        # This should fail on the malformed tag
        root = ET.fromstring(plan_content)
        
        print("✅ XML parsing succeeded (unexpected!)")
        
    except Exception as e:
        print(f"❌ XML parsing failed as expected: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Show the problematic line
        lines = plan_content.split('\n')
        for i, line in enumerate(lines):
            if 'frontend/src/services/propertyService.ts' in line:
                print(f"\n   Problematic line {i+1}: {line.strip()}")
                break


def parse_plan_xml_regex(plan_xml: str) -> list:
    """Parse XML plan using regex to handle malformed XML gracefully"""
    print("\n=== Testing Regex-Based Parser ===\n")
    
    try:
        # Extract plan XML from response
        plan_match = re.search(r'<plan>(.*?)</plan>', plan_xml, re.DOTALL)
        if not plan_match:
            print("❌ No <plan> tags found in response")
            return None
        
        plan_content = plan_match.group(1)
        
        # Extract overview
        overview_match = re.search(r'<overview>(.*?)</overview>', plan_content, re.DOTALL)
        overview = overview_match.group(1).strip() if overview_match else ""
        print(f"📋 Overview: {overview[:100]}...")
        
        # Extract steps using regex
        steps = []
        steps_match = re.search(r'<steps>(.*?)</steps>', plan_content, re.DOTALL)
        
        if not steps_match:
            print("❌ No <steps> element found in plan")
            return None
        
        steps_content = steps_match.group(1)
        
        # Find all step elements
        step_pattern = r'<step\s+id="(\d+)"\s+name="([^"]+)"\s+priority="([^"]+)"\s+dependencies="([^"]*)">(.*?)</step>'
        
        for match in re.finditer(step_pattern, steps_content, re.DOTALL):
            step_id = match.group(1)
            step_name = match.group(2)
            priority = match.group(3)
            dependencies = match.group(4)
            step_content = match.group(5)
            
            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', step_content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            
            # Extract files
            files = []
            files_match = re.search(r'<files>(.*?)</files>', step_content, re.DOTALL)
            
            if files_match:
                files_content = files_match.group(1)
                
                # Handle both correct and malformed file tags
                # Pattern 1: Correct format <file path="...">...</file>
                file_pattern1 = r'<file\s+path="([^"]+)">([^<]*)</file>'
                
                # Pattern 2: Malformed format <path/to/file.ext>description</file>
                file_pattern2 = r'<([^/>\s]+/[^>]+)>([^<]*)</file>'
                
                # First, find all correctly formatted files
                for file_match in re.finditer(file_pattern1, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    files.append({
                        'path': path,
                        'description': desc
                    })
                
                # Then, find malformed files
                for file_match in re.finditer(file_pattern2, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    
                    # Skip if this was already matched by the correct pattern
                    if not any(f['path'] == path for f in files):
                        files.append({
                            'path': path,
                            'description': desc,
                            'malformed': True  # Flag as malformed
                        })
            
            step_data = {
                'id': step_id,
                'name': step_name,
                'priority': priority,
                'dependencies': dependencies.split(',') if dependencies else [],
                'description': description,
                'files': files
            }
            
            steps.append(step_data)
            
        return steps
        
    except Exception as e:
        print(f"❌ Error parsing plan with regex: {e}")
        return None


def test_regex_parser():
    """Test the regex-based parser with problematic XML"""
    steps = parse_plan_xml_regex(PROBLEMATIC_XML)
    
    if not steps:
        print("❌ Failed to parse plan")
        return False
    
    print(f"\n✅ Successfully parsed {len(steps)} steps\n")
    
    # Display parsed results
    for i, step in enumerate(steps, 1):
        print(f"Step {i}: {step['name']}")
        print(f"  ID: {step['id']}")
        print(f"  Priority: {step['priority']}")
        print(f"  Dependencies: {step['dependencies']}")
        print(f"  Description: {step['description'][:100]}...")
        print(f"  Files ({len(step['files'])}):")
        
        for file_info in step['files']:
            malformed_marker = " [MALFORMED TAG]" if file_info.get('malformed') else ""
            print(f"    - {file_info['path']}: {file_info['description']}{malformed_marker}")
        print()
    
    # Verify the malformed file was captured
    malformed_found = False
    for step in steps:
        for file_info in step['files']:
            if 'propertyService.ts' in file_info['path'] and file_info.get('malformed'):
                malformed_found = True
                print(f"✅ Successfully captured malformed file tag: {file_info['path']}")
                break
    
    if not malformed_found:
        print("❌ Failed to detect the malformed file tag")
        return False
    
    return True


def create_improved_parser():
    """Create an improved version of _parse_plan_xml that handles malformed XML"""
    
    code = '''def _parse_plan_xml(self, plan_xml: str) -> list:
    """Parse XML plan into structured chunks using regex to handle malformed XML"""
    
    try:
        # Extract plan XML from response
        plan_match = re.search(r'<plan>(.*?)</plan>', plan_xml, re.DOTALL)
        if not plan_match:
            print("❌ No <plan> tags found in response")
            print("Full response for debugging:")
            print(plan_xml[:500] + "..." if len(plan_xml) > 500 else plan_xml)
            return None
        
        plan_content = plan_match.group(1)
        
        # Debug: Show extracted XML
        print("\\n📄 Extracted XML plan:")
        print("-" * 60)
        print(f"<plan>{plan_content[:1000]}...</plan>" if len(plan_content) > 1000 else f"<plan>{plan_content}</plan>")
        print("-" * 60)
        
        # Extract steps using regex (more robust than XML parsing)
        steps = []
        steps_match = re.search(r'<steps>(.*?)</steps>', plan_content, re.DOTALL)
        
        if not steps_match:
            print("❌ No <steps> element found in plan")
            return None
        
        steps_content = steps_match.group(1)
        
        # Find all step elements
        step_pattern = r'<step\\s+id="(\\d+)"\\s+name="([^"]+)"\\s+priority="([^"]+)"\\s+dependencies="([^"]*)">(.*?)</step>'
        
        for match in re.finditer(step_pattern, steps_content, re.DOTALL):
            step_id = match.group(1)
            step_name = match.group(2)
            priority = match.group(3)
            dependencies = match.group(4)
            step_content = match.group(5)
            
            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', step_content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            
            # Extract files
            files = []
            files_match = re.search(r'<files>(.*?)</files>', step_content, re.DOTALL)
            
            if files_match:
                files_content = files_match.group(1)
                
                # Handle both correct and malformed file tags
                # Pattern 1: Correct format <file path="...">...</file>
                file_pattern1 = r'<file\\s+path="([^"]+)">([^<]*)</file>'
                
                # Pattern 2: Malformed format <path/to/file.ext>description</file>
                file_pattern2 = r'<([^/>\s]+/[^>]+)>([^<]*)</file>'
                
                # First, find all correctly formatted files
                for file_match in re.finditer(file_pattern1, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    
                    # Convert [id] back to {id} for proper path handling
                    if '[' in desc and ']' in desc:
                        desc = desc.replace('[', '{').replace(']', '}')
                    
                    files.append({
                        'path': path,
                        'description': desc
                    })
                
                # Then, find malformed files
                for file_match in re.finditer(file_pattern2, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    
                    # Skip if this was already matched by the correct pattern
                    if not any(f['path'] == path for f in files):
                        print(f"⚠️  Found malformed file tag: <{path}>")
                        
                        # Convert [id] back to {id} for proper path handling
                        if '[' in desc and ']' in desc:
                            desc = desc.replace('[', '{').replace(']', '}')
                        
                        files.append({
                            'path': path,
                            'description': desc
                        })
            
            step_data = {
                'id': step_id,
                'name': step_name,
                'priority': priority,
                'dependencies': dependencies.split(',') if dependencies else [],
                'description': description,
                'files': files
            }
            
            steps.append(step_data)
        
        return steps
        
    except Exception as e:
        print(f"❌ Error parsing plan: {e}")
        return None'''
    
    print("\n=== Improved _parse_plan_xml Method ===\n")
    print(code)
    
    # Save to a file for reference
    with open('/Users/shanjairaj/Documents/forks/bolt.diy/backend/improved_parse_plan_xml.py', 'w') as f:
        f.write(code)
    
    print("\n✅ Saved improved parser to: improved_parse_plan_xml.py")


if __name__ == "__main__":
    print("Testing Plan Parser with Malformed XML from Airbnb Project\n")
    print("=" * 60)
    
    # Test 1: Show that XML parser fails
    test_xml_parser_fails()
    
    # Test 2: Show that regex parser succeeds
    print("\n" + "=" * 60)
    success = test_regex_parser()
    
    # Test 3: Provide the improved implementation
    print("\n" + "=" * 60)
    create_improved_parser()
    
    print("\n" + "=" * 60)
    if success:
        print("\n✅ SUCCESS: Regex-based parser handles malformed XML correctly!")
        print("   The parser can now handle both correct and malformed file tags.")
    else:
        print("\n❌ FAILED: Regex parser did not work as expected")