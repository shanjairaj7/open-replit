# Use Python image with Node.js
FROM python:3.11-slim

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x start.sh vite_wrapper.sh

# Create necessary directories
RUN mkdir -p /tmp/workspace /tmp/projects

# Install lsof for port management
RUN apt-get update && apt-get install -y lsof && rm -rf /var/lib/apt/lists/*

# Expose port
EXPOSE 8000

# Run the application using the start script
ENTRYPOINT ["bash", "start.sh"]