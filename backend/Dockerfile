# Boilerplate System Dockerfile
FROM node:20-alpine AS base

# Install Python and system dependencies
RUN apk add --no-cache python3 py3-pip python3-dev build-base git curl

# Create working directory
WORKDIR /app

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies (override external management for Docker)
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/workspace /app/projects

# Copy boilerplate template
COPY boilerplate/ /app/boilerplate/

# Copy FastAPI application and existing Python scripts
COPY app/ /app/app/
COPY *.py /app/

# Set working directory
WORKDIR /app

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Command to run the FastAPI application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
