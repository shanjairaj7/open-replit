#!/usr/bin/env python3
"""
Quick script to test the build error fix with our update system
"""

import os
import subprocess
import sys



def main():
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable is required")
        return

    # Build error message
    error_message = """Fix this build error in the use-theme.ts file:

[plugin:vite:esbuild] Transform failed with 1 error:
/app/src/hooks/use-theme.ts:60:35: ERROR: Expected ">" but found "{"
/app/src/hooks/use-theme.ts:60:35
Expected ">" but found "{"
58 |  
59 |    return (
60 |      <ThemeProviderContext.Provider {...props} value={value}>
   |                                     ^
61 |        {children}
62 |      </ThemeProviderContext.Provider>

The error indicates there's a syntax issue with the JSX in the ThemeProviderContext.Provider. Please read the file and fix the syntax error."""

    print("🔧 Running build error fix test...")
    print(f"📝 Error message: {error_message[:100]}...")
    
    # Run the update command
    cmd = [
        "python3", 
        "test_groq_project_update.py", 
        "--project-id", "place-just-write-notes-0801",
        "--message", error_message
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        print(f"\n✅ Command completed with return code: {result.returncode}")
    except Exception as e:
        print(f"❌ Error running command: {e}")

if __name__ == "__main__":
    main()