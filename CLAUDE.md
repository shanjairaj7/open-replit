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