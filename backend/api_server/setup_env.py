#!/usr/bin/env python3
"""
Sustainable Environment Setup Script
Automatically handles Python version compatibility and creates proper virtual environments
"""

import sys
import subprocess
import os
import shutil
from pathlib import Path

def get_python_version():
    """Get current Python version as tuple"""
    return sys.version_info[:2]

def run_command(cmd, check=True, capture=True):
    """Run command with proper error handling"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, check=check, 
                                  capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return None, None
    except subprocess.CalledProcessError as e:
        if capture:
            return None, e.stderr
        else:
            raise

def find_compatible_python():
    """Find the best compatible Python version"""
    current_version = get_python_version()
    print(f"🐍 Current Python version: {current_version[0]}.{current_version[1]}")
    
    # Check for available Python versions
    python_versions = []
    for version in ["3.12", "3.11", "3.13"]:
        try:
            cmd = f"python{version} --version"
            stdout, stderr = run_command(cmd)
            if stdout:
                python_versions.append((version, stdout))
                print(f"✅ Found Python {version}: {stdout}")
        except:
            print(f"❌ Python {version} not available")
    
    # Recommend best version
    if current_version == (3, 13):
        print("🔧 Python 3.13 detected - will use compatibility requirements")
        return "python3", "requirements-python313-compatible.txt"
    elif current_version in [(3, 11), (3, 12)]:
        print("✅ Compatible Python version detected")
        return "python3", "requirements.txt"
    else:
        # Try to find 3.12 or 3.11
        for version, _ in python_versions:
            if version in ["3.12", "3.11"]:
                print(f"🔄 Switching to Python {version} for better compatibility")
                return f"python{version}", "requirements.txt"
        
        print("⚠️  Using current Python with compatibility mode")
        return "python3", "requirements-python313-compatible.txt"

def setup_virtual_environment():
    """Create and setup virtual environment with proper dependencies"""
    script_dir = Path(__file__).parent
    venv_path = script_dir / "venv"
    
    print(f"🏠 Working directory: {script_dir}")
    
    # Find compatible Python
    python_cmd, requirements_file = find_compatible_python()
    
    # Remove existing broken venv
    if venv_path.exists():
        print("🗑️  Removing existing virtual environment...")
        shutil.rmtree(venv_path)
    
    # Create new virtual environment
    print(f"🆕 Creating virtual environment with {python_cmd}...")
    stdout, stderr = run_command(f"{python_cmd} -m venv {venv_path}")
    if stderr:
        print(f"⚠️  Warning during venv creation: {stderr}")
    
    # Determine pip command
    if sys.platform == "win32":
        pip_cmd = str(venv_path / "Scripts" / "pip")
        python_venv_cmd = str(venv_path / "Scripts" / "python")
    else:
        pip_cmd = str(venv_path / "bin" / "pip")
        python_venv_cmd = str(venv_path / "bin" / "python")
    
    # Upgrade pip first
    print("⬆️  Upgrading pip...")
    stdout, stderr = run_command(f"{pip_cmd} install --upgrade pip")
    if stderr and "error" in stderr.lower():
        print(f"⚠️  Pip upgrade warning: {stderr}")
    
    # Install wheel for faster builds
    print("🛞 Installing wheel...")
    run_command(f"{pip_cmd} install wheel")
    
    # Install requirements
    requirements_path = script_dir / requirements_file
    if requirements_path.exists():
        print(f"📦 Installing dependencies from {requirements_file}...")
        stdout, stderr = run_command(f"{pip_cmd} install -r {requirements_path}")
        if stderr and "error" in stderr.lower():
            print(f"❌ Error installing requirements: {stderr}")
            return False
        else:
            print("✅ Dependencies installed successfully!")
    else:
        print(f"❌ Requirements file not found: {requirements_path}")
        return False
    
    # Verify critical packages
    print("🔍 Verifying critical packages...")
    critical_packages = ["fastapi", "pydantic", "modal", "requests", "uvicorn"]
    
    for package in critical_packages:
        stdout, stderr = run_command(f"{pip_cmd} show {package}")
        if stdout:
            # Extract version
            for line in stdout.split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    print(f"  ✅ {package}: {version}")
                    break
        else:
            print(f"  ❌ {package}: NOT INSTALLED")
            return False
    
    # Test imports
    print("🧪 Testing critical imports...")
    test_imports = [
        "import fastapi",
        "import pydantic",
        "import modal", 
        "import requests",
        "from pydantic import BaseModel",
        "from fastapi import FastAPI"
    ]
    
    for import_test in test_imports:
        stdout, stderr = run_command(f"{python_venv_cmd} -c \"{import_test}\"")
        if stderr and "error" in stderr.lower():
            print(f"  ❌ Failed: {import_test}")
            print(f"     Error: {stderr}")
            return False
        else:
            print(f"  ✅ {import_test}")
    
    print(f"\n🎉 Environment setup completed successfully!")
    print(f"📍 Virtual environment: {venv_path}")
    print(f"🐍 Python command: {python_venv_cmd}")
    print(f"📦 Pip command: {pip_cmd}")
    
    # Create activation script
    if sys.platform != "win32":
        activate_script = script_dir / "activate_env.sh"
        with open(activate_script, 'w') as f:
            f.write(f"""#!/bin/bash
# Activate the virtual environment
source {venv_path}/bin/activate
echo "✅ Virtual environment activated!"
echo "🐍 Python: $(python --version)"
echo "📦 Pip: $(pip --version)"
echo ""
echo "🚀 Ready to run:"
echo "  python streaming_api.py"
echo "  python test_start_backend.py"
""")
        os.chmod(activate_script, 0o755)
        print(f"📄 Created activation script: {activate_script}")
        print(f"   Run: source {activate_script}")
    
    return True

def main():
    """Main setup function"""
    print("🔧 SUSTAINABLE ENVIRONMENT SETUP")
    print("=" * 50)
    print("This script will:")
    print("- Detect your Python version")  
    print("- Choose compatible dependencies")
    print("- Create a proper virtual environment")
    print("- Install all required packages")
    print("- Verify everything works")
    print()
    
    try:
        if setup_virtual_environment():
            print("\n🎯 NEXT STEPS:")
            print("1. Activate the environment:")
            if sys.platform == "win32":
                print("   venv\\Scripts\\activate")
            else:
                print("   source venv/bin/activate")
            print("2. Test the setup:")
            print("   python streaming_api.py")
            print()
            return True
        else:
            print("\n❌ Setup failed. Check errors above.")
            return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)