#!/usr/bin/env python3
import os
from test_groq_boilerplate_persistent import BoilerplatePersistentGroq

def main():
    # Get API key from environment
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ Please set GROQ_API_KEY environment variable")
        return
    
    # Initialize system with demo_dashboard project
    print("🚀 Starting Enhanced UI Test...")
    system = BoilerplatePersistentGroq(api_key, "demo_dashboard")
    
    # Send request for analytics dashboard with professional UI
    prompt = "Create an analytics dashboard with cards showing revenue, users, and sales. Also add a section that shows our top users in a table."
    
    print(f"\n📝 Sending prompt: {prompt}")
    response = system.send_message(prompt)
    print(f"\n🤖 Model Response:\n{response}")

if __name__ == "__main__":
    main()