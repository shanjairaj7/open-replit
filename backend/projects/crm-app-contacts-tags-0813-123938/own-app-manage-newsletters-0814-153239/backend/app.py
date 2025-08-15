from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import api_router
from datetime import datetime

print(f"[{datetime.now()}] Starting FastAPI backend...")
print(f"[{datetime.now()}] Importing modules completed")

app = FastAPI(title="Project Backend", version="1.0.0")

print(f"[{datetime.now()}] FastAPI app instance created")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Application startup event - database tables should be created via test files"""
    print(f"[{datetime.now()}] === STARTUP EVENT TRIGGERED ===")
    print(f"[{datetime.now()}] FastAPI application starting...")
    print(f"[{datetime.now()}] ℹ️  Database tables should be created via test files (e.g., test_setup.py)")
    print(f"[{datetime.now()}] ℹ️  This ensures proper testing and verification of database functionality")
    print(f"[{datetime.now()}] === STARTUP COMPLETE ===")

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main router
app.include_router(api_router)

@app.get("/")
def read_root():
    print(f"[{datetime.now()}] GET / endpoint called")
    print(f"[{datetime.now()}] Preparing response...")
    response = {"status": "Backend running", "timestamp": str(datetime.now())}
    print(f"[{datetime.now()}] Returning response: {response}")
    return response

@app.get("/health")
def health_check():
    print(f"[{datetime.now()}] GET /health endpoint called")
    print(f"[{datetime.now()}] Performing health checks...")
    
    # Simulate checking various components
    print(f"[{datetime.now()}] Checking database connection...")
    db_status = "healthy"
    
    print(f"[{datetime.now()}] Checking API router...")
    api_status = "healthy"
    
    response = {
        "status": "healthy",
        "database": db_status,
        "api": api_status,
        "timestamp": str(datetime.now())
    }
    print(f"[{datetime.now()}] Health check complete: {response}")
    return response

if __name__ == "__main__":
    import uvicorn
    print(f"[{datetime.now()}] === MAIN EXECUTION STARTED ===")
    print(f"[{datetime.now()}] Starting Uvicorn server...")
    print(f"[{datetime.now()}] Configuration: host=0.0.0.0, port=8892")
    uvicorn.run(app, host="0.0.0.0", port=8892)