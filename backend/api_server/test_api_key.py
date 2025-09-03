#!/usr/bin/env python3
"""
Test if the OpenRouter API key works
"""
import requests

api_key = "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"

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "google/gemini-2.0-flash-exp",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "max_tokens": 10
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")