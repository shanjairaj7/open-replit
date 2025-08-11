#!/usr/bin/env python3
"""
Test to capture DeepSeek-R1's thinking/reasoning process
Investigate raw response structure and timing
"""

import time
import json
from openai import AzureOpenAI

# Configuration
endpoint = "https://rajsu-m9qoo96e-eastus2.openai.azure.com/"
deployment = "DeepSeek-R1-0528"
api_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
api_version = "2024-12-01-preview"

def analyze_raw_chunks():
    """Analyze raw chunks to understand DeepSeek's thinking process"""
    print("🔍 ANALYZING RAW CHUNKS FOR THINKING PROCESS")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    # Problem that requires reasoning
    problem = "Solve this step by step: If I have 3 apples and give away 2, then buy 5 more, how many do I have?"
    
    print(f"Problem: {problem}")
    print("\nRAW CHUNK ANALYSIS:")
    print("-" * 50)
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "Think through this step by step before answering."},
                {"role": "user", "content": problem}
            ],
            stream=True,
            stream_options={"include_usage": True},
            max_tokens=500
        )
        
        chunk_count = 0
        first_content_time = None
        start_time = time.time()
        thinking_content = ""
        final_content = ""
        
        for chunk in response:
            chunk_count += 1
            current_time = time.time() - start_time
            
            # Print raw chunk structure for first few chunks
            if chunk_count <= 5:
                print(f"\n--- CHUNK {chunk_count} (t={current_time:.2f}s) ---")
                chunk_dict = chunk.model_dump() if hasattr(chunk, 'model_dump') else str(chunk)
                print(json.dumps(chunk_dict, indent=2))
            
            # Check all possible content fields
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                
                # Check delta content
                if hasattr(choice, 'delta') and choice.delta:
                    delta = choice.delta
                    
                    # Look for different content types
                    content_found = False
                    if hasattr(delta, 'content') and delta.content:
                        if first_content_time is None:
                            first_content_time = current_time
                            print(f"\n🎯 FIRST CONTENT at t={current_time:.2f}s")
                        
                        content = delta.content
                        final_content += content
                        content_found = True
                        
                        if chunk_count <= 10:  # Show first 10 content chunks
                            print(f"CONTENT({chunk_count}): {repr(content)}")
                    
                    # Check for reasoning/thinking fields
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        thinking_content += delta.reasoning
                        print(f"REASONING({chunk_count}): {repr(delta.reasoning)}")
                    
                    if hasattr(delta, 'thoughts') and delta.thoughts:
                        thinking_content += delta.thoughts
                        print(f"THOUGHTS({chunk_count}): {repr(delta.thoughts)}")
                    
                    # Check for any other fields in delta
                    for attr in dir(delta):
                        if not attr.startswith('_') and attr not in ['content', 'reasoning', 'thoughts', 'role', 'function_call', 'tool_calls']:
                            value = getattr(delta, attr)
                            if value is not None and str(value).strip():
                                print(f"DELTA.{attr.upper()}({chunk_count}): {repr(value)}")
                
                # Check message content (non-delta)
                if hasattr(choice, 'message') and choice.message:
                    message = choice.message
                    if hasattr(message, 'content') and message.content:
                        print(f"MESSAGE.CONTENT({chunk_count}): {repr(message.content)}")
            
            # Check for usage info
            if hasattr(chunk, 'usage') and chunk.usage:
                print(f"\n💰 USAGE INFO at chunk {chunk_count}:")
                print(f"  Prompt tokens: {chunk.usage.prompt_tokens}")
                print(f"  Completion tokens: {chunk.usage.completion_tokens}")
                print(f"  Total tokens: {chunk.usage.total_tokens}")
        
        end_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Total chunks: {chunk_count}")
        print(f"Total time: {end_time:.2f} seconds")
        print(f"Time to first content: {first_content_time:.2f}s" if first_content_time else "No content detected")
        print(f"Average time per chunk: {(end_time/chunk_count*1000):.2f} ms")
        
        if thinking_content:
            print(f"\n🧠 THINKING CONTENT ({len(thinking_content)} chars):")
            print(thinking_content)
        else:
            print("\n🧠 No explicit thinking content found in standard fields")
        
        print(f"\n📝 FINAL CONTENT ({len(final_content)} chars):")
        print(final_content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_thinking_with_complex_problem():
    """Test with a complex problem that requires more thinking"""
    print("\n" + "=" * 70)
    print("🧠 TESTING COMPLEX REASONING PROBLEM")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    complex_problem = """
    A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. 
    How much does the ball cost? Think carefully about this.
    """
    
    print(f"Problem: {complex_problem.strip()}")
    print("\nTIMING ANALYSIS:")
    print("-" * 50)
    
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a careful reasoning assistant. Think through problems step by step."},
                {"role": "user", "content": complex_problem}
            ],
            stream=True,
            max_tokens=800,
            temperature=0.1  # Low temperature for consistent reasoning
        )
        
        silence_periods = []
        last_content_time = start_time
        total_content = ""
        
        print("Time\tChunk\tContent")
        print("-" * 40)
        
        for i, chunk in enumerate(response):
            current_time = time.time()
            elapsed = current_time - start_time
            
            content_in_chunk = False
            
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    total_content += content
                    content_in_chunk = True
                    
                    # Check for silence periods (gaps between content)
                    silence_duration = current_time - last_content_time
                    if silence_duration > 0.5:  # More than 500ms gap
                        silence_periods.append(silence_duration)
                    
                    last_content_time = current_time
                    
                    # Show timing for content chunks
                    print(f"{elapsed:.2f}s\t{i+1}\t{repr(content[:50])}")
            
            if not content_in_chunk and i % 10 == 0:  # Show periodic empty chunks
                print(f"{elapsed:.2f}s\t{i+1}\t[empty]")
        
        total_time = time.time() - start_time
        
        print("-" * 50)
        print(f"📊 Total time: {total_time:.2f} seconds")
        print(f"📊 Total content length: {len(total_content)} characters")
        
        if silence_periods:
            print(f"🤫 Silence periods detected: {len(silence_periods)}")
            print(f"🤫 Longest silence: {max(silence_periods):.2f} seconds")
            print(f"🤫 Average silence: {sum(silence_periods)/len(silence_periods):.2f} seconds")
            print("💭 This might indicate internal reasoning/thinking periods!")
        
        print(f"\n📝 FULL RESPONSE:")
        print(total_content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_non_streaming_vs_streaming():
    """Compare non-streaming vs streaming response times"""
    print("\n" + "=" * 70)
    print("⚡ COMPARING NON-STREAMING vs STREAMING")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    test_problem = "What is 15 * 23? Show your work."
    
    # Test non-streaming first
    print("1. NON-STREAMING TEST:")
    print("-" * 30)
    
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "Solve math problems step by step."},
                {"role": "user", "content": test_problem}
            ],
            stream=False,
            max_tokens=300
        )
        end_time = time.time()
        
        non_stream_time = end_time - start_time
        non_stream_content = response.choices[0].message.content
        
        print(f"⏱️  Non-streaming time: {non_stream_time:.2f} seconds")
        print(f"📝 Content length: {len(non_stream_content)} characters")
        
    except Exception as e:
        print(f"❌ Non-streaming error: {e}")
        return False
    
    # Test streaming
    print("\n2. STREAMING TEST:")
    print("-" * 30)
    
    try:
        start_time = time.time()
        first_content_time = None
        last_content_time = None
        stream_content = ""
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "Solve math problems step by step."},
                {"role": "user", "content": test_problem}
            ],
            stream=True,
            max_tokens=300
        )
        
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    current_time = time.time()
                    if first_content_time is None:
                        first_content_time = current_time
                    last_content_time = current_time
                    stream_content += delta.content
        
        total_stream_time = time.time() - start_time
        time_to_first = first_content_time - start_time if first_content_time else 0
        
        print(f"⏱️  Total streaming time: {total_stream_time:.2f} seconds")
        print(f"⏱️  Time to first content: {time_to_first:.2f} seconds")
        print(f"📝 Content length: {len(stream_content)} characters")
        
        print("\n📊 COMPARISON:")
        print(f"Time difference: {abs(non_stream_time - total_stream_time):.2f}s")
        print(f"Thinking time (before first token): {time_to_first:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return False

def main():
    """Run all thinking analysis tests"""
    print("🧠 DeepSeek-R1 Thinking Process Analysis")
    print("Investigating reasoning delays and internal processing\n")
    
    tests = [
        ("Raw Chunks Analysis", analyze_raw_chunks),
        ("Complex Problem Timing", test_thinking_with_complex_problem),
        ("Streaming vs Non-streaming", test_non_streaming_vs_streaming),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 THINKING ANALYSIS SUMMARY")
    print("=" * 70)
    
    for test_name, success in results:
        status = "✅ COMPLETED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")

if __name__ == "__main__":
    main()