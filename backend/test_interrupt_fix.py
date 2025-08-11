#!/usr/bin/env python3
"""
Test script to verify the interrupt handling fix works correctly
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

def run_test_with_timeout(test_name: str, command: list, timeout: int = 45, expected_patterns: list = None):
    """Run a test with timeout and pattern matching"""
    
    print(f"\n🧪 TEST: {test_name}")
    print("=" * 60)
    print(f"📝 Command: {' '.join(command)}")
    print(f"⏰ Timeout: {timeout} seconds")
    
    if expected_patterns:
        print(f"🔍 Looking for patterns:")
        for pattern in expected_patterns:
            print(f"   - {pattern}")
    
    print("-" * 60)
    
    try:
        # Start the process
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output_lines = []
        start_time = time.time()
        
        # Send input and read output with timeout
        if process.stdin:
            process.stdin.write("create a simple counter component\n")
            process.stdin.close()
        
        while True:
            # Check for timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"⏰ TIMEOUT after {elapsed:.1f} seconds")
                process.kill()
                break
            
            # Try to read output
            try:
                process.stdout.settimeout(0.5)
            except:
                pass
                
            line = process.stdout.readline()
            
            if line:
                line = line.strip()
                output_lines.append(line)
                print(line)
                
                # Check for expected patterns
                if expected_patterns:
                    for pattern in expected_patterns:
                        if pattern.lower() in line.lower():
                            print(f"✅ FOUND PATTERN: {pattern}")
            
            # Check if process ended
            if process.poll() is not None:
                print(f"🏁 Process ended naturally after {elapsed:.1f} seconds")
                break
        
        # Collect remaining output
        try:
            remaining_output, _ = process.communicate(timeout=2)
            if remaining_output:
                remaining_lines = remaining_output.strip().split('\n')
                output_lines.extend(remaining_lines)
                for line in remaining_lines:
                    if line.strip():
                        print(line)
        except subprocess.TimeoutExpired:
            pass
        
        return_code = process.poll()
        
        print("-" * 60)
        print(f"📊 RESULTS:")
        print(f"   Return Code: {return_code}")
        print(f"   Output Lines: {len(output_lines)}")
        print(f"   Elapsed Time: {time.time() - start_time:.1f} seconds")
        
        # Analysis
        interrupt_indicators = [
            "COMPLETE FILE ACTION VALIDATED",
            "INTERRUPT",  
            "Breaking from chunk loop",
            "Creating file immediately",
            "File action tags found but not yet complete"
        ]
        
        found_indicators = []
        for line in output_lines:
            for indicator in interrupt_indicators:
                if indicator.lower() in line.lower():
                    found_indicators.append((indicator, line))
        
        if found_indicators:
            print(f"🔍 INTERRUPT ANALYSIS:")
            for indicator, line in found_indicators:
                print(f"   ✅ {indicator}: {line[:100]}...")
        else:
            print("⚠️  No interrupt indicators found in output")
        
        return {
            "success": True,
            "return_code": return_code,
            "output_lines": output_lines,
            "elapsed_time": time.time() - start_time,
            "interrupt_indicators": found_indicators
        }
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": time.time() - start_time if 'start_time' in locals() else 0
        }

def main():
    """Run interrupt handling tests"""
    
    print("🔧 INTERRUPT HANDLING FIX VERIFICATION")
    print("=" * 60)
    print("Testing both original and fixed versions to compare behavior")
    
    backend_dir = Path(__file__).parent
    setup_dir = backend_dir / "setup"
    
    # Test 1: Original version
    original_command = [
        sys.executable, str(setup_dir / "base.py"), "--create"
    ]
    
    # Test 2: Fixed version
    fixed_command = [
        sys.executable, str(setup_dir / "base_test.py"), "--create"
    ]
    
    expected_patterns = [
        "COMPLETE FILE ACTION VALIDATED",
        "File action tags found but not yet complete",
        "validated file creation interrupt"
    ]
    
    # Run tests
    print("\n" + "="*60)
    print("TEST 1: ORIGINAL VERSION (base.py)")
    print("="*60)
    original_result = run_test_with_timeout(
        "Original Interrupt Handling", 
        original_command, 
        timeout=45,
        expected_patterns=expected_patterns
    )
    
    print("\n" + "="*60) 
    print("TEST 2: FIXED VERSION (base_test.py)")
    print("="*60)
    fixed_result = run_test_with_timeout(
        "Fixed Interrupt Handling",
        fixed_command,
        timeout=45, 
        expected_patterns=expected_patterns
    )
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    print(f"Original Version:")
    print(f"   Success: {original_result.get('success', False)}")
    print(f"   Interrupt Indicators: {len(original_result.get('interrupt_indicators', []))}")
    
    print(f"Fixed Version:")
    print(f"   Success: {fixed_result.get('success', False)}")
    print(f"   Interrupt Indicators: {len(fixed_result.get('interrupt_indicators', []))}")
    
    # Analysis
    if fixed_result.get('success') and len(fixed_result.get('interrupt_indicators', [])) > 0:
        print("\n✅ FIXED VERSION SHOWS IMPROVED INTERRUPT HANDLING!")
        
        fixed_indicators = fixed_result.get('interrupt_indicators', [])
        for indicator, line in fixed_indicators:
            if "validated" in indicator.lower():
                print(f"   🎯 Validation working: {line[:80]}...")
    else:
        print("\n⚠️  Need to investigate further - fixed version may need more work")
    
    return original_result, fixed_result

if __name__ == "__main__":
    main()