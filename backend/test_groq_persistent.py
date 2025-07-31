#!/usr/bin/env python3
"""
Persistent Groq Bolt Test - Multi-turn conversation with project context
This script maintains project state across multiple requests
"""

import os
import asyncio
import json
from groq import AsyncGroq
from typing import AsyncGenerator, Dict, List
import re
from datetime import datetime
import uuid

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

class ProjectSession:
    """Manages persistent project state across multiple requests"""
    
    def __init__(self, project_dir: str = "persistent_project"):
        self.project_dir = project_dir
        self.session_id = str(uuid.uuid4())[:8]
        self.conversation_history = []
        self.project_files = {}  # filepath -> content
        self.files_created = []
        self.files_updated = []
        self.commands_run = []
        
        # Create project directory
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Initialize session log
        self.session_log = f"session_{self.session_id}.json"
        
    def add_conversation(self, user_request: str, ai_response: str):
        """Add conversation turn to history"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_request,
            "ai_response": ai_response,
            "files_created": list(self.files_created),
            "files_updated": list(self.files_updated),
            "commands": list(self.commands_run)
        })
        self._save_session()
    
    def get_project_context(self) -> str:
        """Generate project context for the model"""
        if not self.project_files:
            return ""
        
        context = "\n\nCURRENT PROJECT STATE:\n"
        context += "The following files already exist in this project:\n\n"
        
        # Create a tree-like structure
        context += "Project Structure:\n"
        context += f"{self.project_dir}/\n"
        
        # Group files by directory
        file_tree = {}
        for filepath in sorted(self.project_files.keys()):
            parts = filepath.split('/')
            current = file_tree
            for part in parts[:-1]:  # directories
                if part not in current:
                    current[part] = {}
                current = current[part]
            # Add file
            current[parts[-1]] = None
        
        def print_tree(tree, prefix="", is_last=True):
            items = list(tree.items())
            for i, (name, subtree) in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "
                context_line = f"{prefix}{current_prefix}{name}"
                
                if subtree is None:  # It's a file
                    context_line += "\n"
                else:  # It's a directory
                    context_line += "/\n"
                
                nonlocal context
                context += context_line
                
                if subtree is not None:  # Process subdirectory
                    extension = "    " if is_last_item else "│   "
                    print_tree(subtree, prefix + extension, is_last_item)
        
        print_tree(file_tree)
        
        context += f"\nTotal files: {len(self.project_files)}\n"
        context += "\nWhen making changes, you can:\n"
        context += "- UPDATE existing files by providing the full new content\n"
        context += "- CREATE new files as needed\n"
        context += "- Reference and import from existing files\n"
        context += "- Follow the existing project structure and naming patterns\n\n"
        
        return context
    
    def parse_and_apply_changes(self, response: str):
        """Parse AI response and apply file changes"""
        self.files_created.clear()
        self.files_updated.clear()
        self.commands_run.clear()
        
        # Find artifact
        artifact_match = re.search(r'<artifact\s+id="([^"]+)"\s+title="([^"]+)">', response)
        if artifact_match:
            artifact_id = artifact_match.group(1)
            artifact_title = artifact_match.group(2)
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}📦 Project: {artifact_title}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        # Find all actions
        action_pattern = r'<action\s+type="([^"]+)"(?:\s+filePath="([^"]+)")?>(.*?)</action>'
        
        for match in re.finditer(action_pattern, response, re.DOTALL):
            action_type = match.group(1)
            file_path = match.group(2) if match.group(2) else None
            content = match.group(3).strip()
            
            if action_type == "file" and file_path:
                self._apply_file_change(file_path, content)
                    
            elif action_type == "shell":
                self.commands_run.append(content)
                print(f"{Colors.GREEN}🚀 Command: {content}{Colors.ENDC}")
                
            elif action_type == "start":
                self.commands_run.append(content)
                print(f"{Colors.CYAN}🌐 Start: {content}{Colors.ENDC}")
        
        self._print_summary()
    
    def _apply_file_change(self, file_path: str, content: str):
        """Apply file creation or update"""
        full_path = os.path.join(self.project_dir, file_path)
        
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Check if file exists (update vs create)
        is_update = file_path in self.project_files
        
        # Write file
        with open(full_path, 'w') as f:
            f.write(content)
        
        # Update project state
        self.project_files[file_path] = content
        
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
        
        total_files = len(self.project_files)
        print(f"\n{Colors.GREEN}📁 Project: {total_files} files in {self.project_dir}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    def _save_session(self):
        """Save session state to file"""
        session_data = {
            "session_id": self.session_id,
            "project_dir": self.project_dir,
            "conversation_history": self.conversation_history,
            "project_files": list(self.project_files.keys()),
            "created_at": datetime.now().isoformat()
        }
        
        with open(self.session_log, 'w') as f:
            json.dump(session_data, f, indent=2)

class PersistentGroqGenerator:
    """Groq generator with persistent project context"""
    
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)
        self.model = "moonshotai/kimi-k2-instruct"
        
        # Base system prompt
        self.base_system_prompt = """You are a coding assistant working on a React application with TypeScript, Tailwind CSS, and shadcn-ui components already configured.

IMPORTANT CONTEXT AWARENESS:
- If this is a follow-up request, you will see the current project files below
- You can UPDATE existing files by providing the full new content
- You can CREATE new files as needed
- Always consider existing code structure and patterns
- Import and reference existing components appropriately

Your job is to:
- Build the specific feature requested
- Maintain consistency with existing code
- Use TypeScript, Tailwind CSS, and shadcn-ui components
- Create modular, reusable components

MUST respond using this exact XML format:

<artifact id="project-id" title="Project Title">
<action type="file" filePath="src/components/ComponentName.tsx">
COMPONENT CODE HERE
</action>
<action type="file" filePath="src/App.tsx">
APP CODE HERE (only if needs changes)
</action>
</artifact>

Focus on the specific functionality requested while maintaining the existing codebase."""

    async def generate_response(self, user_prompt: str, project_context: str = "") -> AsyncGenerator[str, None]:
        """Generate response with project context"""
        
        # Combine system prompt with project context
        full_system_prompt = self.base_system_prompt + project_context
        
        messages = [
            {"role": "system", "content": full_system_prompt},
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

async def run_persistent_session():
    """Run persistent multi-turn conversation"""
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY", "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")
    
    generator = PersistentGroqGenerator(api_key)
    session = ProjectSession()
    
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}🔄 Persistent Groq Bolt Generation{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.CYAN}Session ID: {session.session_id}{Colors.ENDC}")
    print(f"{Colors.CYAN}Project Directory: {session.project_dir}{Colors.ENDC}")
    print()
    print("This is a persistent session. Each request builds on the previous ones.")
    print("Type 'quit', 'exit', or 'q' to end the session.")
    print("Type 'status' to see current project state.")
    print("Type 'clear' to start a new project.")
    print()
    
    conversation_count = 0
    
    while True:
        conversation_count += 1
        print(f"{Colors.BOLD}💬 Request #{conversation_count}:{Colors.ENDC}")
        user_input = input(f"{Colors.BOLD}> {Colors.ENDC}")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print(f"\n{Colors.GREEN}Session ended. Files saved in: {session.project_dir}{Colors.ENDC}")
            break
        
        if user_input.lower() == 'status':
            print(f"\n{Colors.CYAN}📊 Project Status:{Colors.ENDC}")
            print(f"Files: {len(session.project_files)}")
            for filepath in session.project_files.keys():
                print(f"  📄 {filepath}")
            print(f"Conversations: {len(session.conversation_history)}")
            print()
            continue
        
        if user_input.lower() == 'clear':
            session = ProjectSession()
            print(f"{Colors.YELLOW}🗑️ Started new project session{Colors.ENDC}")
            conversation_count = 0
            continue
            
        if not user_input.strip():
            continue
        
        print(f"\n{Colors.YELLOW}🤖 Generating response...{Colors.ENDC}")
        
        # Get project context for follow-up requests
        project_context = session.get_project_context()
        
        # Generate response
        full_response = ""
        async for chunk in generator.generate_response(user_input, project_context):
            full_response += chunk
            print(f"{Colors.CYAN}.{Colors.ENDC}", end="", flush=True)
        
        print(f"\n\n{Colors.GREEN}✅ Response received!{Colors.ENDC}")
        
        # Apply changes to project
        session.parse_and_apply_changes(full_response)
        
        # Save conversation
        session.add_conversation(user_input, full_response)
        
        # Save raw response for debugging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = f"response_{conversation_count}_{timestamp}.xml"
        with open(response_file, 'w') as f:
            f.write(full_response)
        
        print(f"\n{Colors.BLUE}💾 Response saved: {response_file}{Colors.ENDC}")
        print()

async def main():
    """Main function"""
    await run_persistent_session()

if __name__ == "__main__":
    asyncio.run(main())