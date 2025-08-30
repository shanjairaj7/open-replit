"""
Utility functions shared across the API server
"""

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