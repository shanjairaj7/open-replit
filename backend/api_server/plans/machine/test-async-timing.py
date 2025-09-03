#!/usr/bin/env python3

import asyncio
import aiohttp
import time
import json
from datetime import datetime

API_URL = "http://llm-agent-api.eastus.cloudapp.azure.com:8000"

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

async def make_request(session, name, endpoint, data, expected_duration):
    """Make an API request and track precise timing"""
    start_time = time.time()
    print(f"⏰ {timestamp()} | 🚀 STARTED: {name} (expecting ~{expected_duration}s)")
    
    try:
        async with session.post(f"{API_URL}/{endpoint}", 
                               json=data,
                               timeout=aiohttp.ClientTimeout(total=60)) as response:
            result = await response.json()
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            
            print(f"⏰ {timestamp()} | ✅ COMPLETED: {name} in {duration}s")
            print(f"   📊 Response: {json.dumps(result, indent=2)[:200]}...")
            print(f"   {'🔥 FASTER than expected!' if duration < expected_duration else '⏳ As expected' if duration <= expected_duration + 1 else '🐌 Slower than expected'}")
            print("-" * 60)
            
            return {
                'name': name,
                'duration': duration,
                'expected': expected_duration,
                'start_time': start_time,
                'end_time': end_time,
                'response': result
            }
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        print(f"⏰ {timestamp()} | ❌ FAILED: {name} after {duration}s - {e}")
        return None

async def test_concurrent_operations():
    """Test multiple operations with different expected durations"""
    
    print("🎯 LLM Agent Backend - Async Timing Test")
    print("=" * 60)
    print(f"⏰ Test started at: {timestamp()}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        
        # Create test tasks with different expected durations
        tasks = [
            # Fast operations (should complete almost instantly)
            make_request(session, "📄 Read hello.py (Fast)", "file/read", {
                "project_id": "test-project",
                "file_path": "hello.py"
            }, 0.5),
            
            make_request(session, "⚡ Quick echo (Fast)", "execute", {
                "project_id": "speed-test-1",
                "command": "echo 'Lightning fast!'"
            }, 0.5),
            
            # Medium operations
            make_request(session, "📁 File creation (Medium)", "execute", {
                "project_id": "speed-test-2", 
                "command": "echo 'Creating files...' && for i in {1..5}; do echo \"File $i\" > file$i.txt; done && ls -la"
            }, 2),
            
            make_request(session, "🐍 Python execution (Medium)", "execute", {
                "project_id": "speed-test-3",
                "command": "python3 -c 'import time; print(\"Starting Python task...\"); time.sleep(2); print(\"Python task complete!\")'"
            }, 3),
            
            # Slow operations  
            make_request(session, "🐌 Long task 1 (Slow)", "execute", {
                "project_id": "slow-test-1",
                "command": "echo 'Starting 8-second task...' && sleep 8 && echo 'Long task 1 complete!'"
            }, 8),
            
            make_request(session, "🐌 Long task 2 (Slow)", "execute", {
                "project_id": "slow-test-2", 
                "command": "echo 'Starting 6-second task...' && sleep 6 && echo 'Long task 2 complete!'"
            }, 6),
            
            # Another fast operation that should complete even while slow tasks run
            make_request(session, "💨 Super fast read (Fast)", "file/read", {
                "project_id": "test-project",
                "file_path": "hello.js"
            }, 0.5),
            
            make_request(session, "⚡ Another quick task (Fast)", "execute", {
                "project_id": "speed-test-4",
                "command": "pwd && whoami && date"
            }, 0.5),
        ]
        
        print(f"🚀 Launching {len(tasks)} concurrent requests...")
        print("📊 Watch the completion order - fast tasks should finish first!")
        print("=" * 60)
        
        # Start all tasks simultaneously
        overall_start = time.time()
        results = await asyncio.gather(*tasks)
        overall_end = time.time()
        
        print("=" * 60)
        print("📈 FINAL RESULTS:")
        print("=" * 60)
        
        # Sort results by completion time
        completed_results = [r for r in results if r is not None]
        completed_results.sort(key=lambda x: x['end_time'])
        
        print("🏁 Completion Order (proof of non-blocking):")
        for i, result in enumerate(completed_results, 1):
            status = "🔥" if result['duration'] < result['expected'] else "✅"
            print(f"  {i:2d}. {status} {result['name']} - {result['duration']}s")
        
        total_time = round(overall_end - overall_start, 2)
        sum_expected = sum(r['expected'] for r in completed_results)
        
        print(f"\n⏱️  PERFORMANCE ANALYSIS:")
        print(f"   • Total test duration: {total_time}s")
        print(f"   • Sum of all expected durations: {sum_expected}s")
        print(f"   • Efficiency: {round((sum_expected/total_time)*100, 1)}% concurrent")
        
        if total_time < sum_expected * 0.7:
            print("   🎉 EXCELLENT: True async/non-blocking behavior confirmed!")
            print("      Fast operations completed while slow operations were still running.")
        elif total_time < sum_expected * 0.9:
            print("   ✅ GOOD: Async behavior working well")  
        else:
            print("   ⚠️  CONCERN: May be blocking - investigate worker capacity")

if __name__ == "__main__":
    asyncio.run(test_concurrent_operations())