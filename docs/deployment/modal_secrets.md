# Modal.com Secrets Setup for horizon-api

## Required Secrets

### 1. azure-storage-secret
```
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=functionalaistorage;AccountKey=35N7QOp+WIphG9CD9zdtmd9N15tZRJ7NID4i6CHLxP4a09FTBzU/9hHOrnCjJFWtIj+how8vArIZ+AStLA1RVA==;BlobEndpoint=https://functionalaistorage.blob.core.windows.net/;FileEndpoint=https://functionalaistorage.file.core.windows.net/;QueueEndpoint=https://functionalaistorage.queue.core.windows.net/;TableEndpoint=https://functionalaistorage.table.core.windows.net/"
```

### 2. openai-secret
```
GROQ_API_KEY = "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"
```

## Modal Authentication Credentials
```
[shanjairajdev]
token_id = "ak-wETXcFyV2y37sVGVQRkSsN"
token_secret = "as-2g1lHHDePkY90L7sz4wtuY"
active = true
```

## Setup Instructions

1. **Install Modal CLI:**
   ```bash
   pip install modal
   ```

2. **Authenticate with Modal:**
   ```bash
   modal token set
   ```
   Use the credentials above when prompted.

3. **Create secrets in Modal dashboard:**
   - Go to https://modal.com/secrets
   - Create `azure-storage-secret` with Azure connection string
   - Create `openai-secret` with GROQ API key

4. **Deploy the API:**
   ```bash
   python deploy_modal.py
   ```
   OR
   ```bash
   modal deploy streaming_api.py
   ```

## Expected Modal URL
After deployment, your API will be available at:
`https://shanjairajdev--horizon-api-fastapi-app.modal.run`

## Endpoints
- `POST /chat/stream` - Main streaming chat
- `GET /` - Health check 
- `GET /pool/status` - Project pool status
- `GET /conversations` - List conversations
- `GET /projects/{id}/history/streaming-format` - Get conversation history