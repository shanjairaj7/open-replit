# Claude Memory - bolt.diy Project

## Docker Python Library Critical Fix

**Problem:** `http+docker URL scheme error` when using Docker Python library

**Root Cause:** Docker version 6.1.3 is **BROKEN** - causes URL parsing errors with Ubuntu/Python combinations

**Solution:** Use Docker version 7.1.0 instead

### Working Setup Requirements:
- **OS:** Ubuntu 22.04 LTS (stable, not development versions like 25.04)
- **Python:** 3.10.12 (stable LTS version)
- **Docker version:** `docker==7.1.0` (NOT 6.1.3)
- **Socket permissions:** `sudo chmod 666 /var/run/docker.sock`
- **Virtual environment:** Fresh venv if corrupted

### Fix Commands:
```bash
# Fix socket permissions
sudo chmod 666 /var/run/docker.sock

# Use correct Docker version
pip install docker==7.1.0

# Test Docker connection
python3 -c "import docker; print(docker.from_env().ping())"
```

### Files Updated:
- `projects-api/vps-requirements.txt`: Changed `docker==6.1.3` to `docker==7.1.0`
- `projects-api/vps-app.py`: Uses `docker.from_env()` with delayed initialization

### Git Sync Setup:
- **Local:** Work from main repository root
- **VPS:** Use SSH clone with proper branch tracking (main, not master)
- **Issue:** Sparse-checkout can cause sync issues - disable if needed

## VPS Configuration

**Current Working VPS:**
- **IP:** 206.189.229.208
- **OS:** Ubuntu 22.04 LTS 
- **Location:** /opt/codebase-platform (projects-api contents)
- **Python:** 3.10.12 in virtual environment

**Previous VPS (deleted):**
- **IP:** 165.22.42.162 (reference only)

## Project Structure

**Monorepo Implementation Status:**
- ✅ Phase 1: Backend boilerplate template created
- 🔄 Phase 2: Project creation logic modification (next)
- ⏳ Phase 3: File CRUD operations for monorepo paths
- ⏳ Phase 4: Dual container management (frontend + backend)
- ⏳ Phase 5: Backend FastAPI server startup logic
- ⏳ Phase 6: Preview URLs and port management

**Current Working:**
- FastAPI VPS server running on port 8000
- Docker containers for frontend preview (3001-3999 ports)
- Git sync between local and VPS working

## Important Reminders

1. **Always use Ubuntu 22.04 LTS** for stability
2. **Never use docker==6.1.3** - it's fundamentally broken
3. **Always fix socket permissions** before testing Docker
4. **Recreate virtual environment** if Docker issues persist
5. **Check git branch sync** (master vs main) for proper updates

## Commands to Remember

**Test Docker connection:**
```bash
python3 -c "import docker; print(docker.from_env().ping())"
```

**VPS Setup:**
```bash
cd /opt/codebase-platform
source venv/bin/activate
python vps-app.py
```

**Git Sync:**
```bash
git pull origin main  # On VPS
git push origin main  # Local
```

## Cloud Storage Migration Project

**Current Implementation:** Local file storage in `/opt/codebase-platform/projects/`

**New Architecture:**
- **Boilerplates**: GitHub repositories (public)
- **File Storage**: Azure Blob Storage
- **Conversation History**: Stored in cloud storage
- **Frontend**: Webcontainer receives files via streaming/API sync
- **Backend**: Direct cloud storage integration

**Key Changes:**
1. Move boilerplates to GitHub repos, clone per project
2. All files (frontend/backend) stored persistently in Azure
3. Conversation history migrated to cloud storage
4. Terminal commands: frontend interrupts → webcontainer execution → action_result → continue conversation
5. Backend terminal commands: placeholder responses (VPS prep)

## Prompt Engineering Principles

### Identity-Based Instructions > Technical Instructions

**Key Discovery:** AI models respond much better to identity/personality-based rules than detailed technical checklists.

**Effective Pattern (Identity-Based):**
```
"You are a programming wizard"
"Stay true to yourself - your reputation is at stake"
"You have built countless production-grade applications"
"Feature completion means integration - this is who you are"
```

**Less Effective Pattern (Technical Instructions):**
```
"Create API client functions for login/signup/logout"
"Implement token storage and management"
"Add authentication headers to all API calls"
```

**Why This Works:**
- **Identity** = Internal motivation and standards
- **Technical steps** = Just checklist items to complete
- Models internalize identity much more deeply than procedural steps
- Creates a "master developer persona" that naturally wants fully integrated apps

**Application:** When fixing behavior issues, redefine what success means to the model's identity rather than adding more technical instructions.