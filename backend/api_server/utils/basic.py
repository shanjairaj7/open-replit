"""
Utility functions shared across the API server
"""
import os
from openai import OpenAI
from datetime import datetime

async def enhance_user_message(message: str):
    """
    Enhances user's vague requests into proper structured messages with clear features
    and requirements, making them more actionable for development.

    Args:
        message: User's natural language request that may be vague or incomplete

    Returns:
        Enhanced message with clearer structure, features, and requirements
    """
    # Use same OpenRouter setup as agent_class.py
    api_key = os.environ.get('OPENAI_KEY', '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')
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={"x-include-usage": 'true'}
    )

    # Simple system prompt for message enhancement
    enhancement_system_prompt = """You are a message enhancement assistant. Your job is to take the user's vague or incomplete request and transform it into a clear, well-structured message that specifies:

1. What exactly they want to build or modify
2. Key features and functionality they need
3. Any specific requirements or preferences
4. Clear structure and organization of their request

Transform vague requests like "build me an app" into specific requests like "Build me a task management app where I can create, edit, and delete tasks, organize them by priority, and track completion status."

Keep the enhanced message concise but comprehensive. Don't add unnecessary complexity - just clarify what they actually want."""

    # Remove await since OpenAI client is sync
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash",  # Use a model that works with OpenRouter
        messages=[
            {"role": "system", "content": enhancement_system_prompt},
            {"role": "user", "content": message}
        ],
        temperature=0.3,  # Lower temperature for more consistent enhancement
        max_tokens=2000  # Reduced since we just want enhanced message, not full plans
    )

    return response.choices[0].message.content

def generate_short_app_name(project_id: str) -> str:
    """Generate a short, Modal-compliant app name from project ID

    Handles various project ID formats:
    - horizon-702-b1597 -> horizon_702_dbd25209
    - emergency-really-nice-project-management-app -> emergency_dbd25209
    - simple-todo-app -> simple_dbd25209

    Args:
        project_id: The project identifier

    Returns:
        Modal-compliant app name under 40 characters
    """
    import hashlib
    import re

    # Create a deterministic hash from project_id
    hash_obj = hashlib.md5(project_id.encode())
    short_hash = hash_obj.hexdigest()[:8]

    # Extract meaningful parts from project_id
    # Remove common prefixes and suffixes
    clean_id = project_id.replace('emergency-really-nice-project-management-', '')
    clean_id = clean_id.replace('-backend', '')

    # Handle different project ID patterns
    parts = clean_id.split('-')

    if len(parts) >= 2:
        # For IDs like "horizon-702-b1597", use first two parts: "horizon_702"
        # For longer IDs, use first part only to avoid length issues
        if len(clean_id) <= 20:
            meaningful_part = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else parts[0]
        else:
            meaningful_part = parts[0]
    else:
        meaningful_part = parts[0] if parts else 'app'

    # Limit meaningful part to reasonable length
    meaningful_part = meaningful_part[:15]  # Reduced to leave room for hash

    # Create short app name: meaningful_part + hash
    short_name = f"{meaningful_part}_{short_hash}"

    # Ensure Modal compliance
    short_name = re.sub(r'[^a-zA-Z0-9._-]', '_', short_name)
    short_name = re.sub(r'[-_]+', '_', short_name)
    short_name = short_name.strip('-_')

    # Ensure it's under 40 characters for safety
    short_name = short_name[:39]

    return short_name
