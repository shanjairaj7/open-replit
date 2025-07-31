#!/bin/bash

# Vite wrapper script to handle crypto issues
# This script sets up the environment properly for Vite

PROJECT_PATH=$1
PORT=$2

cd "$PROJECT_PATH"

# Fix for crypto.hash issue - use older Node crypto
export NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=512"

# Try with Vite 5 first (more stable)
if [ -f "node_modules/.bin/vite" ]; then
    # Check Vite version
    VITE_VERSION=$(node -p "require('./package.json').devDependencies.vite || require('./package.json').dependencies.vite || 'unknown'")
    echo "Starting Vite $VITE_VERSION on port $PORT..."
    
    # If Vite 7+, downgrade to 5
    if [[ $VITE_VERSION == *"^7"* ]] || [[ $VITE_VERSION == *"~7"* ]]; then
        echo "Downgrading Vite to v5 for stability..."
        npm install vite@^5.4.0 --save-dev --force
    fi
fi

# Start Vite
exec npx vite --host 0.0.0.0 --port "$PORT" --strictPort