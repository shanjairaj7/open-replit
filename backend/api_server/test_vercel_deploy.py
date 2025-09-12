#!/usr/bin/env python3
"""
Test script for Vercel deployment
"""

import os
import sys
import json
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from vercel_deployment import deploy_frontend_to_vercel

def test_vercel_deployment(project_id: str, project_name: str = None):
    """Test deploying a project to Vercel"""
    
    print(f"🚀 Testing Vercel deployment...")
    print(f"📋 Project ID: {project_id}")
    print(f"📋 Project Name: {project_name or 'auto-generated'}")
    print("=" * 50)
    
    # Check if Vercel token is set
    if not os.getenv('VERCEL_TOKEN'):
        print("❌ VERCEL_TOKEN environment variable not set!")
        print("\n🔑 To get your Vercel token:")
        print("1. Go to https://vercel.com/account/tokens")
        print("2. Create a new token")  
        print("3. Set it as environment variable:")
        print("   export VERCEL_TOKEN='your_token_here'")
        return
    
    print("✅ Vercel token found")
    print("\n🚀 Starting deployment...")
    
    try:
        result = deploy_frontend_to_vercel(
            project_id=project_id,
            project_name=project_name
        )
        
        print("\n" + "=" * 50)
        print("📊 DEPLOYMENT RESULT:")
        print("=" * 50)
        
        if result["status"] == "success":
            print("✅ SUCCESS!")
            print(f"🌐 Deployment URL: {result['deployment_url']}")
            print(f"📦 Project Name: {result['project_name']}")
            print(f"🆔 Deployment ID: {result['deployment_id']}")
            
            print("\n📋 Deployment Logs:")
            for log in result.get("logs", []):
                print(f"   {log}")
                
        else:
            print("❌ FAILED!")
            print(f"💬 Message: {result['message']}")
            print(f"🔍 Error Type: {result.get('error_type', 'unknown')}")
            
            if "logs" in result:
                print("\n📋 Deployment Logs:")
                for log in result["logs"]:
                    print(f"   {log}")
            
            if "suggestions" in result:
                print("\n💡 Suggestions:")
                for suggestion in result["suggestions"]:
                    print(f"   - {suggestion}")
            
            if "errors" in result:
                print("\n🔍 Detailed Errors:")
                for error in result["errors"]:
                    print(f"   - {error}")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vercel_deploy.py <project_id> [project_name]")
        print("\nExample:")
        print("  python test_vercel_deploy.py horizon-564-c2cc1")
        print("  python test_vercel_deploy.py horizon-564-c2cc1 my-awesome-app")
        sys.exit(1)
    
    project_id = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_vercel_deployment(project_id, project_name)