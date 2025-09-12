# Sustainable Dependency Management

## Problem Solved
This system prevents Python version compatibility issues that were causing:
- `ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'`
- `module 'certifi' has no attribute 'where'`
- FastAPI/Pydantic import failures
- Modal deployment failures

## Solution Architecture

### 1. Version Detection & Compatibility
- **`setup_env.py`** automatically detects Python version and chooses compatible dependencies
- **Python 3.13** → uses `requirements-python313-compatible.txt`
- **Python 3.11/3.12** → uses standard `requirements.txt`

### 2. Locked Dependencies
All requirements files now use **exact version pinning** to prevent unexpected updates:

```
# Instead of: pydantic>=2.0.0
# We use: pydantic==2.10.6
```

### 3. Critical Version Locks

#### Python 3.13 Compatible Stack
- **FastAPI**: 0.115.4 (has Python 3.13 support)
- **Pydantic**: 2.10.6 (fixes ForwardRef._evaluate issues)
- **Certifi**: 2024.8.30 (has .where() function)
- **Modal**: >=1.1.4 (latest with 3.13 support)

#### Python 3.11/3.12 Compatible Stack
- **FastAPI**: 0.104.1 (stable)
- **Pydantic**: 2.5.0 (stable)
- **Certifi**: 2024.8.30 (consistent across versions)

## Usage

### Quick Setup (Recommended)
```bash
cd /path/to/backend/api_server
python3 setup_env.py
source venv/bin/activate
```

### Manual Setup
```bash
# For Python 3.13
pip install -r requirements-python313-compatible.txt

# For Python 3.11/3.12  
pip install -r requirements.txt
```

### Verification
```bash
# Test imports work
python -c "import fastapi, pydantic; print('✅ All working')"

# Test streaming API
python streaming_api.py

# Test Modal deployment
python test_start_backend.py
```

## Boilerplate Consistency

Updated all requirement files to maintain consistency:
- `/backend/api_server/requirements.txt`
- `/backend/api_server/requirements-python313-compatible.txt`  
- `/backend-boilerplate-clone/requirements.txt`

## Future-Proofing

### When Adding New Dependencies
1. **Pin exact versions**: `package==1.2.3`
2. **Test on Python 3.13**: Run `setup_env.py` to verify
3. **Update all requirement files** to maintain consistency
4. **Test critical workflows**: FastAPI imports, Modal deployment

### When Python 3.14+ is Released
1. Create new `requirements-python314-compatible.txt`
2. Update `setup_env.py` detection logic
3. Test and pin compatible versions

### Monitoring for Issues
Watch for these patterns that indicate compatibility problems:
- `ForwardRef._evaluate()` errors → Pydantic version issue
- `module 'X' has no attribute 'Y'` → Package version mismatch
- Modal deployment failures → Check requirements.txt in boilerplate

## Emergency Recovery

If dependencies break again:
```bash
# Reset environment completely
rm -rf venv
python3 setup_env.py

# Or use specific Python version
python3.12 setup_env.py
```

## Architecture Benefits

1. **Zero-Config**: `setup_env.py` handles everything automatically
2. **Version Flexible**: Works with Python 3.11, 3.12, and 3.13
3. **Dependency Locked**: Exact versions prevent surprises
4. **Boilerplate Synced**: All deployments use same working versions
5. **Self-Verifying**: Tests critical imports and functions
6. **Future-Ready**: Easy to add new Python version support

This ensures **no more compatibility surprises** and **sustainable long-term development**.