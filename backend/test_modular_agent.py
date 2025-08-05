#!/usr/local/bin/python3.13
"""
Test script for the modular coding agent
This script should work exactly like the original test_groq_project_update.py
"""

import sys
import os

# Add the current directory to the path so we can import the coding_agent module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function from the modular coding agent
from coding_agent.main import main

if __name__ == "__main__":
    main()