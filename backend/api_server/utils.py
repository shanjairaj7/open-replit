"""
Utility functions shared across the API server
"""
import os
from openai import OpenAI
from datetime import datetime
from prompts.planning_prompt import planning_prompt

async def generate_user_message_plan(message: str):
    """
    Translates user's natural language request into a structured implementation plan
    following the system's development methodology and rules.

    Args:
        message: User's natural language request for building an application

    Returns:
        Structured plan as a string with feature selection, architecture, and implementation steps
    """
    # Use same OpenRouter setup as agent_class.py
    api_key = os.environ.get('OPENAI_KEY', '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')
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={"x-include-usage": 'true'}
    )

    # Use the planning prompt that generates first-person plans
    planning_system_prompt = planning_prompt

    # Remove await since OpenAI client is sync
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash",  # Use a model that works with OpenRouter
        messages=[
            {"role": "system", "content": planning_system_prompt},
            {"role": "user", "content": message}
        ],
        temperature=0.3,  # Lower temperature for more consistent planning
        max_tokens=15000
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
