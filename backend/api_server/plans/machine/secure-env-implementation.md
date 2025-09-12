# Secure Environment Variables Implementation for LLM Agent Backend

## Problem Statement
Enable LLMs to test code requiring sensitive environment variables (API keys, database credentials) without exposing the actual secret values to the model.

## Core Requirements
1. **Functional**: Code using `os.getenv()` or `process.env` must work with real values
2. **Secure**: LLM must never see actual secret values in any output
3. **Transparent**: No changes required to application code
4. **Isolated**: Each project has its own set of secrets
5. **Auditable**: Track secret usage for security monitoring

## Proposed Architecture

### 1. Secret Storage Layer
```
Azure Key Vault
    └── Project Secrets (encrypted)
         ├── horizon-123/
         │   ├── STRIPE_SECRET_KEY
         │   ├── STRIPE_PUBLISHABLE_KEY
         │   └── DATABASE_URL
         └── horizon-456/
             ├── OPENAI_API_KEY
             └── SENDGRID_API_KEY
```

### 2. Three-Layer Security Model

#### Layer 1: Storage Security
- Secrets stored in Azure Key Vault (or Azure Table Storage with encryption)
- Project-specific secret collections
- Encryption at rest with Azure-managed keys
- Access only via service principal with minimal permissions

#### Layer 2: Runtime Injection
- Secrets loaded into worker process memory (never written to disk)
- Injected as subprocess environment variables
- No .env files created in project directories
- Secrets exist only in process memory during execution

#### Layer 3: Output Sanitization
- All command output passes through sanitization pipeline
- Pattern matching to detect and mask secrets
- Contextual masking (show partial values for debugging)
- Audit logging of sanitization events

## Implementation Details

### Modified Worker Architecture

```python
# worker-secure.py

import os
import re
import json
import subprocess
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from typing import Dict, Optional, Any

class SecureEnvironmentManager:
    def __init__(self, keyvault_url: str):
        credential = DefaultAzureCredential()
        self.secret_client = SecretClient(vault_url=keyvault_url, credential=credential)
        self.secret_cache: Dict[str, Dict[str, str]] = {}
        self.secret_patterns: Dict[str, re.Pattern] = {}
    
    def load_project_secrets(self, project_id: str) -> Dict[str, str]:
        """Load secrets for a project from Key Vault"""
        if project_id in self.secret_cache:
            return self.secret_cache[project_id]
        
        secrets = {}
        secret_prefix = f"{project_id}-"
        
        # List all secrets for this project
        for secret_properties in self.secret_client.list_properties_of_secrets():
            if secret_properties.name.startswith(secret_prefix):
                key_name = secret_properties.name[len(secret_prefix):]
                secret = self.secret_client.get_secret(secret_properties.name)
                secrets[key_name] = secret.value
                
                # Create regex pattern for this secret
                if len(secret.value) > 10:  # Only for substantial secrets
                    # Escape special regex characters
                    escaped_value = re.escape(secret.value)
                    self.secret_patterns[secret.value] = re.compile(escaped_value)
        
        self.secret_cache[project_id] = secrets
        return secrets
    
    def sanitize_output(self, text: str, project_id: str) -> str:
        """Remove or mask secrets from output"""
        if project_id not in self.secret_cache:
            return text
        
        sanitized = text
        secrets = self.secret_cache[project_id]
        
        for key, value in secrets.items():
            if not value or len(value) < 4:
                continue
            
            # Different masking strategies based on secret type
            if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
                # Full mask for highly sensitive values
                mask = f"<{key}_REDACTED>"
            elif 'URL' in key or 'ENDPOINT' in key:
                # Partial mask for URLs (show domain)
                if '://' in value:
                    parts = value.split('://')
                    if len(parts) > 1 and '/' in parts[1]:
                        domain = parts[1].split('/')[0]
                        mask = f"{parts[0]}://{domain}/***REDACTED***"
                    else:
                        mask = f"<{key}_REDACTED>"
                else:
                    mask = f"<{key}_REDACTED>"
            else:
                # Partial mask for other values (show first 4 chars)
                mask = f"{value[:4]}***REDACTED***"
            
            # Replace all occurrences
            sanitized = sanitized.replace(value, mask)
        
        return sanitized

class SecureWorker:
    def __init__(self, env_manager: SecureEnvironmentManager):
        self.env_manager = env_manager
    
    def execute_command(self, project_id: str, command: str, working_dir: Optional[str] = None) -> dict:
        """Execute command with injected secrets and sanitized output"""
        
        # Block direct .env file operations
        blocked_patterns = [
            r'cat\s+.*\.env',
            r'less\s+.*\.env',
            r'more\s+.*\.env',
            r'head\s+.*\.env',
            r'tail\s+.*\.env',
            r'grep\s+.*\.env',
            r'echo\s+.*\$\{.*\}',  # Block echo of env vars
            r'printenv',
            r'env\s*$',  # Block plain env command
            r'set\s*$',  # Block set command that shows env
        ]
        
        for pattern in blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "stdout": "",
                    "stderr": "Security Error: Direct access to environment variables is not allowed",
                    "return_code": 1,
                    "security_blocked": True
                }
        
        # Load secrets for this project
        secrets = self.env_manager.load_project_secrets(project_id)
        
        # Prepare environment with base + secrets
        env = os.environ.copy()
        env.update(secrets)
        
        # Add security notice
        env['ENV_SECURITY_NOTICE'] = 'Environment variables are injected securely and masked in output'
        
        project_path = get_project_working_directory(project_id, working_dir)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=project_path,
                env=env,  # Injected environment
                timeout=300
            )
            
            # Sanitize output before returning
            sanitized_stdout = self.env_manager.sanitize_output(result.stdout, project_id)
            sanitized_stderr = self.env_manager.sanitize_output(result.stderr, project_id)
            
            # Log if sanitization occurred
            if sanitized_stdout != result.stdout or sanitized_stderr != result.stderr:
                print(f"[SECURITY] Sanitized output for project {project_id}")
            
            return {
                "stdout": sanitized_stdout,
                "stderr": sanitized_stderr,
                "return_code": result.returncode,
                "working_directory": project_path,
                "env_injected": True,
                "env_count": len(secrets)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timed out after 5 minutes",
                "return_code": 124,
                "working_directory": project_path
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "return_code": 1,
                "working_directory": project_path
            }
    
    def read_file(self, project_id: str, file_path: str, working_dir: Optional[str] = None) -> dict:
        """Read file with .env blocking"""
        
        # Block reading any .env files
        if '.env' in file_path.lower() or file_path.endswith('env'):
            return {
                "content": "# Environment variables are securely managed and cannot be read directly\n# Use os.getenv() or process.env to access them in your code",
                "error": "Security: Direct access to .env files is not allowed",
                "security_blocked": True
            }
        
        # Continue with normal file read...
        return standard_read_file(project_id, file_path, working_dir)
```

### API Modifications

```python
# In api.py, add secret management endpoint

@app.post("/secrets/set")
async def set_project_secret(req: SetSecretRequest):
    """Set a secret for a project (admin only)"""
    # This would be called by project owner, not LLM
    # Requires authentication
    
    secret_name = f"{req.project_id}-{req.key}"
    secret_client.set_secret(secret_name, req.value)
    
    return {"status": "Secret stored securely"}

@app.post("/secrets/list")
async def list_project_secrets(req: ListSecretsRequest):
    """List secret keys (not values) for a project"""
    # Returns only the keys, never the values
    
    keys = []
    secret_prefix = f"{req.project_id}-"
    
    for secret_properties in secret_client.list_properties_of_secrets():
        if secret_properties.name.startswith(secret_prefix):
            key_name = secret_properties.name[len(secret_prefix):]
            keys.append(key_name)
    
    return {"project_id": req.project_id, "secret_keys": keys}
```

## Secret Management Flow

### 1. User Sets Secrets (via UI)
```
User Dashboard → Set Environment Variables
    ↓
API validates user owns project
    ↓
Secrets stored in Azure Key Vault
    ↓
Confirmation (keys only, no values shown)
```

### 2. LLM Executes Code
```
LLM: "Run npm start"
    ↓
Worker loads secrets from Key Vault
    ↓
Injects into subprocess environment
    ↓
Command executes with real secrets
    ↓
Output sanitized before return
    ↓
LLM sees: "Stripe connected with key sk_test_***REDACTED***"
```

### 3. Code Access Patterns (All Work Normally)

**Node.js:**
```javascript
// This works normally
const stripeKey = process.env.STRIPE_SECRET_KEY;
const stripe = new Stripe(stripeKey);
```

**Python:**
```python
# This works normally
import os
stripe_key = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = stripe_key
```

**But these are blocked:**
```bash
cat .env  # Returns: "Security Error: Direct access to environment variables is not allowed"
echo $STRIPE_SECRET_KEY  # Blocked
printenv  # Blocked
```

## Output Examples

### What the LLM Sees:

```
> npm start

Server starting...
Stripe initialized with key: sk_test_***REDACTED***
Database connected to: postgresql://user:***REDACTED***@db.example.com/mydb
Server running on port 3000
```

### What Actually Happened:
- Real Stripe test key was used
- Real database connection was made
- But LLM never sees the actual values

## Additional Security Measures

### 1. Audit Logging
```python
# Log all secret access
def log_secret_access(project_id: str, command: str, secrets_used: List[str]):
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "project_id": project_id,
        "command": command[:100],  # First 100 chars
        "secrets_accessed": secrets_used,
        "worker_id": os.getpid()
    }
    # Send to Azure Monitor or logging service
```

### 2. Rate Limiting
- Limit secret access per project per hour
- Alert on unusual patterns

### 3. Secret Rotation
- Support for automatic secret rotation
- Versioned secrets with graceful transitions

### 4. Emergency Kill Switch
- Ability to instantly revoke all secrets for a project
- Useful if suspicious activity detected

## Implementation Priority

1. **Phase 1** (Immediate):
   - Basic Key Vault integration
   - Runtime injection
   - Basic output sanitization
   - Block .env file reads

2. **Phase 2** (Week 1):
   - Advanced sanitization patterns
   - Audit logging
   - Secret management API

3. **Phase 3** (Week 2):
   - Rate limiting
   - Monitoring dashboard
   - Secret rotation support

## Testing Strategy

### Test Cases:
1. **Functional Test**: Stripe API call succeeds with injected key
2. **Security Test**: `cat .env` returns blocked message
3. **Sanitization Test**: Console.log of API key shows masked value
4. **Integration Test**: Full app with multiple secrets works normally
5. **Edge Cases**: Binary data, multi-line secrets, special characters

### Example Test:
```python
# Test that secrets work but are hidden
def test_stripe_integration():
    # Set test secret
    set_secret("test-project", "STRIPE_SECRET_KEY", "sk_test_123456789")
    
    # Execute code that uses Stripe
    result = execute_command("test-project", "python test_stripe.py")
    
    # Verify it worked
    assert "Payment successful" in result["stdout"]
    
    # Verify secret is masked
    assert "sk_test_123456789" not in result["stdout"]
    assert "***REDACTED***" in result["stdout"]
```

## Benefits

1. **Zero Code Changes**: Existing code works without modification
2. **Real Functionality**: APIs and services work with actual keys
3. **Complete Security**: LLM never sees sensitive values
4. **Audit Trail**: All secret access is logged
5. **Project Isolation**: Each project's secrets are completely separate

## Potential Challenges & Solutions

### Challenge 1: Performance
**Issue**: Loading secrets on every command
**Solution**: Cache secrets in worker memory with TTL

### Challenge 2: Complex Secret Patterns
**Issue**: Some secrets might be hard to detect/mask
**Solution**: Multiple detection strategies + manual patterns

### Challenge 3: Debugging
**Issue**: Developers need to debug secret-related issues
**Solution**: Provide sanitized hints (first/last 4 chars, length, type)

## Configuration

### Environment Variables for Worker:
```bash
# Azure Key Vault configuration
AZURE_KEY_VAULT_URL=https://llm-agent-vault.vault.azure.net/
AZURE_TENANT_ID=xxx
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx

# Security settings
ENABLE_SECRET_INJECTION=true
ENABLE_OUTPUT_SANITIZATION=true
BLOCK_ENV_FILE_ACCESS=true
AUDIT_SECRET_ACCESS=true
```

## Rollback Plan

If issues arise, can quickly revert by:
1. Setting `ENABLE_SECRET_INJECTION=false`
2. Workers fall back to standard execution
3. No secrets injected, but also no functionality requiring them

## Success Metrics

1. **Security**: 0 secret leaks in LLM outputs
2. **Functionality**: 100% of secret-dependent code works
3. **Performance**: <100ms overhead for secret injection
4. **Usability**: No code changes required

This architecture provides the security you need while maintaining full functionality for the LLM to test real integrations like Stripe.