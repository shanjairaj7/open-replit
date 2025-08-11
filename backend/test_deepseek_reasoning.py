#!/usr/bin/env python3
"""
Test DeepSeek-R1's advanced reasoning capabilities
This model is known for its step-by-step reasoning
"""

from openai import AzureOpenAI
import time

# Azure configuration
endpoint = "https://rajsu-m9qoo96e-eastus2.openai.azure.com/"
deployment = "DeepSeek-R1-0528"
api_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
api_version = "2024-12-01-preview"

def test_math_reasoning():
    """Test mathematical reasoning with step-by-step solution"""
    print("=" * 70)
    print("🧮 TEST: Mathematical Reasoning")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    problem = """
    A store is having a sale. The original price of a jacket is $120.
    First, there's a 25% discount. Then, there's an additional 10% off the discounted price.
    Finally, there's a 8% sales tax on the final price.
    What is the total amount a customer pays? Show your work step by step.
    """
    
    print("Problem:")
    print(problem)
    print("\n" + "DeepSeek-R1 Solution:" + "\n" + "-" * 40)
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful math tutor. Show your reasoning step by step."},
                {"role": "user", "content": problem}
            ],
            max_tokens=500,
            temperature=0.1,  # Low temperature for consistent math
            stream=True,
            stream_options={"include_usage": True}
        )
        
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    print(content, end='', flush=True)
                    full_response += content
            
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = chunk.usage
        
        print("\n" + "-" * 40)
        if 'usage' in locals():
            print(f"📊 Tokens used: {usage.total_tokens}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_code_generation():
    """Test code generation with explanation"""
    print("\n" + "=" * 70)
    print("💻 TEST: Code Generation with Explanation")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    prompt = """
    Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes.
    Include comments explaining each step of the algorithm.
    """
    
    print("Request:")
    print(prompt)
    print("\n" + "DeepSeek-R1 Response:" + "\n" + "-" * 40)
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert Python programmer. Write clean, efficient code with clear explanations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.3,
            stream=True,
        )
        
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    print(content, end='', flush=True)
                    full_response += content
        
        print("\n" + "-" * 40)
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_logical_reasoning():
    """Test logical reasoning and puzzle solving"""
    print("\n" + "=" * 70)
    print("🧩 TEST: Logical Reasoning")
    print("=" * 70)
    
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    puzzle = """
    Three friends - Alice, Bob, and Charlie - are wearing hats. 
    Each hat is either red or blue, but they can't see their own hat.
    
    Alice can see Bob and Charlie's hats.
    Bob can see Alice and Charlie's hats.
    Charlie can see Alice and Bob's hats.
    
    They're told that at least one person has a red hat.
    
    Alice says: "I don't know my hat color."
    Bob says: "I don't know my hat color either."
    Charlie says: "Now I know my hat color!"
    
    What color is Charlie's hat and how did he figure it out?
    Explain the logical reasoning step by step.
    """
    
    print("Puzzle:")
    print(puzzle)
    print("\n" + "DeepSeek-R1 Analysis:" + "\n" + "-" * 40)
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a logical reasoning expert. Solve puzzles step by step with clear logic."},
                {"role": "user", "content": puzzle}
            ],
            max_tokens=800,
            temperature=0.2,
            stream=True,
        )
        
        full_response = ""
        start_time = time.time()
        
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    print(content, end='', flush=True)
                    full_response += content
        
        elapsed = time.time() - start_time
        print("\n" + "-" * 40)
        print(f"⏱️  Response time: {elapsed:.2f} seconds")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    """Run all reasoning tests"""
    print("\n🚀 DeepSeek-R1 Advanced Reasoning Tests")
    print("Testing the model's ability to reason step-by-step\n")
    
    tests = [
        ("Mathematical Reasoning", test_math_reasoning),
        ("Code Generation", test_code_generation),
        ("Logical Reasoning", test_logical_reasoning),
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
    print("📋 REASONING TEST SUMMARY")
    print("=" * 70)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 DeepSeek-R1 reasoning capabilities verified!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()