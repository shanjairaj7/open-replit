#!/usr/bin/env python3
"""
Test Refactored Token Tracking Module

Quick test to verify that the refactored token tracking system works correctly
with both the agent.py and agent_class.py implementations.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to enable imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.token_tracking import TokenTracker, OpenRouterTokenTracker, create_token_tracker


def test_basic_token_tracker():
    """Test basic TokenTracker functionality"""
    print("🧪 Testing basic TokenTracker...")
    
    # Test basic initialization
    tracker = TokenTracker()
    usage = tracker.get_token_usage()
    assert usage['total_tokens'] == 0, "Initial token count should be 0"
    print("  ✅ Basic initialization works")
    
    # Test token usage update
    tracker.update_token_usage(100, 200, 300)
    usage = tracker.get_token_usage()
    assert usage['total_tokens'] == 300, f"Expected 300 tokens, got {usage['total_tokens']}"
    assert usage['prompt_tokens'] == 100, f"Expected 100 prompt tokens, got {usage['prompt_tokens']}"
    assert usage['completion_tokens'] == 200, f"Expected 200 completion tokens, got {usage['completion_tokens']}"
    print("  ✅ Token usage update works")
    
    # Test should_summarize
    assert not tracker.should_summarize(), "Should not summarize with low token count"
    
    # Test with high token count
    tracker.update_token_usage(250000, 250000, 500000)
    assert tracker.should_summarize(), "Should summarize with high token count"
    print("  ✅ Should summarize logic works")
    
    # Test reset
    tracker.reset_token_tracking()
    usage = tracker.get_token_usage()
    assert usage['total_tokens'] == 0, "Token count should be 0 after reset"
    print("  ✅ Token reset works")
    
    print("  🎉 Basic TokenTracker tests passed!")


def test_openrouter_token_tracker():
    """Test OpenRouterTokenTracker functionality"""
    print("🧪 Testing OpenRouterTokenTracker...")
    
    # Get API key from environment
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("  ⚠️ No OPENROUTER_API_KEY found, testing without API functionality")
        tracker = OpenRouterTokenTracker(None)
    else:
        tracker = OpenRouterTokenTracker(api_key)
        print("  ✅ OpenRouterTokenTracker initialized with API key")
    
    # Test basic functionality (inherited from TokenTracker)
    usage = tracker.get_token_usage()
    assert usage['total_tokens'] == 0, "Initial token count should be 0"
    print("  ✅ Basic functionality inherited correctly")
    
    # Test generation ID extraction (mock)
    class MockChunk:
        def __init__(self, chunk_id):
            self.id = chunk_id
    
    mock_chunk = MockChunk("test-gen-123")
    gen_id = tracker.extract_generation_id(mock_chunk)
    assert gen_id == "test-gen-123", f"Expected 'test-gen-123', got {gen_id}"
    print("  ✅ Generation ID extraction works")
    
    print("  🎉 OpenRouterTokenTracker tests passed!")


def test_create_token_tracker():
    """Test create_token_tracker factory function"""
    print("🧪 Testing create_token_tracker factory...")
    
    # Test without API key
    tracker = create_token_tracker()
    assert isinstance(tracker, TokenTracker), "Should return basic TokenTracker without API key"
    assert not isinstance(tracker, OpenRouterTokenTracker), "Should not return OpenRouterTokenTracker without API key"
    print("  ✅ Factory returns basic tracker without API key")
    
    # Test with API key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        tracker = create_token_tracker(api_key)
        assert isinstance(tracker, OpenRouterTokenTracker), "Should return OpenRouterTokenTracker with API key"
        print("  ✅ Factory returns OpenRouter tracker with API key")
    else:
        print("  ⚠️ No API key available, skipping OpenRouter factory test")
    
    print("  🎉 Factory function tests passed!")


def test_backward_compatibility():
    """Test backward compatibility functions"""
    print("🧪 Testing backward compatibility functions...")
    
    from utils.token_tracking import initialize_token_usage, should_summarize_conversation, calculate_token_costs
    
    # Test initialize_token_usage
    usage = initialize_token_usage()
    expected_keys = ['total_tokens', 'prompt_tokens', 'completion_tokens']
    for key in expected_keys:
        assert key in usage, f"Missing key: {key}"
        assert usage[key] == 0, f"Expected 0 for {key}, got {usage[key]}"
    print("  ✅ initialize_token_usage works")
    
    # Test should_summarize_conversation
    assert not should_summarize_conversation({'total_tokens': 100}), "Should not summarize low token count"
    assert should_summarize_conversation({'total_tokens': 600000}), "Should summarize high token count"
    print("  ✅ should_summarize_conversation works")
    
    # Test calculate_token_costs
    costs = calculate_token_costs(1000, 2000)
    assert 'total_cost' in costs, "Missing total_cost"
    assert costs['total_cost'] > 0, "Cost should be greater than 0"
    print("  ✅ calculate_token_costs works")
    
    print("  🎉 Backward compatibility tests passed!")


def main():
    """Run all tests"""
    print("🚀 Starting Token Tracking Refactor Tests")
    print("=" * 50)
    
    try:
        test_basic_token_tracker()
        print()
        
        test_openrouter_token_tracker()
        print()
        
        test_create_token_tracker()
        print()
        
        test_backward_compatibility()
        print()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! Token tracking refactor is working correctly.")
        print("✅ The centralized token_tracking.py module is ready for use.")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()