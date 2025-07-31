#!/bin/bash

# Create necessary directories
mkdir -p /tmp/workspace
mkdir -p /tmp/projects

# Set the port from environment variable, default to 8000
PORT=${PORT:-8000}

# Start the FastAPI application
exec uvicorn app:app --host 0.0.0.0 --port $PORT