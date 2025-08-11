#!/usr/bin/env python3
"""
Test to measure the volume of DeepSeek's thinking vs actual response
"""

import time
from openai import AzureOpenAI

# Configuration
endpoint = "https://rajsu-m9qoo96e-eastus2.openai.azure.com/"
deployment = "DeepSeek-R1-0528"
api_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
api_version = "2024-12-01-preview"

def measure_thinking_vs_response():
    """Measure how much DeepSeek thinks vs final response"""
    print("🧠 MEASURING DEEPSEEK'S THINKING VOLUME")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    problem = "Calculate 17 * 23 step by step"
    
    print(f"Problem: {problem}")
    print("Analyzing thinking vs response content...\n")
    
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "user", "content": problem}
            ],
            stream=True,
            max_tokens=500
        )
        
        thinking_content = ""
        final_content = ""
        thinking_chunks = 0
        content_chunks = 0
        first_thinking_time = None
        first_content_time = None
        
        print("📊 REAL-TIME ANALYSIS:")
        print("T = Thinking chunk, C = Content chunk")
        print("-" * 50)
        
        for i, chunk in enumerate(response):
            current_time = time.time() - start_time
            
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Track thinking content
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_content += delta.reasoning_content
                    thinking_chunks += 1
                    if first_thinking_time is None:
                        first_thinking_time = current_time
                    print(f"T{thinking_chunks}", end='', flush=True)
                
                # Track final content
                if hasattr(delta, 'content') and delta.content:
                    final_content += delta.content
                    content_chunks += 1
                    if first_content_time is None:
                        first_content_time = current_time
                        print(f"\n\n🎯 FIRST CONTENT at {current_time:.2f}s")
                    print(f"C{content_chunks}", end='', flush=True)
        
        total_time = time.time() - start_time
        
        print("\n\n" + "=" * 60)
        print("📊 THINKING vs RESPONSE ANALYSIS")
        print("=" * 60)
        
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print(f"⏱️  Time to first thinking: {first_thinking_time:.2f}s" if first_thinking_time else "No thinking detected")
        print(f"⏱️  Time to first content: {first_content_time:.2f}s" if first_content_time else "No content detected")
        
        if first_content_time and first_thinking_time:
            thinking_duration = first_content_time - first_thinking_time
            print(f"⏱️  Pure thinking time: {thinking_duration:.2f}s")
        
        print(f"\n📝 THINKING CONTENT:")
        print(f"   • Chunks: {thinking_chunks}")
        print(f"   • Characters: {len(thinking_content)}")
        if thinking_content:
            print(f"   • Preview: {thinking_content[:200]}...")
        
        print(f"\n📝 FINAL CONTENT:")
        print(f"   • Chunks: {content_chunks}")  
        print(f"   • Characters: {len(final_content)}")
        if final_content:
            print(f"   • Full response: {final_content}")
        
        # Calculate ratios
        if len(final_content) > 0:
            thinking_ratio = len(thinking_content) / len(final_content)
            print(f"\n🧮 THINKING RATIO: {thinking_ratio:.1f}:1")
            print(f"   (DeepSeek thinks {thinking_ratio:.1f}x more than it outputs!)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_complex_reasoning():
    """Test with a complex problem that requires lots of thinking"""
    print("\n" + "=" * 60)
    print("🧠 COMPLEX REASONING TEST")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    complex_problem = """
    Three friends split a restaurant bill. Alice pays twice what Bob pays. 
    Charlie pays $3 more than Bob. If the total bill is $51, how much does each person pay?
    """
    
    print(f"Complex Problem: {complex_problem.strip()}")
    
    try:
        start_time = time.time()
        thinking_chars = 0
        content_chars = 0
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "Solve this step by step with detailed reasoning."},
                {"role": "user", "content": complex_problem}
            ],
            stream=True,
            max_tokens=800
        )
        
        print("\n📊 LIVE THINKING MONITOR:")
        print("🧠 = 100 thinking chars, 💬 = 100 response chars")
        print("-" * 50)
        
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Count thinking characters
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_chars += len(delta.reasoning_content)
                    if thinking_chars % 100 == 0:  # Every 100 chars
                        print("🧠", end='', flush=True)
                
                # Count response characters  
                if hasattr(delta, 'content') and delta.content:
                    content_chars += len(delta.content)
                    if content_chars % 100 == 0:  # Every 100 chars
                        print("💬", end='', flush=True)
        
        total_time = time.time() - start_time
        
        print(f"\n\n📊 COMPLEX PROBLEM RESULTS:")
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print(f"🧠 Thinking characters: {thinking_chars:,}")
        print(f"💬 Response characters: {content_chars:,}")
        
        if content_chars > 0:
            ratio = thinking_chars / content_chars
            print(f"🧮 Thinking ratio: {ratio:.1f}:1")
            print(f"💡 DeepSeek did {ratio:.1f}x more thinking than output!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧠 DeepSeek-R1 Thinking Volume Analysis")
    print("Understanding why responses take so long\n")
    
    # Test simple problem
    success1 = measure_thinking_vs_response()
    
    # Test complex problem
    success2 = test_complex_reasoning()
    
    print("\n" + "=" * 60)
    print("💡 EXPLANATION FOR LONG RESPONSE TIMES")
    print("=" * 60)
    print("DeepSeek-R1 is designed to do extensive internal reasoning")
    print("before producing its final answer. This is why:")
    print("• Responses take longer to start")
    print("• But the quality is much higher") 
    print("• The model thinks through problems thoroughly")
    print("• You're seeing the full reasoning process now!")