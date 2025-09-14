# Bolt.DIY Clean Codebase Structure

## Essential Files Only

### Core System Files

```
bolt.diy/
├── README.md                       # Project overview
├── ARCHITECTURE.md                 # System architecture documentation
├── SETUP_GUIDE.md                  # Setup instructions
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
│
├── backend/
│   ├── api_server/                # Main API server
│   │   ├── app.py                 # Main FastAPI application (ESSENTIAL)
│   │   ├── streaming_api.py       # WebSocket streaming handler (ESSENTIAL)
│   │   ├── agent.py               # Main LLM agent (ESSENTIAL)
│   │   ├── agent_class.py         # LLM agent logic (ESSENTIAL)
│   │   ├── cloud_storage.py       # Azure storage integration (ESSENTIAL)
│   │   ├── vm_api.py              # VM terminal API client (ESSENTIAL)
│   │   ├── shared_models.py       # Shared data models (ESSENTIAL)
│   │   ├── tools.py               # Tool operations (ESSENTIAL)
│   │   ├── diff_parser.py         # File diff handling (ESSENTIAL)
│   │   ├── update_file_handler.py # File update logic (ESSENTIAL)
│   │   ├── project_pool_manager.py# Project allocation (ESSENTIAL)
│   │   ├── starter_kits.py        # Starter kit management (ESSENTIAL)
│   │   ├── requirements.txt       # Python dependencies (ESSENTIAL)
│   │   │
│   │   ├── prompts/               # LLM prompts
│   │   │   └── simpler_prompt.py  # Main prompt (ESSENTIAL)
│   │   │
│   │   ├── plans/                 # Planning documents (ESSENTIAL)
│   │   │   └── *.md               # Implementation plans
│   │   │
│   │   ├── api/                   # Deployment APIs
│   │   │   ├── netlify_deployment.py
│   │   │   ├── vercel_deployment.py
│   │   │   └── cloudflare_deployment.py
│   │   │
│   │   └── utils/                 # Utility functions
│   │       └── basic.py
│   │
│   ├── backend-boilerplate-clone/ # Backend template (ESSENTIAL)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── routes/
│   │
│   └── frontend-boilerplate-clone/# Frontend template (ESSENTIAL)
│       ├── src/
│       ├── package.json
│       └── index.html
│
├── frontend/                       # React frontend (OPTIONAL - for development)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
└── vm-api/                        # VM terminal API (DEPLOY ON VM)
    ├── vm_api.py
    └── requirements.txt
```

## Files to Remove (Not Essential)

### Test and Debug Files
- `test_*.py` files (test_netlify.py, test_syntax.py, etc.)
- `reproduce_corruption_bug.py`
- `analyze_*.py` files
- `setup_sample_docs.py`
- `conversation_history_converter.py`

### Backup and Duplicate Files
- `app_backup.py`
- `app_simple.py`
- `azure_app.py`
- `modal_app_original.py`
- `streaming_api_backup.py`

### Old and Deprecated
- `old_files/` directory
- `prompts_consolidated/` (old versions)

### Development Tools
- `generate_plan.py`
- `setup_env.py`
- `clear_project_pool.py`
- `upload_*.py` files

## Clean File Organization

### 1. Core API Server (`/backend/api_server/`)
Keep only these essential files:

**Main Application:**
- `app.py` - FastAPI main application
- `streaming_api.py` - WebSocket streaming
- `requirements.txt` - Dependencies

**Core Logic:**
- `agent.py` - Main LLM agent
- `agent_class.py` - LLM agent classes
- `shared_models.py` - Data models
- `tools.py` - Tool operations

**File Operations:**
- `cloud_storage.py` - Azure storage
- `vm_api.py` - VM terminal client
- `diff_parser.py` - Diff handling
- `update_file_handler.py` - File updates

**Project Management:**
- `project_pool_manager.py` - Project allocation
- `starter_kits.py` - Starter kits

**Prompts:**
- `prompts/simpler_prompt.py` - Main prompt

**Deployment APIs:**
- `api/netlify_deployment.py`
- `api/vercel_deployment.py`
- `api/cloudflare_deployment.py`

### 2. Boilerplate Templates (`/backend/`)
**Keep these directories intact:**
- `backend-boilerplate-clone/` - Backend template
- `frontend-boilerplate-clone/` - Frontend template

### 3. VM API (`/vm-api/`)
**Deploy this on your VM:**
- `vm_api.py` - Terminal API server
- `requirements.txt` - Dependencies

## Cleanup Commands

To clean up the codebase, run these commands:

```bash
# Remove test files
find . -name "test_*.py" -delete
find . -name "*_test.py" -delete

# Remove backup files
find . -name "*_backup.*" -delete
find . -name "*_original.*" -delete

# Remove analysis files
find . -name "analyze_*.py" -delete

# Remove old directories
rm -rf backend/api_server/old_files/
rm -rf backend/api_server/prompts_consolidated/
# Keep plans/ directory - it contains important documentation

# Remove development tools
rm -f backend/api_server/setup_env.py
rm -f backend/api_server/generate_plan.py
rm -f backend/api_server/upload_*.py
rm -f backend/api_server/clear_project_pool.py

# Remove duplicate app files
rm -f backend/api_server/app_backup.py
rm -f backend/api_server/app_simple.py
rm -f backend/api_server/azure_app.py
rm -f backend/api_server/modal_app_original.py
```

## Essential Configuration Files

### `.env` (Create from .env.example)
```env
# Minimum required variables
OPENROUTER_API_KEY=your_key
AZURE_STORAGE_CONNECTION_STRING=your_connection
VM_API_BASE_URL=http://your-vm:8000
```

### `requirements.txt` (Backend)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
aiohttp==3.9.0
azure-storage-blob==12.19.0
pydantic==2.5.0
openai
groq
```

### `package.json` (Frontend)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "axios": "^1.6.0",
    "socket.io-client": "^4.5.0"
  }
}
```

## Directory Purpose Summary

| Directory | Purpose | Required |
|-----------|---------|----------|
| `/backend/api_server/` | Main API server | ✅ Essential |
| `/backend/backend-boilerplate-clone/` | Backend template | ✅ Essential |
| `/backend/frontend-boilerplate-clone/` | Frontend template | ✅ Essential |
| `/vm-api/` | Terminal execution | ✅ Essential (on VM) |
| `/frontend/` | Development UI | ⚠️ Optional |
| `/plans/` | Documentation | ❌ Remove |
| `/old_files/` | Deprecated code | ❌ Remove |

## Final Clean Structure

After cleanup, your structure should be:

```
bolt.diy/
├── backend/
│   ├── api_server/
│   │   ├── Core files (10-15 files)
│   │   ├── prompts/
│   │   ├── api/
│   │   └── utils/
│   ├── backend-boilerplate-clone/
│   └── frontend-boilerplate-clone/
├── vm-api/
├── Documentation (3-4 files)
└── Config files (2-3 files)
```

Total essential files: ~30-40 files (down from 100+)