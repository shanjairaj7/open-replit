#!/usr/bin/env python3
"""
Modal.com deployment script for horizon-api
"""
import subprocess
import sys

def deploy_to_modal():
    """Deploy the streaming API to Modal.com"""
    
    print("🚀 Deploying horizon-api to Modal.com...")
    print("=" * 50)
    
    try:
        # Deploy using Modal CLI
        result = subprocess.run([
            "modal", "deploy", "streaming_api.py"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Successfully deployed to Modal!")
            print("\n📊 Deployment Output:")
            print(result.stdout)
            
            if result.stderr:
                print("\n⚠️ Warnings:")
                print(result.stderr)
                
        else:
            print("❌ Deployment failed!")
            print("\n🐛 Error Output:")
            print(result.stderr)
            if result.stdout:
                print("\n📊 Additional Info:")
                print(result.stdout)
            return False
            
        return True
        
    except FileNotFoundError:
        print("❌ Modal CLI not found!")
        print("Please install Modal CLI first:")
        print("pip install modal")
        return False
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False

def setup_secrets():
    """Instructions for setting up Modal secrets"""
    print("\n🔐 Setting up Modal Secrets...")
    print("=" * 50)
    
    print("You need to create these secrets in Modal dashboard:")
    print()
    
    print("1. azure-storage-secret:")
    print("   AZURE_STORAGE_CONNECTION_STRING=<your_azure_connection_string>")
    print()
    
    print("2. openai-secret:")
    print("   GROQ_API_KEY=<your_groq_api_key>")
    print("   AZURE_OPENAI_API_KEY=<your_azure_openai_key>")
    print("   AZURE_OPENAI_ENDPOINT=<your_azure_openai_endpoint>")
    print()
    
    print("🌐 Create secrets at: https://modal.com/secrets")

if __name__ == "__main__":
    print("🌐 Modal.com Deployment for horizon-api")
    print("=" * 60)
    
    # Show secret setup instructions first
    setup_secrets()
    
    # Ask if user wants to proceed with deployment
    response = input("\nHave you set up the secrets? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        success = deploy_to_modal()
        if success:
            print("\n🎉 Deployment completed successfully!")
            print("Your API is now live at: https://your-modal-url.modal.run")
        else:
            print("\n💥 Deployment failed. Check the errors above.")
            sys.exit(1)
    else:
        print("\n📋 Please set up the secrets first, then run this script again.")
        print("Run: python deploy_modal.py")