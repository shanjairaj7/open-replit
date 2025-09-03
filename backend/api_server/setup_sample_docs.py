#!/usr/bin/env python3
"""
Setup sample documentation files in Azure Storage for testing
"""

from cloud_storage import AzureBlobStorage

def create_sample_docs():
    """Create sample documentation files"""
    print("📚 Setting up sample documentation files...")
    
    storage = AzureBlobStorage()
    
    # Sample API Reference
    api_doc = """# API Reference

## Authentication
All API requests require authentication using Bearer tokens.

### Login Endpoint
- **POST** `/api/auth/login`
- **Body**: `{"email": "user@example.com", "password": "password"}`
- **Response**: `{"token": "bearer_token_here", "expires": "2024-12-31T23:59:59Z"}`

### Protected Routes
Include the Bearer token in the Authorization header:
```
Authorization: Bearer your_token_here
```

## User Management
- **GET** `/api/users` - List all users
- **POST** `/api/users` - Create new user
- **PUT** `/api/users/:id` - Update user
- **DELETE** `/api/users/:id` - Delete user

## Project Management
- **GET** `/api/projects` - List projects
- **POST** `/api/projects` - Create project
- **PUT** `/api/projects/:id` - Update project
- **DELETE** `/api/projects/:id` - Delete project
"""
    
    # Sample Deployment Guide
    deployment_doc = """# Deployment Guide

## Prerequisites
- Docker installed
- Azure CLI configured
- Node.js 18+ for frontend
- Python 3.11+ for backend

## Backend Deployment
1. Build Docker image:
   ```bash
   docker build -t codebase-backend .
   ```

2. Run with environment variables:
   ```bash
   docker run -p 8000:8000 \
     -e AZURE_STORAGE_CONNECTION_STRING="your_connection" \
     codebase-backend
   ```

## Frontend Deployment
1. Install dependencies:
   ```bash
   npm install
   ```

2. Build for production:
   ```bash
   npm run build
   ```

3. Serve static files:
   ```bash
   npm run preview
   ```

## Environment Variables
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage connection
- `OPENAI_API_KEY` - OpenAI API key for AI features
- `JWT_SECRET` - Secret for JWT token signing
"""

    # Sample Authentication Guide
    auth_doc = """# Authentication Guide

## Overview
The platform uses JWT (JSON Web Tokens) for authentication and authorization.

## User Registration
1. User submits registration form
2. Backend validates email format and password strength
3. User account created with `pending` status
4. Email verification sent (optional)

## Login Process
1. User provides email and password
2. Backend verifies credentials
3. JWT token generated with user info
4. Token returned to client with expiration

## Token Structure
```json
{
  "user_id": "uuid",
  "email": "user@example.com", 
  "role": "user",
  "exp": 1735689599,
  "iat": 1703239599
}
```

## Security Best Practices
- Tokens expire after 24 hours
- Use HTTPS in production
- Store tokens securely (httpOnly cookies recommended)
- Implement refresh token mechanism for long sessions

## Role-Based Access
- `admin` - Full system access
- `user` - Limited to own projects
- `viewer` - Read-only access
"""

    # Sample Troubleshooting Guide  
    troubleshooting_doc = """# Troubleshooting Guide

## Common Issues

### Backend Won't Start
**Symptoms**: Server crashes on startup
**Solutions**:
1. Check environment variables are set
2. Verify Azure Storage connection string
3. Ensure Python dependencies installed: `pip install -r requirements.txt`
4. Check port 8000 is not in use: `lsof -i :8000`

### Frontend Build Errors
**Symptoms**: `npm run build` fails
**Solutions**:
1. Clear node_modules: `rm -rf node_modules && npm install`
2. Update dependencies: `npm update`
3. Check TypeScript errors: `npm run type-check`
4. Verify all imports are valid

### Authentication Issues
**Symptoms**: Login returns 401 errors
**Solutions**:
1. Verify JWT_SECRET environment variable
2. Check user credentials in database
3. Confirm token expiration settings
4. Test with curl: `curl -X POST /api/auth/login -d '{"email":"test@example.com","password":"password"}'`

### File Upload Problems
**Symptoms**: Files not saving to Azure Storage
**Solutions**:
1. Check Azure Storage connection string
2. Verify container permissions
3. Test connectivity: `az storage blob list`
4. Check file size limits (max 100MB)

### Performance Issues
**Symptoms**: Slow API responses
**Solutions**:
1. Enable query logging to identify slow database queries
2. Check Azure Storage region (use same region as compute)
3. Implement caching for frequently accessed data
4. Monitor memory usage: `htop` or `ps aux`

## Getting Help
- Check application logs: `docker logs container_name`
- Enable debug mode: Set `DEBUG=true`
- Contact support with error logs and reproduction steps
"""

    # Upload all docs
    docs = {
        "api_reference.md": api_doc,
        "deployment_guide.md": deployment_doc, 
        "authentication_guide.md": auth_doc,
        "troubleshooting.md": troubleshooting_doc
    }
    
    for doc_name, content in docs.items():
        try:
            blob_client = storage.docs_container_client.get_blob_client(doc_name)
            blob_client.upload_blob(content.encode('utf-8'), overwrite=True)
            print(f"✅ Uploaded: {doc_name} ({len(content)} chars)")
        except Exception as e:
            print(f"❌ Failed to upload {doc_name}: {e}")
    
    print(f"\n🎉 Successfully set up {len(docs)} sample documentation files!")
    return True

if __name__ == "__main__":
    create_sample_docs()