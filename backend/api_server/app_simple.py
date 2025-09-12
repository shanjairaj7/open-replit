"""
Simple FastAPI test app to verify Azure deployment works
"""
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Horizon API Server Test", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Horizon API Server deployed successfully on Azure!",
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        "environment": "Azure App Service"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint working!", "data": [1, 2, 3, 4, 5]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app_simple:app", host="0.0.0.0", port=port)