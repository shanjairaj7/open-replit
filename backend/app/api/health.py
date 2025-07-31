from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
@router.head("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint - replaces api.health.ts"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bolt-backend-api",
        "version": "1.0.0"
    }