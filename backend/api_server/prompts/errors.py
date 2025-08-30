"""
Critical Error Prevention Guidelines
Based on real project failures - actionable guidance to prevent common mistakes
"""

common_errors = [
    # Import Management - CRITICAL FOR MODAL DEPLOYMENT
    "Modal deployment import pattern: Import from project root WITHOUT 'backend' prefix. Modal copies backend/ code to /root/ and treats it as import root. Use 'from models import User', NOT 'from backend.models import User' which causes 'No module named backend' errors",
    "Use absolute imports only (from models.user import User) NEVER relative imports (from ..models import User) as relative imports fail when project structure changes or in deployment environments",

    # JSON Database Management
    "Initialize all entity JSON files in app.py startup to ensure database tables exist before operations",
    "Use consistent data structure across all JSON files with 'id' field to prevent data inconsistencies",
    "Wrap all JSON operations in try/except blocks to handle file read/write errors gracefully",
    "Implement proper unique ID management with get_next_id() function for each entity to prevent duplicate records",
    "Read entire file, modify in memory, write back atomically to prevent concurrent access issues and data corruption",

    # Modal.com Deployment - MOST COMMON DEPLOYMENT FAILURES  
    "Create the initialize_json_databases() function yourself - it does NOT exist in json_db.py, you must define it in app.py",
    "Call initialize_json_databases() INSIDE @modal.asgi_app() function only, NEVER at module level - module-level code runs during build but /root/json_data volume only exists after Modal container starts",
    "Use create_tables(table_names) from json_db.py with a list of your app's table names like ['users', 'todos', 'projects'] to initialize empty JSON files",
    "Use Path('/root/json_data') paths automatically handled by json_db.py - never hardcode paths as Modal mounts persistent volumes at specific locations",
    "Always read existing app.py first, then UPDATE by adding only JSON initialization to preserve existing Modal configuration and avoid breaking deployment",
    "Preserve all existing Modal app definitions, volume mounts, and secrets - only ADD your initialize_json_databases() function and call",

    # User Communication
    "Always refer to 'database', 'data storage', 'backend persistence' when discussing data to maintain professional abstraction and never reveal JSON file implementation details",

    # API Integration
    "Check HTTP status codes (200, 201, 400, 500) to determine API call success instead of checking non-existent properties",
    "Use 'sonner' for all notifications and error messages as the toast component is deprecated",
    "Implement proper error boundaries and user feedback with try-catch blocks around all API calls",

    # Authentication Logic
    "Ensure consistent authentication fields across schemas and JSON structure (use email, not username) to prevent login failures",
    "Implement protected routes that redirect unauthenticated users to login page for proper security flow",

    # Frontend State Management
    "Store all application data in Zustand with proper handlers to maintain centralized state management",
    "Connect all API calls through Zustand actions instead of making direct API calls for consistent state updates",

    # UI/UX Quality
    "Build complete, production-ready UI with realistic data and finishing touches to avoid empty, unfinished appearance",
    "Create custom design system with professional appearance instead of using generic, basic styling",

    # Pydantic Compatibility
    "Use 'pattern' parameter instead of 'regex' for Pydantic v2+ compatibility as the regex keyword was removed",

    # Boilerplate Transformation
    "Transform home page to immediately show the requested app functionality so users see their working app immediately",
    "Update navigation to show only pages relevant to the specific app being built for coherent user experience",
    "Comment out or hide authentication pages when auth is not required for the specific app to streamline user flow",
    "Make the entire user experience coherent for the specific app type being built",

    # V4A Diff Format
    "Always wrap all V4A diffs in action tags to prevent the V4A patch bug where raw patch content gets written to files as literal text instead of being applied as code changes"
]
