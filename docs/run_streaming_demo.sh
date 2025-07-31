#!/bin/bash

# Run the Bolt.diy Streaming Demo

echo "🚀 Bolt.diy Streaming Architecture Demo"
echo "======================================"
echo ""
echo "This demo shows how:"
echo "1. AI responses are streamed chunk by chunk"
echo "2. Parser detects bolt actions in real-time"
echo "3. Files are created and updated live"
echo "4. Commands are executed in sequence"
echo ""
echo "Press Enter to start the demo..."
read

# Make sure Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Run the demo
python3 streaming_demo.py

echo ""
echo "✅ Demo complete!"
echo ""
echo "To understand the architecture better, check out:"
echo "- STREAMING_ARCHITECTURE.md: Detailed documentation"
echo "- STREAMING_FLOW_DIAGRAM.md: Visual flow diagrams"
echo "- streaming_demo.py: Python implementation"