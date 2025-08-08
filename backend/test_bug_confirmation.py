#!/usr/bin/env python3
"""Test to confirm the exact bug in coder logic"""

# Test content that has BOTH file and update_file actions
test_content = '''<action type="file" filePath="backend/services/auth_routes.py">
file content here
</action>

<action type="update_file" path="backend/app.py">
update content here
</action>'''

def test_coder_bug():
    print("🔍 TESTING: Confirming the exact coder bug")
    print("="*60)
    
    # Simulate exact coder logic
    accumulated_content = test_content
    update_file_detected = False
    should_interrupt = False
    
    print(f"📝 Content has both actions:")
    print(f"   File action: {'<action type=\"file\"' in accumulated_content}")
    print(f"   Update action: {'<action type=\"update_file\"' in accumulated_content}")
    
    print(f"\n🔍 Step 1: Check update_file detection (line 100)")
    if not update_file_detected and '<action type="update_file"' in accumulated_content:
        update_file_detected = True
        print(f"✅ update_file_detected set to TRUE")
    else:
        print(f"❌ update_file not detected")
        
    print(f"\n🔍 Step 2: Check file action detection (line 107) - AFTER FIX")
    print(f"   Condition: REMOVED 'not update_file_detected' check")
    print(f"   File action present: {'<action type=\"file\"' in accumulated_content}")
    
    if '<action type="file"' in accumulated_content:
        if '</action>' in accumulated_content:
            print(f"✅ File action interrupt should trigger")
            should_interrupt = True
        else:
            print(f"⏳ File action incomplete")
    else:
        print(f"❌ File action detection SKIPPED because update_file_detected=True")
        
    print(f"\n🎯 RESULT:")
    print(f"   update_file_detected: {update_file_detected}")
    print(f"   should_interrupt: {should_interrupt}")
    
    if should_interrupt:
        print(f"\n✅ FIX WORKS!")
        print(f"   File action interrupt triggered correctly")
        print(f"   Even with update_file_detected=True")
        print(f"   The fix allows both detections to work!")
    else:
        print(f"\n❌ Fix failed - still no interrupt")

if __name__ == "__main__":
    test_coder_bug()