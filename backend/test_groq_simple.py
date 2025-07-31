#!/usr/bin/env python3
"""
Simple Groq Bolt Test - Minimal example
"""

import asyncio
from groq import AsyncGroq
import os

# System prompt
SYSTEM_PROMPT = """You are a coding assistant that MUST respond using this exact XML format:

<boltArtifact id="project-id" title="Project Title">
<boltAction type="file" filePath="path/to/file">
FILE CONTENT HERE
</boltAction>
<boltAction type="shell">COMMAND HERE</boltAction>
<boltAction type="start">START COMMAND</boltAction>
</boltArtifact>

Rules:
- Use type="file" for creating files
- Use type="shell" for running commands
- Use type="start" for starting servers
- Always provide complete file contents
- Create package.json first for web projects"""

async def test_groq():
    # API key
    api_key = "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"
    client = AsyncGroq(api_key=api_key)
    
    # Test prompt
    prompt = "Create a simple React counter app with increment and decrement buttons"
    
    print("🤖 Testing Groq with Bolt XML format\n")
    print(f"Prompt: {prompt}\n")
    print("Response:")
    print("-" * 60)
    
    # Make API call
    stream = await client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        stream=True,
        max_tokens=4000,
        temperature=0.7
    )
    
    # Collect and print response
    full_response = ""
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print("\n" + "-" * 60)
    
    # Count actions
    import re
    file_actions = len(re.findall(r'<boltAction type="file"', full_response))
    shell_actions = len(re.findall(r'<boltAction type="shell"', full_response))
    start_actions = len(re.findall(r'<boltAction type="start"', full_response))
    
    print(f"\n✅ Summary:")
    print(f"   Files created: {file_actions}")
    print(f"   Shell commands: {shell_actions}")
    print(f"   Start commands: {start_actions}")

if __name__ == "__main__":
    asyncio.run(test_groq())