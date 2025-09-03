#!/bin/bash

# LLM Agent Backend Concurrent Testing Script
# Tests multiple simultaneous requests across different projects and operations

API_URL="http://llm-agent-api.eastus.cloudapp.azure.com:8000"

echo "🚀 Starting Concurrent LLM Agent Backend Test"
echo "Testing non-blocking architecture with multiple projects and operations"
echo "=================================================="

# Function to run API call and time it
run_test() {
    local name="$1"
    local endpoint="$2"
    local data="$3"
    local start_time=$(date +%s.%N)
    
    echo "▶️ Starting: $name"
    response=$(curl -s -X POST "$API_URL/$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    echo "✅ Completed: $name (${duration}s)"
    echo "📄 Response: $response"
    echo "---"
}

# Function to run concurrent tests
run_concurrent_tests() {
    echo "🔄 Running concurrent tests (all starting simultaneously)..."
    
    # Test 1: Fast file read from project-a
    (run_test "Read hello.py from project-a" "file/read" '{
        "project_id": "project-a",
        "file_path": "hello.py"
    }') &
    
    # Test 2: Create files in project-b (medium speed)
    (run_test "Create files in project-b" "execute" '{
        "project_id": "project-b",
        "command": "echo \"Project B content\" > readme.txt && echo \"console.log(\\\"Hello from B\\\")\"; > app.js && ls -la"
    }') &
    
    # Test 3: Long-running build simulation in project-c
    (run_test "Long build simulation project-c" "execute" '{
        "project_id": "project-c", 
        "command": "echo \"Starting build...\" && sleep 10 && echo \"Build complete!\" && echo \"Built project C\" > build.log"
    }') &
    
    # Test 4: Fast file operations in project-d
    (run_test "Quick file ops project-d" "execute" '{
        "project_id": "project-d",
        "command": "echo \"Fast task\" > fast.txt && cat fast.txt"
    }') &
    
    # Test 5: Python execution in test-project
    (run_test "Python execution test-project" "execute" '{
        "project_id": "test-project",
        "command": "python3 hello.py"
    }') &
    
    # Test 6: File read from project-b (should be instant)
    sleep 2  # Start this after a delay to test queue handling
    (run_test "Read newly created file project-b" "file/read" '{
        "project_id": "project-b",
        "file_path": "readme.txt"
    }') &
    
    # Test 7: Complex operations in project-e
    (run_test "Complex ops project-e" "execute" '{
        "project_id": "project-e",
        "command": "mkdir -p src test && echo \"export const hello = () => console.log(\\\"Hello\\\")\" > src/index.js && echo \"// Test file\" > test/test.js && find . -name \"*.js\""
    }') &
    
    # Test 8: System info (should be fast)
    (run_test "System info project-a" "execute" '{
        "project_id": "project-a",
        "command": "pwd && whoami && date"
    }') &
    
    # Wait for all background jobs to complete
    wait
}

# Sequential setup tests
echo "📋 Setting up test projects..."

curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{
        "project_id": "project-a",
        "command": "echo \"print(\\\"Hello from Project A\\\")\" > hello.py && echo \"Project A setup complete\""
    }' > /dev/null

curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{
        "project_id": "test-project", 
        "command": "ls -la"
    }' > /dev/null

echo "✅ Setup complete. Starting concurrent tests..."
echo ""

# Record start time for overall test
overall_start=$(date +%s)

# Run all concurrent tests
run_concurrent_tests

# Calculate total time
overall_end=$(date +%s)
total_time=$((overall_end - overall_start))

echo "=================================================="
echo "🎯 Concurrent Test Results:"
echo "   • Total test duration: ${total_time} seconds"
echo "   • 8 simultaneous operations across 5 projects"
echo "   • Mixed fast/slow operations tested non-blocking behavior"
echo ""
echo "✅ If you see all operations completed without blocking,"
echo "   the async architecture is working correctly!"
echo "=================================================="

# Test queue health
echo "🔍 Final API health check:"
curl -s "$API_URL/health" | python3 -m json.tool

echo ""
echo "🏁 Concurrent testing complete!"