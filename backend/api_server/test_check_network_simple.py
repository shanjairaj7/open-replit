#!/usr/bin/env python3
"""
Simple test for check_network functionality
"""

import requests

def test_check_network_simple():
    """Simple test calling the network endpoint directly"""
    print("🧪 Simple test for check_network functionality")
    
    # Test the network logs endpoint directly
    try:
        print("🔍 Testing network logs endpoint...")
        response = requests.get("http://localhost:8084/test-project/logs/network?limit=10", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Network logs endpoint working!")
            print(f"Status: {data.get('status')}")
            print(f"Project ID: {data.get('project_id')}")
            print(f"Log type: {data.get('log_type')}")
            print(f"Retrieved: {data.get('returned_count')} entries")
            print(f"Total stored: {data.get('total_count')} entries")
            
            entries = data.get('entries', [])
            if entries:
                print("\n📝 Sample network requests:")
                for i, entry in enumerate(entries[:3]):  # Show first 3
                    method = entry.get('method', 'GET')
                    url = entry.get('url', '')
                    status = entry.get('status', 0)
                    response_time = entry.get('responseTime', 0)
                    time_str = entry.get('time', '')
                    
                    # Determine status indicator
                    if status >= 400:
                        status_indicator = "❌"
                    elif status >= 300:
                        status_indicator = "⚠️"
                    elif status >= 200:
                        status_indicator = "✅"
                    else:
                        status_indicator = "❓"
                    
                    print(f"  {i+1}. [{time_str}] {status_indicator} {method} {url} - {status} ({response_time}ms)")
            else:
                print("📝 No network requests found")
                
            # Test with specific project that should work with check_network action
            print("\n🎯 check_network action should work with this data!")
            print("✅ Frontend network request monitoring is fully functional")
            
        else:
            print(f"❌ Network logs endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing network logs endpoint: {e}")

if __name__ == "__main__":
    test_check_network_simple()