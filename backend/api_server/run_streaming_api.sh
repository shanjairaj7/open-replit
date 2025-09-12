#!/bin/bash
# Sustainable streaming API runner that uses correct Python environment

echo "🚀 Starting Streaming API with correct Python environment..."
echo "🐍 Using: $(./venv/bin/python --version)"
echo "📦 Pydantic: $(./venv/bin/python -c 'import pydantic; print(pydantic.VERSION)')"
echo ""

# Run streaming API with the correct Python from venv
./venv/bin/python streaming_api.py