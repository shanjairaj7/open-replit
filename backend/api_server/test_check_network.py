#!/usr/bin/env python3
"""
Test script for check_network action handler
"""

import sys
import os

# Add the current directory to path to import the modules
sys.path.append(os.path.dirname(__file__))

from base_test_azure_hybrid import GroqAgentState

def test_check_network_action():
    """Test the check_network interrupt handler"""
    print("🧪 Testing check_network action handler")
    
    # Create a mock agent state
    agent_state = GroqAgentState()
    agent_state.project_id = "test-project"
    
    # Test check_network action
    test_action = {
        "type": "check_network"
    }
    
    print("🔍 Testing check_network interrupt handler...")
    result = agent_state._handle_check_network_interrupt(test_action)
    
    if result:
        print(f"✅ check_network handler worked!")
        print(f"Status: {result.get('status')}")
        print(f"Service: {result.get('service')}")
        print(f"Request count: {result.get('request_count')}")
        print(f"Error count: {result.get('error_count')}")
        print(f"Success count: {result.get('success_count')}")
        print(f"Total stored: {result.get('total_stored')}")
        
        requests_content = result.get('requests', '')
        if requests_content:
            print("\n📝 Network Requests:")
            print(requests_content[:500] + "..." if len(requests_content) > 500 else requests_content)
        
        recent_errors = result.get('recent_errors', [])
        if recent_errors:
            print(f"\n🚨 Recent errors: {len(recent_errors)}")
            for error in recent_errors[:2]:
                print(f"  • {error}")
                
    else:
        print("❌ check_network handler failed")
        
    return result

if __name__ == "__main__":
    test_check_network_action()