#!/usr/bin/env python3
"""
Generate a plan for the AI-powered task app and save to MD file
"""
import asyncio
import os
from utils import generate_user_message_plan
from datetime import datetime

async def generate_and_save_plan():
    """Generate plan and save to markdown file"""
    
    # Set API key
    os.environ["OPENAI_KEY"] = "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"
    
    # The user request
    user_request = """
    build me a ai powered task app, notion and todoist is good, but no proper ai integrations. 
    i want you to build a app where people can create their todos, one clicked should take them 
    to a new page to show that task information, should be able to add descriptions and add 
    comments to the tasks. should be intuitive and simple. then once users click on a todo, 
    they should be able to talk with ai to land on a plan on how they are going to do that task, 
    then the ai should update the description with that plan
    """
    
    print("🚀 Generating implementation plan for AI-powered task app...")
    print("-" * 80)
    
    try:
        # Generate the plan
        plan = await generate_user_message_plan(user_request)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_task_app_plan_{timestamp}.md"
        filepath = f"/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/plans/{filename}"
        
        # Ensure plans directory exists
        os.makedirs("/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/plans", exist_ok=True)
        
        # Add header to the plan
        full_plan = f"""# AI-Powered Task App - Implementation Plan
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## User Request
{user_request.strip()}

---

{plan}
"""
        
        # Save to file
        with open(filepath, 'w') as f:
            f.write(full_plan)
        
        print(f"✅ Plan saved to: {filepath}")
        print("-" * 80)
        print("\n📄 Opening in Zed editor...")
        
        # Open in Zed
        os.system(f"zed {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    filepath = asyncio.run(generate_and_save_plan())
    if filepath:
        print(f"\n✨ Plan successfully generated and opened in Zed!")
        print(f"📍 Location: {filepath}")