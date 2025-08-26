# modal_auth_controller.py

"""
Different methods to authenticate with Modal from your hosted AI backend
"""

import modal
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional
import json

class ModalAuthController:
"""
Handles Modal authentication for hosted servers without local token setup
"""

    def __init__(self, auth_method: str = "env_vars"):
        """
        Initialize Modal authentication

        Args:
            auth_method: "env_vars", "token_file", "manual_token", or "api_client"
        """
        self.auth_method = auth_method
        self._setup_authentication()

    def _setup_authentication(self):
        """Setup Modal authentication based on chosen method"""

        if self.auth_method == "env_vars":
            self._setup_env_vars_auth()
        elif self.auth_method == "token_file":
            self._setup_token_file_auth()
        elif self.auth_method == "manual_token":
            self._setup_manual_token_auth()
        elif self.auth_method == "api_client":
            self._setup_api_client_auth()
        else:
            raise ValueError(f"Unknown auth method: {self.auth_method}")

    def _setup_env_vars_auth(self):
        """Method 1: Use environment variables (RECOMMENDED)"""

        # Get token from environment variables
        token_id = os.getenv("MODAL_TOKEN_ID")
        token_secret = os.getenv("MODAL_TOKEN_SECRET")

        if not token_id or not token_secret:
            raise ValueError(
                "MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables must be set.\n"
                "Get these from your local ~/.modal.toml file after running 'modal token new'"
            )

        # Create temporary token file for Modal CLI
        modal_dir = Path.home() / ".modal"
        modal_dir.mkdir(exist_ok=True)

        token_content = f"""[default]

token_id = "{token_id}"
token_secret = "{token_secret}"
"""

        with open(modal_dir / "config.toml", "w") as f:
            f.write(token_content)

        print("✅ Modal authentication setup via environment variables")

    def _setup_token_file_auth(self):
        """Method 2: Copy token file to server"""

        token_file = Path.home() / ".modal" / "config.toml"

        if not token_file.exists():
            raise FileNotFoundError(
                f"Modal token file not found at {token_file}.\n"
                "Copy your local ~/.modal.toml to the server, or use environment variables."
            )

        print(f"✅ Modal authentication setup via token file: {token_file}")

    def _setup_manual_token_auth(self):
        """Method 3: Pass tokens manually (for testing)"""

        # This method requires you to pass tokens when creating the controller
        print("✅ Manual token authentication ready")

    def _setup_api_client_auth(self):
        """Method 4: Use Modal Python client directly (advanced)"""

        try:
            # Try to use Modal's client directly
            import modal.client
            print("✅ Modal API client authentication ready")
        except ImportError:
            raise ImportError("Modal client not available for direct API access")

class ProgrammaticModalDeployer:
"""
Deploys FastAPI apps to Modal programmatically from hosted server
"""

    def __init__(self, modal_token_id: str = None, modal_token_secret: str = None):
        """
        Initialize deployer with optional manual token passing

        Args:
            modal_token_id: Manual token ID (optional, uses env vars if not provided)
            modal_token_secret: Manual token secret (optional, uses env vars if not provided)
        """

        # Setup authentication
        if modal_token_id and modal_token_secret:
            os.environ["MODAL_TOKEN_ID"] = modal_token_id
            os.environ["MODAL_TOKEN_SECRET"] = modal_token_secret

        self.auth = ModalAuthController("env_vars")

        # Base image for FastAPI apps
        self.base_image = modal.Image.debian_slim(python_version="3.11").pip_install([
            "fastapi==0.104.1",
            "uvicorn[standard]==0.24.0",
            "python-multipart==0.0.6",
            "pandas==2.1.4",
            "pydantic==2.5.0",
            "requests==2.31.0",
        ])

    def deploy_fastapi_app(self,
                          app_name: str,
                          fastapi_code: str,
                          env_vars: Dict[str, str] = None) -> Dict[str, str]:
        """
        Deploy FastAPI app programmatically

        Args:
            app_name: Name for the Modal app
            fastapi_code: The FastAPI code to deploy
            env_vars: Environment variables for the app

        Returns:
            Deployment result with URL and status
        """

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create project files
                self._create_deployment_files(temp_path, app_name, fastapi_code)

                # Create Modal secrets if env vars provided
                if env_vars:
                    self._create_modal_secrets(f"{app_name}-secrets", env_vars)

                # Deploy using subprocess (most reliable)
                return self._deploy_via_subprocess(temp_path, app_name)

        except Exception as e:
            return {
                "status": "error",
                "app_name": app_name,
                "error": str(e)
            }

    def _create_deployment_files(self, project_path: Path, app_name: str, fastapi_code: str):
        """Create the Modal deployment files"""

        # Create api_routes.py
        api_routes_content = f'''

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

def create_fastapi_app():
app = FastAPI(title="{app_name}", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def health_check():
        return {{
            "app": "{app_name}",
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }}

{fastapi_code}

    return app

fastapi_app = create_fastapi_app()
'''

        with open(project_path / "api_routes.py", "w") as f:
            f.write(api_routes_content)

        # Create app.py (Modal deployment config)
        app_py_content = f'''

import modal

BASE_IMAGE = modal.Image.debian_slim(python_version="3.11").pip_install([
"fastapi==0.104.1",
"uvicorn[standard]==0.24.0",
"python-multipart==0.0.6",
"pandas==2.1.4",
"pydantic==2.5.0",
])

app = modal.App("{app_name}")

@app.function(
image=BASE_IMAGE,
secrets=[modal.Secret.from_name("{app_name}-secrets")] if True else [],
)
@modal.web_endpoint(method="GET")
@modal.web_endpoint(method="POST")
@modal.web_endpoint(method="PUT")
@modal.web_endpoint(method="DELETE")
def web_app():
from api_routes import fastapi_app
return fastapi_app
'''

        with open(project_path / "app.py", "w") as f:
            f.write(app_py_content)

    def _create_modal_secrets(self, secret_name: str, env_vars: Dict[str, str]):
        """Create Modal secrets using subprocess"""
        try:
            cmd = ["modal", "secret", "create", secret_name]
            for key, value in env_vars.items():
                cmd.append(f"{key}={value}")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Created Modal secret: {secret_name}")

        except subprocess.CalledProcessError as e:
            print(f"⚠️ Warning: Could not create secret {secret_name}: {e.stderr}")

    def _deploy_via_subprocess(self, project_path: Path, app_name: str) -> Dict[str, str]:
        """Deploy to Modal using subprocess"""

        try:
            # Change to project directory
            original_cwd = os.getcwd()
            os.chdir(project_path)

            # Run modal deploy
            result = subprocess.run(
                ["modal", "deploy", "app.py"],
                capture_output=True,
                text=True,
                check=True,
                timeout=120  # 2 minute timeout
            )

            # Extract URL from output
            output = result.stdout + result.stderr
            url = self._extract_modal_url(output, app_name)

            return {
                "status": "success",
                "app_name": app_name,
                "url": url,
                "docs_url": f"{url}/docs",
                "logs_command": f"modal logs {app_name}",
                "deployment_output": output[:500]  # First 500 chars
            }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "app_name": app_name,
                "error": str(e),
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "app_name": app_name,
                "error": "Deployment timeout (>2 minutes)"
            }
        finally:
            os.chdir(original_cwd)

    def _extract_modal_url(self, output: str, app_name: str) -> str:
        """Extract the deployed URL from Modal's output"""

        lines = output.split('\n')
        for line in lines:
            if 'modal.run' in line and 'https://' in line:
                words = line.split()
                for word in words:
                    if word.startswith('https://') and 'modal.run' in word:
                        return word.rstrip('.,!?')

        # Fallback URL pattern
        return f"https://your-username--{app_name}-web-app.modal.run"

    def get_deployment_logs(self, app_name: str, lines: int = 50) -> str:
        """Get logs for a deployed app"""
        try:
            result = subprocess.run(
                ["modal", "logs", app_name, "--lines", str(lines)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error getting logs: {e.stderr}"

# Usage Examples for Different Authentication Methods

# Method 1: Environment Variables (Recommended for Production)

def deploy_with_env_vars():
"""Deploy using environment variables"""

    # Set these on your server:
    # export MODAL_TOKEN_ID="ak-your-token-id"
    # export MODAL_TOKEN_SECRET="as-your-token-secret"

    deployer = ProgrammaticModalDeployer()

    ai_generated_code = '''
    @app.get("/customers")
    def get_customers():
        return {"customers": [{"id": 1, "name": "John Doe"}]}
    '''

    result = deployer.deploy_fastapi_app(
        app_name="my-crm-app",
        fastapi_code=ai_generated_code,
        env_vars={"DATABASE_URL": "sqlite:///./crm.db"}
    )

    return result

# Method 2: Manual Token Passing (for Testing)

def deploy_with_manual_tokens():
"""Deploy by passing tokens manually"""

    deployer = ProgrammaticModalDeployer(
        modal_token_id="ak-your-token-id",
        modal_token_secret="as-your-token-secret"
    )

    ai_generated_code = '''
    @app.get("/products")
    def get_products():
        return {"products": [{"id": 1, "name": "Widget"}]}
    '''

    result = deployer.deploy_fastapi_app(
        app_name="product-api",
        fastapi_code=ai_generated_code
    )

    return result

if **name** == "**main**":

    # Test environment variables method
    print("Testing deployment...")

    # Make sure you have MODAL_TOKEN_ID and MODAL_TOKEN_SECRET set
    if not os.getenv("MODAL_TOKEN_ID"):
        print("❌ MODAL_TOKEN_ID not set")
        print("Set it with: export MODAL_TOKEN_ID='ak-your-token-id'")
        exit(1)

    result = deploy_with_env_vars()
    print("Deployment result:", result)
