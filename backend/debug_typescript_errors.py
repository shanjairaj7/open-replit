#!/usr/bin/env python3
"""
Debug TypeScript error checking specifically
"""

import requests
import json
import time

API_BASE = "http://206.189.229.208:8000/api"

def debug_typescript_error_checking():
    print("🔍 Debugging TypeScript Error Checking")
    print("=" * 50)
    
    # Use existing project
    project_id = "0e05c282"
    
    # Create a simple TypeScript file with clear errors
    print("\n1️⃣ Creating simple TypeScript file with obvious errors...")
    
    simple_ts_content = """
// Simple TypeScript errors
let age: number = "not a number";  // Type error
let name: string = 123;            // Type error
console.log(nonExistentVariable);  // Reference error

function broken(x: string): number {
    return x;  // Type error: string is not assignable to number
}
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/frontend/src/simple_errors.ts",
        json={"content": simple_ts_content}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File created: frontend/src/simple_errors.ts")
        print(f"📋 Full API Response:")
        print(json.dumps(result, indent=2))
        
        if result.get('typescript_errors'):
            print(f"\n📘 TypeScript errors found:")
            print(result['typescript_errors'])
        else:
            print(f"\n❌ No TypeScript errors detected")
            
        print(f"\n🔍 TypeScript check status:")
        print(json.dumps(result.get('typescript_check_status', {}), indent=2))
        
    else:
        print(f"❌ Failed to create file: {response.text}")
    
    # Try updating an existing file
    print(f"\n2️⃣ Updating existing broken_component.tsx...")
    
    updated_content = """
// Updated with more obvious errors
let broken: string = 123;
let another: number = "string";
console.log(undefinedVar);
"""
    
    response = requests.put(
        f"{API_BASE}/projects/{project_id}/files/frontend/src/broken_component.tsx",
        json={"content": updated_content}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ File updated")
        print(f"📋 Full API Response:")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    debug_typescript_error_checking()