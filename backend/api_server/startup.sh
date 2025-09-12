#!/bin/bash
echo "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "Starting application..."
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --timeout 600