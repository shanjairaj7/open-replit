# Railway Deployment Guide

## Quick Setup

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   # or
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Initialize and Deploy**:
   ```bash
   railway link
   railway up
   ```

## Files Created for Railway

- `Procfile`: Defines how to start the application
- `railway.toml`: Railway-specific configuration
- `runtime.txt`: Python version specification
- `/health` endpoint added to app.py for health checks

## Environment Variables

Set these in the Railway dashboard under Variables:

- `GROQ_API_KEY`: Your Groq API key
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI features)
- `AZURE_STORAGE_CONNECTION_STRING`: For cloud storage (if using)

## Post-deployment

Your API will be available at: https://your-app-name.up.railway.app

Test endpoints:
- `/health` - Health check
- `/` - API status
- `/docs` - FastAPI documentation

## Troubleshooting

If build fails, check logs with:
```bash
railway logs
```

Common issues:
- Missing environment variables
- Python version conflicts (specified in runtime.txt)
- Port binding (handled automatically by Railway)