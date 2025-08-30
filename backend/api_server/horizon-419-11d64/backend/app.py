*** Begin Patch
*** Update File: backend/app.py
@@ -78,9 +78,6 @@
     from fastapi import FastAPI
     from fastapi.middleware.cors import CORSMiddleware
     from routes import api_router  # Import auto-discovery router registry
-    from json_db import initialize_json_databases
-
-    # Initialize JSON databases AFTER volume is mounted
-    print("🗄️ Initializing JSON databases...")
-    initialize_json_databases()
     
     # Create FastAPI app with dynamic configuration
     app = FastAPI(
*** End Patch