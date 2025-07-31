"""
Lambda handler for FastAPI projects API
"""
from mangum import Mangum
from main_lambda import app

# Lambda handler
handler = Mangum(app, lifespan="off")