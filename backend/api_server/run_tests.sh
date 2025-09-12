#!/bin/bash
# Test runner using correct Python environment

echo "🧪 Running tests with correct Python environment..."
echo "🐍 Using: $(./venv/bin/python --version)"
echo ""

# Test start_backend functionality
echo "📋 Testing start_backend functionality..."
./venv/bin/python /Users/shanjairaj/Documents/horizon_project/test_start_backend.py