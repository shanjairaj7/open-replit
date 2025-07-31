# FastAPI Backend Integration Guide

This guide explains how to set up and use the new FastAPI backend with the existing bolt.diy frontend.

## What Was Done

The frontend has been updated to **optionally** use a FastAPI backend instead of the internal Remix API routes. This allows for:

1. **Zero functionality change** - All features work exactly the same
2. **Developer choice** - Easy switching between Remix routes and FastAPI backend
3. **Gradual migration** - Can test the backend without breaking existing functionality

## Setup Instructions

### 1. Start the FastAPI Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python run.py
```

The FastAPI backend will be available at `http://localhost:8000`

### 2. Switch Frontend to Use FastAPI Backend

When you run the frontend (`npm run dev`), you'll see a **Backend Switcher** component in the bottom-right corner.

**To enable FastAPI backend:**
1. Make sure the FastAPI server is running (step 1)
2. Click the toggle switch to change from "Remix" to "FastAPI"
3. The page will reload and start using the FastAPI backend

**To go back to Remix:**
1. Click the toggle switch to change from "FastAPI" to "Remix"  
2. The page will reload and use the original Remix API routes

### 3. Test the Integration

**Test basic functionality:**
1. Try asking the AI a question - it should work identically
2. Check that model selection works
3. Verify streaming responses work
4. Test different AI providers (OpenAI, Anthropic, etc.)

**Check the backend status:**
- The switcher shows a colored dot indicating backend status (green = online, red = offline)
- Click "Check" to test the connection to the FastAPI backend

## How It Works

### Configuration System

The integration uses a configuration system (`app/lib/config/api.ts`) that:

- **Detects environment** - Only shows switcher in development (localhost)
- **Routes API calls** - Directs calls to either Remix routes or FastAPI backend
- **Handles API keys** - Automatically passes API keys from cookies to FastAPI headers
- **Provides fallback** - Falls back to Remix routes if FastAPI is unavailable

### API Call Routing

**Original (Remix internal):**
```typescript
fetch('/api/chat', { ... })
```

**New (configurable):**
```typescript
fetch(getApiUrl('/api/chat'), {
  headers: getApiHeaders(),
  ...
})
```

The `getApiUrl()` function returns:
- `http://localhost:8000/api/chat` when using FastAPI backend
- `/api/chat` when using Remix routes

### API Key Handling

API keys are automatically extracted from cookies and passed as headers to the FastAPI backend:
- `x-openai-api-key`
- `x-anthropic-api-key`
- `x-google-api-key`

## What's Different

### Identical Functionality
- ✅ All chat features work the same
- ✅ Model selection works the same
- ✅ Streaming responses work the same
- ✅ API key management works the same
- ✅ All AI providers work the same

### Development Experience
- 🔧 Backend switcher for easy testing
- 🔧 Backend status indicator
- 🔧 Automatic API key forwarding
- 🔧 Fallback to Remix if FastAPI is down

## FastAPI Endpoints

The FastAPI backend provides these endpoints:

### Core Endpoints
- `GET /` - Service information
- `GET /api/health` - Health check
- `GET /api/models` - Get available AI models and providers
- `GET /api/models/{provider}` - Get models for specific provider
- `POST /api/chat` - Main chat endpoint with streaming
- `POST /api/chat/simple` - Simple non-streaming chat for testing

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing Examples

### Test FastAPI Backend Directly

```bash
# Health check
curl http://localhost:8000/api/health

# Get models
curl http://localhost:8000/api/models

# Simple chat (replace YOUR_API_KEY)
curl -X POST http://localhost:8000/api/chat/simple \
  -H "Content-Type: application/json" \
  -H "x-openai-api-key: YOUR_API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "gpt-3.5-turbo"
  }'
```

### Test Frontend Integration

1. **Start both servers:**
   ```bash
   # Terminal 1: Frontend
   npm run dev
   
   # Terminal 2: Backend  
   cd backend && python run.py
   ```

2. **Open frontend:** http://localhost:5173

3. **Switch to FastAPI backend** using the toggle in bottom-right

4. **Test chat functionality** - should work identically to Remix mode

## Troubleshooting

### Backend Switcher Not Visible
- Only shows on localhost (development)
- Make sure you're accessing the frontend via localhost, not 127.0.0.1

### FastAPI Backend Shows Offline
- Check that `python run.py` is running in the backend directory
- Verify no other service is using port 8000
- Check backend logs for errors

### API Key Errors
- Ensure API keys are set in the frontend (same as before)
- Check browser console for API key extraction errors
- Verify API keys are being sent as headers in network tab

### CORS Errors
- FastAPI backend has CORS enabled for localhost
- If running on different ports, update CORS settings in `backend/app/main.py`

### Chat Not Working with FastAPI
- Check network tab to see if requests are going to `http://localhost:8000/api/chat`
- Verify FastAPI backend logs show incoming requests
- Check if API keys are being passed correctly in headers

## Next Steps

This integration provides the foundation for:

1. **Container management** - Adding Docker container orchestration
2. **File system API** - File operations in cloud containers  
3. **WebSocket services** - Real-time terminal and file sync
4. **Authentication** - User management and project isolation

The FastAPI backend is ready to be extended with cloud infrastructure while maintaining identical frontend functionality.