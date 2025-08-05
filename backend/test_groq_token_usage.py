#!/usr/bin/env python3
"""
Test script to explore Groq API token usage tracking
"""

import os
import json
from groq import Groq
from datetime import datetime

def test_token_usage():
    """Test token usage tracking with Groq API"""
    api_key = os.getenv("GROQ_API_KEY", "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")
    client = Groq(api_key=api_key)
    
    # Test with non-streaming first
    print("🔍 Testing non-streaming completion for token usage...")
    
    try:
        completion = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a haiku about programming."}
            ],
            temperature=0.1,
            max_tokens=100,
            stream=False  # Non-streaming to get usage data
        )
        
        print("\n✅ Non-streaming completion successful!")
        print(f"Response: {completion.choices[0].message.content}")
        
        # Check if usage data is available
        if hasattr(completion, 'usage'):
            print("\n📊 Token Usage Data Found!")
            print(f"   Prompt tokens: {completion.usage.prompt_tokens}")
            print(f"   Completion tokens: {completion.usage.completion_tokens}")
            print(f"   Total tokens: {completion.usage.total_tokens}")
        else:
            print("\n❌ No usage attribute found")
            
        # Inspect the completion object
        print("\n🔍 Completion object attributes:")
        for attr in dir(completion):
            if not attr.startswith('_'):
                print(f"   - {attr}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test with streaming
    print("\n\n🔍 Testing streaming completion for token usage...")
    
    try:
        stream = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count from 1 to 5."}
            ],
            temperature=0.1,
            max_tokens=50,
            stream=True,
        )
        
        accumulated_content = ""
        chunk_count = 0
        final_chunk = None
        all_chunks = []
        
        for chunk in stream:
            chunk_count += 1
            all_chunks.append(chunk)
            
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                accumulated_content += chunk.choices[0].delta.content
            
            # Keep the last chunk
            final_chunk = chunk
            
            # Check if any chunk has usage data
            if hasattr(chunk, 'usage') and chunk.usage:
                print(f"\n📊 Token usage found in chunk {chunk_count}!")
                print(f"   Prompt tokens: {chunk.usage.prompt_tokens}")
                print(f"   Completion tokens: {chunk.usage.completion_tokens}")
                print(f"   Total tokens: {chunk.usage.total_tokens}")
        
        print(f"\n✅ Streaming completed with {chunk_count} chunks")
        print(f"Response: {accumulated_content}")
        
        # Check the final chunk for usage data
        if final_chunk and hasattr(final_chunk, 'usage') and final_chunk.usage:
            print("\n📊 Token usage in final chunk:")
            print(f"   Prompt tokens: {final_chunk.usage.prompt_tokens}")
            print(f"   Completion tokens: {final_chunk.usage.completion_tokens}")
            print(f"   Total tokens: {final_chunk.usage.total_tokens}")
        else:
            print("\n❌ No usage data found in final chunk")
            
        # Check x_groq for usage data
        if final_chunk and hasattr(final_chunk, 'x_groq'):
            print("\n🔍 Checking x_groq data:")
            x_groq = final_chunk.x_groq
            if x_groq:
                print(f"   x_groq type: {type(x_groq)}")
                print(f"   x_groq value: {x_groq}")
                if hasattr(x_groq, 'usage'):
                    print(f"   ✅ Found usage in x_groq!")
                    print(f"   Usage data: {x_groq.usage}")
                    
        # Check all chunks for usage
        print("\n🔍 Checking all chunks for usage data:")
        for i, chunk in enumerate(all_chunks[-5:]):  # Check last 5 chunks
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                print(f"   Chunk {len(all_chunks) - 5 + i}: usage = {chunk.usage}")
                
        # Alternative: Try making a non-streaming call with same messages to get token count
        print("\n\n🔍 Alternative: Getting token count via non-streaming call...")
        try:
            # Use same messages to get accurate token count
            usage_check = client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Count from 1 to 5."},
                    {"role": "assistant", "content": accumulated_content}  # Include the response
                ],
                temperature=0.1,
                max_tokens=1,  # Minimal tokens since we just want usage
                stream=False
            )
            
            if hasattr(usage_check, 'usage'):
                print("✅ Got token usage from non-streaming check:")
                print(f"   Total tokens (including response): {usage_check.usage.prompt_tokens}")
                # Subtract the response from prompt tokens to get original prompt size
                original_prompt_tokens = usage_check.usage.prompt_tokens - len(accumulated_content.split())
                print(f"   Estimated original prompt tokens: ~{original_prompt_tokens}")
                print(f"   Completion tokens: ~{len(accumulated_content.split())}")
        except Exception as e:
            print(f"   Alternative method error: {e}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_token_usage()