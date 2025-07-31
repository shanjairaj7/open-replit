#!/usr/bin/env python3
"""
Test Groq Kimi Model with Bolt-style XML Generation
This script tests the Groq API's ability to generate bolt-style XML commands
"""

import os
import asyncio
import json
from groq import AsyncGroq
from typing import AsyncGenerator
import re
from datetime import datetime

# ANSI colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# System prompt for existing React project with full setup
SYSTEM_PROMPT = """You are a coding assistant working on an existing React application that is already fully configured and ready to use.

The project already has COMPLETE setup with:
- React 18 + TypeScript configured
- Tailwind CSS fully configured (tailwind.config.js, postcss.config.js, CSS imports)
- shadcn-ui components library installed and configured
- All necessary dependencies in package.json
- Build tools and development server ready
- Project structure: src/, public/, package.json, etc.

DO NOT create any configuration files like:
- tailwind.config.js (already exists)
- postcss.config.js (already exists) 
- package.json modifications (dependencies already installed)
- Basic CSS setup files

Your job is to focus ONLY on the specific feature requested:
- Create new React components in src/components/
- Create pages, hooks, utils, types as needed
- Use existing shadcn-ui components and Tailwind classes
- Create mock data files if needed
- Only update src/App.tsx if the main app needs changes

MUST respond using this exact XML format:

<artifact id="project-id" title="Project Title">
<action type="file" filePath="src/components/ComponentName.tsx">
COMPONENT CODE HERE
</action>
<action type="file" filePath="src/App.tsx">
APP CODE HERE (only if needed)
</action>
</artifact>

Focus ONLY on the specific functionality requested. The project is ready - just add the feature components."""

class GroqBoltGenerator:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)
        self.model = "moonshotai/kimi-k2-instruct"
        
    async def generate_bolt_response(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """Generate bolt-style XML response from user prompt"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=8000,
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error: {str(e)}"

class ProjectFileCreator:
    """Parse response and create actual files"""
    
    def __init__(self, project_dir="generated_project"):
        self.project_dir = project_dir
        self.files_created = []
        self.files_updated = []
        self.commands_run = []
        
        # Create project directory
        os.makedirs(self.project_dir, exist_ok=True)
        
    def parse_and_create_files(self, response: str):
        """Parse the response and create actual files"""
        
        # Find artifact
        artifact_match = re.search(r'<artifact\s+id="([^"]+)"\s+title="([^"]+)">', response)
        if artifact_match:
            artifact_id = artifact_match.group(1)
            artifact_title = artifact_match.group(2)
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}📦 Project: {artifact_title}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        # Find all actions - updated for new format with multiline content
        action_pattern = r'<action\s+type="([^"]+)"(?:\s+filePath="([^"]+)")?>(.*?)</action>'
        
        for match in re.finditer(action_pattern, response, re.DOTALL):
            action_type = match.group(1)
            file_path = match.group(2) if match.group(2) else None
            content = match.group(3).strip()
            
            if action_type == "file" and file_path:
                self._create_file(file_path, content)
                    
            elif action_type == "shell":
                self.commands_run.append(content)
                print(f"{Colors.GREEN}🚀 Command: {content}{Colors.ENDC}")
                
            elif action_type == "start":
                self.commands_run.append(content)
                print(f"{Colors.CYAN}🌐 Start: {content}{Colors.ENDC}")
        
        self._print_summary()
    
    def _create_file(self, file_path: str, content: str):
        """Create or update a file"""
        full_path = os.path.join(self.project_dir, file_path)
        
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Check if file exists (update vs create)
        is_update = os.path.exists(full_path)
        
        # Write file
        with open(full_path, 'w') as f:
            f.write(content)
        
        if is_update:
            self.files_updated.append(file_path)
            print(f"{Colors.YELLOW}📝 Updated: {file_path}{Colors.ENDC}")
        else:
            self.files_created.append(file_path)
            print(f"{Colors.BLUE}📄 Created: {file_path}{Colors.ENDC}")
    
    def _print_summary(self):
        """Print summary of all actions"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}📋 Summary:{Colors.ENDC}")
        
        if self.files_created:
            print(f"\n{Colors.GREEN}✅ Files Created ({len(self.files_created)}):{Colors.ENDC}")
            for f in self.files_created:
                print(f"   📄 {f}")
        
        if self.files_updated:
            print(f"\n{Colors.YELLOW}🔄 Files Updated ({len(self.files_updated)}):{Colors.ENDC}")
            for f in self.files_updated:
                print(f"   📝 {f}")
                
        if self.commands_run:
            print(f"\n{Colors.CYAN}⚡ Commands ({len(self.commands_run)}):{Colors.ENDC}")
            for c in self.commands_run:
                print(f"   🚀 {c}")
        
        print(f"\n{Colors.GREEN}📁 Project directory: {self.project_dir}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

async def test_analytics_dashboard():
    """Test creating an analytics dashboard"""
    
    # Get API key from environment or use the one from cookies
    api_key = os.getenv("GROQ_API_KEY", "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")
    
    generator = GroqBoltGenerator(api_key)
    file_creator = ProjectFileCreator()
    
    # Test prompt
    test_prompt = """Create a modern analytics dashboard with the following features:
    1. A beautiful UI with charts showing revenue, users, and sales data
    2. Use React with TypeScript and Recharts for visualization
    3. Include mock data for demonstration
    4. Use Tailwind CSS for styling
    5. Make it responsive and professional looking"""
    
    print(f"{Colors.BOLD}{Colors.CYAN}Bolt-style XML Generation Test{Colors.ENDC}")
    print(f"{Colors.YELLOW}Model: Groq Kimi K2{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Prompt:{Colors.ENDC}")
    print(test_prompt)
    print(f"\n{Colors.YELLOW}Generating response...{Colors.ENDC}\n")
    
    # Collect full response
    full_response = ""
    async for chunk in generator.generate_bolt_response(test_prompt):
        full_response += chunk
        # Show streaming progress
        print(f"{Colors.CYAN}.{Colors.ENDC}", end="", flush=True)
    
    print(f"\n\n{Colors.GREEN}Response received!{Colors.ENDC}")
    
    # Parse and create files from the response
    file_creator.parse_and_create_files(full_response)
    
    # Save the raw response for debugging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"bolt_response_{timestamp}.xml"
    with open(output_file, 'w') as f:
        f.write(full_response)
    print(f"\n{Colors.GREEN}Raw response saved to: {output_file}{Colors.ENDC}")

async def test_custom_prompt():
    """Test with custom user prompt"""
    
    api_key = os.getenv("GROQ_API_KEY", "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")
    
    generator = GroqBoltGenerator(api_key)
    file_creator = ProjectFileCreator()
    
    print(f"{Colors.BOLD}{Colors.CYAN}Bolt-style XML Generation - Custom Prompt{Colors.ENDC}")
    print(f"{Colors.YELLOW}Enter your prompt (or 'quit' to exit):{Colors.ENDC}")
    
    while True:
        user_input = input(f"\n{Colors.BOLD}> {Colors.ENDC}")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
            
        print(f"\n{Colors.YELLOW}Generating response...{Colors.ENDC}\n")
        
        full_response = ""
        async for chunk in generator.generate_bolt_response(user_input):
            full_response += chunk
            print(f"{Colors.CYAN}.{Colors.ENDC}", end="", flush=True)
        
        print(f"\n\n{Colors.GREEN}Response received!{Colors.ENDC}")
        file_creator.parse_and_create_files(full_response)

async def main():
    """Main function"""
    
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}Groq Bolt Generation Test{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print()
    print("This tests Groq's ability to generate bolt-style XML commands")
    print("for creating files, updating files, and running terminal commands.")
    print()
    print("Options:")
    print("1. Test with analytics dashboard prompt")
    print("2. Enter custom prompt")
    print()
    
    choice = input("Select option (1 or 2): ")
    
    if choice == "1":
        await test_analytics_dashboard()
    elif choice == "2":
        await test_custom_prompt()
    else:
        print(f"{Colors.RED}Invalid choice{Colors.ENDC}")

if __name__ == "__main__":
    asyncio.run(main())