#!/usr/bin/env python3
"""
Simple test for the planning function
"""
import asyncio
import os
from utils.basic import enhance_user_message

async def test_planning():
    """Test the message enhancement function with the AI task app example"""

    # Set the API key if available
    api_key = "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"
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key

    test_request = """
    build me a ai powered task app, notion and todoist is good, but no proper ai integrations.
    i want you to build a app where people can create their todos, one clicked should take them
    to a new page to show that task information, should be able to add descriptions and add
    comments to the tasks. should be intuitive and simple. then once users click on a todo,
    they should be able to talk with ai to land on a plan on how they are going to do that task,
    then the ai should update the description with that plan
    """

    print("=" * 80)
    print("AI TASK APP MESSAGE ENHANCEMENT TEST")
    print("=" * 80)
    print(f"\nUSER REQUEST:\n{test_request.strip()}\n")
    print("-" * 80)
    print("ENHANCED MESSAGE:")
    print("-" * 80)

    try:
        enhanced_message = await enhance_user_message(test_request)
        print(enhanced_message)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_planning())
