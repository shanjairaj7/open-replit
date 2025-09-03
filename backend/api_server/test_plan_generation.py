#!/usr/bin/env python3
"""
Test script for the planning function
"""
import asyncio
import os
from utils import generate_user_message_plan

async def test_planning():
    """Test the planning function with various user requests"""
    
    # Test case 1: AI-powered task app (your example)
    test_request_1 = """
    build me a ai powered task app, notion and todoist is good, but no proper ai integrations. 
    i want you to build a app where people can create their todos, one clicked should take them 
    to a new page to show that task information, should be able to add descriptions and add 
    comments to the tasks. should be intuitive and simple. then once users click on a todo, 
    they should be able to talk with ai to land on a plan on how they are going to do that task, 
    then the ai should update the description with that plan
    """
    
    # Test case 2: CRM with multiple features
    test_request_2 = """
    Build a CRM where I can manage contacts, track deals, see analytics, send automated emails, 
    import CSV files, create custom fields, and generate reports
    """
    
    # Test case 3: Simple app
    test_request_3 = """
    I need a simple note-taking app where I can create, edit, and delete notes with markdown support
    """
    
    print("=" * 80)
    print("PLANNING FUNCTION TEST")
    print("=" * 80)
    
    # Test each request
    for i, request in enumerate([test_request_1, test_request_2, test_request_3], 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}")
        print(f"{'=' * 80}")
        print(f"USER REQUEST:\n{request.strip()}")
        print(f"\n{'-' * 40}")
        print("GENERATED PLAN:")
        print(f"{'-' * 40}\n")
        
        try:
            plan = await generate_user_message_plan(request)
            print(plan)
        except Exception as e:
            print(f"ERROR: {e}")
            print("Make sure OPENROUTER_API_KEY is set in environment variables")
        
        print(f"\n{'=' * 80}\n")
        
        # Continue to next test automatically

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY not found in environment variables")
        print("Set it with: export OPENROUTER_API_KEY='your-key-here'")
        print()
    
    asyncio.run(test_planning())