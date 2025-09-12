#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/Users/shanjairaj/Documents/horizon_project/bolt.diy/backend/api_server')

print("Testing all imports...")

try:
    from prompts import fundamental_prompt
    print("✓ fundamental_prompt imported successfully")
except SyntaxError as e:
    print(f"✗ fundamental_prompt has syntax error: {e}")
    
try:
    from prompts import simpler_prompt
    print("✓ simpler_prompt imported successfully")
except SyntaxError as e:
    print(f"✗ simpler_prompt has syntax error: {e}")
    
try:
    from prompts import gpt5_prompt
    print("✓ gpt5_prompt imported successfully")
except SyntaxError as e:
    print(f"✗ gpt5_prompt has syntax error: {e}")
    
try:
    from prompts import planning_prompt
    print("✓ planning_prompt imported successfully")
except SyntaxError as e:
    print(f"✗ planning_prompt has syntax error: {e}")
    
try:
    from prompts import grok_system_prompt
    print("✓ grok_system_prompt imported successfully")
except SyntaxError as e:
    print(f"✗ grok_system_prompt has syntax error: {e}")

print("\nNow testing the full chain:")
try:
    from agent_class import BoilerplatePersistentGroq
    print("✓ agent_class imported successfully")
except Exception as e:
    print(f"✗ agent_class import failed: {e}")
    import traceback
    traceback.print_exc()