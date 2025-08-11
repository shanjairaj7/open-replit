#!/usr/local/bin/python3.13
"""
Enhanced Groq Persistent Conversation System with Boilerplate Integration
- Uses pre-built boilerplate as starting point
- Always passes complete file tree to model
- Clones boilerplate for each new project
- Maintains project state across requests
"""

import os
import re
import json
import shutil
import requests
import asyncio
import time
import argparse
from datetime import datetime
from pathlib import Path
from groq import Groq
from typing import Generator, Dict, Optional
import sys
sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend')
from shared_models import GroqAgentState, StreamingXMLParser
from openai import OpenAI


sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend')
from coder.prompts import _build_summary_prompt, senior_engineer_prompt
from coder.index import coder


def generate_project_name(user_request: str) -> str:
    """Generate a meaningful project name from user request"""
    import re
    
    # Extract key words from the request
    words = re.findall(r'\b\w+\b', user_request.lower())
    
    # Filter out common words
    stop_words = {'create', 'make', 'build', 'add', 'a', 'an', 'the', 'for', 'with', 'that', 'where', 'can', 'will', 'should', 'i', 'my', 'our', 'and', 'or', 'but', 'is', 'are', 'have', 'has', 'to', 'of', 'in', 'on', 'at', 'by'}
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Take first 3-4 most meaningful words
    key_words = meaningful_words[:4] if len(meaningful_words) >= 4 else meaningful_words[:3]
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%m%d")
    
    # Join with dashes
    if key_words:
        project_name = '-'.join(key_words) + f'-{timestamp}'
    else:
        project_name = f'project-{timestamp}-{datetime.now().strftime("%H%M")}'
    
    return project_name


class BoilerplatePersistentGroq:
    """
    Main orchestrator class for Groq-based project generation and updates.
    
    State Model: GroqAgentState (Pydantic model defined above)
    """
    
    def __init__(self, api_key: str = None, project_name: str = None, api_base_url: str = "http://localhost:8000/api", project_id: str = None):
        print("🐛 DEBUG: Starting BoilerplatePersistentGroq __init__")
        self.client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=api_key or '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', default_headers={"x-include-usage": 'true'})
        print("🐛 DEBUG: Groq client created")
        self.model = "qwen/qwen3-coder"
        self.conversation_history = []  # Store conversation messages
        self.api_base_url = api_base_url
        
        # Track files that have been read - project-specific persistence
        self.read_files_tracker = set()  # Files read in current session
        self.read_files_persistent = set()  # Files read across all sessions for THIS project
        
        # Simplified token tracking - just 3 variables
        self.token_usage = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        
        # Todo management
        self.todos = []
        
        # Paths (for local boilerplate reference)
        print("🐛 DEBUG: Setting up paths")
        self.backend_dir = Path(__file__).parent
        print(f"🐛 DEBUG: Backend dir: {self.backend_dir}")
        self.boilerplate_path = self.backend_dir / "boilerplate" / "shadcn-boilerplate"
        print("🐛 DEBUG: Paths set up successfully")
        
        if project_id:
            # Load existing project
            self.project_id = project_id
            self.project_name = project_id  # Use project_id as name for now
            self.project_files = {}
            self._scan_project_files_via_api()
            
            # Load project summary and conversation history
            self._load_project_context()
            
            # Load project-specific read files tracking
            self._load_read_files_tracking()
            
            # Load system prompt
            self.system_prompt = self._load_system_prompt()
            
            print(f"✅ Loaded existing project for updates: {self.project_name} (ID: {self.project_id})")
            print(f"📁 Total files: {len(self.project_files)}")
            print(f"💬 Loaded conversation history: {len(self.conversation_history)} messages")
            
        else:
            # Create new project
            if project_name:
                self.project_name = project_name
                self.project_id = self._setup_project_via_api(project_name)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.project_name = f"project_{timestamp}"
                self.project_id = self._setup_project_via_api(self.project_name)
                
            self.project_files = {}
            self._scan_project_files_via_api()
            
            # Load system prompt from file (after project setup)
            self.system_prompt = self._load_system_prompt()
            
            print(f"✅ Project initialized via API: {self.project_name} (ID: {self.project_id})")
            print(f"📁 Total files: {len(self.project_files)}")
            
        # Show read files status for both modes
        self._show_read_files_status()
        
        # Initialize missing attributes that might be set later
        self.preview_url = None
        self.backend_url = None
        self._last_plan_response = None
    
    def _show_read_files_status(self):
        """Display current read files tracking status"""
        print(f"📚 READ FILES TRACKING:")
        print(f"   📖 Current session: {len(self.read_files_tracker)} files")
        print(f"   💾 Persistent total: {len(self.read_files_persistent)} files")
        if self.read_files_persistent:
            print(f"   📋 Previously read: {', '.join(sorted(list(self.read_files_persistent)[:5]))}{'...' if len(self.read_files_persistent) > 5 else ''}")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file with project context"""
        # Use the update prompt since it has all the capabilities
        # prompt_file = Path(__file__).parent / "SYSTEM_PROMPT_UPDATE.md"
        # print(f"🔍 Loading system prompt from: {prompt_file}")
            
        # if prompt_file.exists():
        #     with open(prompt_file, 'r', encoding='utf-8') as f:
        #         base_prompt = f.read()
        #     print(f"✅ Loaded system prompt: {len(base_prompt)} characters")
        #     # Show first few lines to verify which prompt was loaded
        #     first_lines = '\n'.join(base_prompt.split('\n')[:3])
        #     print(f"📝 Prompt preview: {first_lines}")
        # else:
        #     # Fallback to basic prompt if file not found
        #     print(f"❌ System prompt file not found: {prompt_file}")
        #     base_prompt = "You are Bolt, an expert full-stack developer."
        
        base_prompt = senior_engineer_prompt
        
        # Add todo workflow instructions to the existing prompt
        todo_workflow_addition = """

## 📋 TODO-DRIVEN WORKFLOW
As a senior engineer, you naturally work through todos. This is how your mind organizes complex tasks:

**Creating Todos:**
- Break down requirements into actionable todos: `<action type="todo_create" id="unique_id" priority="high/medium/low" integration="true/false">Description</action>`
- Use descriptive IDs like: setup_auth, create_dashboard, implement_api
- Set priority: high (critical), medium (important), low (nice-to-have)  
- Set integration="true" if the todo requires testing with other components

**Managing Todos:**
- Start working on a todo: `<action type="todo_update" id="todo_id" status="in_progress"/>`
- Complete a todo: `<action type="todo_complete" id="todo_id" integration_tested="true/false"/>`
- List current todos: `<action type="todo_list"/>`

**Integration Focus:**
- Always test integrations when integration="true" or integration_tested="true"
- Verify components work together, not just in isolation
- Update todo status based on actual completion, not just file creation

**Natural Flow:**
1. Understand requirements → Create todos
2. Pick highest priority todo → Update to in_progress  
3. Implement, test, verify → Complete todo
4. Repeat until all todos done

Work systematically through each todo to build a complete, working solution."""

        # Add current project context and extra enforcement for update mode
        context_addition = f"\n\nCURRENT PROJECT:\n{self.get_project_context()}"
        
        return base_prompt + todo_workflow_addition + context_addition

    def _load_project_context(self):
        """Load existing project summary and conversation history for update mode"""
        # Load project summary
        summaries_dir = self.backend_dir / "project_summaries"
        summary_file = summaries_dir / f"{self.project_id}_summary.md"
        
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                self.project_summary = f.read()
            print(f"📋 Loaded project summary from: {summary_file}")
        else:
            self.project_summary = "No project summary available."
            print(f"⚠️  No project summary found at: {summary_file}")
        
        # Load conversation history
        conversations_dir = self.backend_dir / "project_conversations"
        conversations_dir.mkdir(exist_ok=True)
        
        conversation_file = conversations_dir / f"{self.project_id}_messages.json"
        
        if conversation_file.exists():
            with open(conversation_file, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
                self.conversation_history = conversation_data.get('messages', [])
                
                # Load token usage from conversation data
                if 'token_usage' in conversation_data:
                    # Ensure backwards compatibility with old token format
                    old_usage = conversation_data['token_usage']
                    self.token_usage = {
                        'total_tokens': old_usage.get('total_tokens', 0),
                        'prompt_tokens': old_usage.get('total_prompt_tokens', 0),
                        'completion_tokens': old_usage.get('total_completion_tokens', 0)
                    }
            print(f"💬 Loaded conversation history from: {conversation_file}")
            print(f"📚 Loaded read files tracker: {len(self.read_files_persistent)} files previously read")
            if 'token_usage' in conversation_data:
                print(f"💰 Total tokens used: {self.token_usage['total_tokens']:,}")
        else:
            print(f"⚠️  No conversation history found at: {conversation_file}")

    def _save_conversation_history(self):
        """Save current conversation history to JSON file"""
        conversations_dir = self.backend_dir / "project_conversations"
        conversations_dir.mkdir(exist_ok=True)
        
        conversation_file = conversations_dir / f"{self.project_id}_messages.json"
        
        # Check if we need to summarize conversation
        if self.token_usage['total_tokens'] >= 75000:
            # Mid-task summarization (token limit reached)
            print(f"🔄 Triggering summarization: {self.token_usage['total_tokens']:,} total tokens")
            self._check_and_summarize_conversation(is_mid_task=True)
        elif self.token_usage['total_tokens'] >= 75000 and len(self.conversation_history) > 50:
            # Optional summarization for completed tasks (lower threshold)
            print(f"🔄 Optional summarization for completed task: {self.token_usage['total_tokens']:,} total tokens")
            self._check_and_summarize_conversation(is_mid_task=False)
        
        conversation_data = {
            "project_id": self.project_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "summary_generated": True,
            "messages": self.conversation_history,
            "token_usage": self.token_usage,
            "project_state": {
                "files_created": list(self.project_files.keys()),
                "last_preview_status": "running"
            }
        }
        
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved conversation history to: {conversation_file}")

    def _check_and_summarize_conversation(self, is_mid_task=False):
        """Check if conversation needs summarization and create detailed summary"""
        
        print(f"\n🔄 Conversation has grown large ({self.token_usage['total_tokens']:,} total tokens)")
        print(f"📋 Creating summary to reset token count...")
        
        # Generate comprehensive summary
        summary_content = self._generate_detailed_conversation_summary(is_mid_task=is_mid_task)
        
        if summary_content:
            # Add summary to conversation with XML tag
            summary_message = {
                "role": "assistant",
                "content": f"<summary timestamp='{datetime.now().isoformat()}'>\n{summary_content}\n</summary>",
                "metadata": {
                    "type": "conversation_summary",
                    "tokens_at_summary": self.token_usage['total_tokens'],
                    "created_at": datetime.now().isoformat()
                }
            }
            
            self.conversation_history.append(summary_message)
            print(f"✅ Added detailed summary to conversation ({len(summary_content)} characters)")
            
            # Reset token counter to start fresh count from this point
            self._reset_token_tracking_after_summary()
        else:
            print(f"❌ Failed to generate conversation summary")

    def _get_tokens_since_last_summary(self) -> int:
        """Get token count since last VALID summary"""
        last_summary_index = -1
        
        # Find the last VALID summary message (same logic as filtered history)
        for i in range(len(self.conversation_history) - 1, -1, -1):  # Search backwards
            message = self.conversation_history[i]
            if (message.get('role') == 'assistant' and 
                '<summary' in message.get('content', '')):
                # VALIDATE that this is actually a real summary
                content = message.get('content', '')
                if self._is_valid_summary(content):
                    last_summary_index = i
                    break
                
        if last_summary_index == -1:
            # No previous valid summary, return total tokens
            print(f"🔢 No valid summary found - using total tokens: {self.token_usage['total_tokens']}")
            return self.token_usage['total_tokens']
        
        # Count tokens in messages after last VALID summary
        # This is approximate - we'd need to track per-message tokens for exact count
        messages_after_summary = self.conversation_history[last_summary_index + 1:]
        estimated_tokens = sum(len(msg.get('content', '')) // 4 for msg in messages_after_summary)
        
        print(f"🔢 Tokens since last valid summary: {estimated_tokens} (from {len(messages_after_summary)} messages)")
        return estimated_tokens

    def _generate_detailed_conversation_summary(self, is_mid_task=False) -> str:
        """Generate comprehensive summary of messages since last summary"""
        
        # Find the latest VALID summary message index (same validation as other functions)
        latest_summary_index = -1
        for i in range(len(self.conversation_history) - 1, -1, -1):  # Search backwards
            message = self.conversation_history[i]
            if (message.get('role') == 'assistant' and 
                '<summary' in message.get('content', '')):
                # VALIDATE that this is actually a real summary
                content = message.get('content', '')
                if self._is_valid_summary(content):
                    latest_summary_index = i
                    break
        
        # Get messages to summarize (only NEW messages since last summary)
        if latest_summary_index == -1:
            # No previous summary, summarize everything except system prompt
            messages_to_summarize = self.conversation_history[1:]  # Skip system prompt
            print(f"📋 Summarizing entire conversation: {len(messages_to_summarize)} messages")
        else:
            # Summarize only messages since last summary
            messages_to_summarize = self.conversation_history[latest_summary_index + 1:]
            print(f"📋 Summarizing {len(messages_to_summarize)} messages since last summary")
        
        # Prepare conversation for summarization
        conversation_text = ""
        for i, message in enumerate(messages_to_summarize):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            conversation_text += f"\n[{role.upper()}]: {content}\n"
        
        # Create comprehensive summary prompt
        summary_prompt = f"""Create a comprehensive, detailed summary of this entire project conversation. This summary will be used as context for future updates to this codebase.

CONVERSATION TO SUMMARIZE:
{conversation_text}

PROJECT CONTEXT:
- Project ID: {self.project_id}
- Total tokens used: {self.token_usage['total_tokens']:,}
- Files in project: {len(self.project_files)}

REQUIRED SUMMARY SECTIONS:

1. **User Requirements & Objectives**
   - List every user request and requirement mentioned
   - Include both major features and minor changes
   - Note any evolving or changing requirements

2. **Implementation Details**
   - All files created, updated, or read
   - Terminal commands executed and their purposes
   - Dependencies added or modified
   - Configuration changes made

3. **Technical Architecture**
   - Current file structure and organization
   - Key components and their relationships
   - Important identifiers, functions, and classes
   - Design patterns and conventions used

4. **Issues & Solutions**
   - Errors encountered and how they were resolved
   - Debugging steps taken
   - Important fixes and workarounds
   - Things to watch out for in future development

5. **Project State**
   - Current functionality and features
   - What's working and what's in progress
   - Testing status and known limitations
   - Next steps or areas for improvement

6. **Development Context**
   - Important decisions made and reasoning
   - Alternative approaches considered
   - Best practices followed
   - Conventions established

7. **File Tree & Changes**
   - Current project structure
   - Recently modified files
   - Important file locations and purposes

""" + ("""
8. **CURRENT TASK STATUS & CONTINUATION** ⚠️ MID-TASK SUMMARY
   - What task is currently in progress (analyze the most recent messages)
   - What was just completed in the latest actions
   - What needs to be done next to complete the current task
   - Any pending actions or iterations that were interrupted by token limit
   - Specific next steps for seamless task continuation""" if is_mid_task else "") + """

Make this summary extremely detailed and comprehensive. Include specific file names, function names, command outputs, error messages, and any other details that would help a developer understand the complete context of this project. This summary will replace all previous conversation history, so it must capture everything important.

IMPORTANT: Write this as if explaining the project to a new developer who needs to understand everything that has happened so far."""

        try:
            # Generate summary using API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical writer who creates comprehensive project documentation. Create detailed summaries that capture all important context for software development projects."},
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=10000,  # Allow for very detailed summary
                temperature=0.1,   # Keep it factual and consistent
            )
            
            summary_content = response.choices[0].message.content
            
            # Track token usage for summary generation
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self.token_usage['prompt_tokens'] = usage.prompt_tokens
                self.token_usage['completion_tokens'] = usage.completion_tokens
                self.token_usage['total_tokens'] = usage.total_tokens
                
                print(f"📊 Summary generation used: {usage.total_tokens} tokens")
            
            return summary_content
            
        except Exception as e:
            print(f"❌ Error generating conversation summary: {e}")
            return None

    def _is_valid_summary(self, content: str) -> bool:
        """Validate that a summary is actually a proper summary, not broken garbage"""
        if not content or len(content) < 500:  # Real summaries should be substantial
            return False
            
        return True

    def _reset_token_tracking_after_summary(self):
        """Reset token tracking to start fresh count after summary"""
        print(f"🔄 Resetting token count from {self.token_usage['total_tokens']:,} to 0")
        self.token_usage = {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }

    def _get_filtered_conversation_history(self) -> list:
        """Get conversation history from latest summary point onwards for model context"""
        
        if not self.conversation_history:
            return []
        
        # Find the latest VALID summary message index
        latest_summary_index = -1
        for i in range(len(self.conversation_history) - 1, -1, -1):  # Search backwards
            message = self.conversation_history[i]
            if (message.get('role') == 'assistant' and 
                '<summary' in message.get('content', '')):
                # VALIDATE that this is actually a real summary, not broken garbage
                content = message.get('content', '')
                if self._is_valid_summary(content):
                    latest_summary_index = i
                    print(f"✅ Found valid summary at index {i}")
                    break
                else:
                    print(f"⚠️ Skipping invalid summary at index {i} (too short or incomplete)")
        
        if latest_summary_index == -1:
            # No summary found, return all messages until we hit 20k tokens, then only current session
            print(f"📝 No summary found - using full conversation history: {len(self.conversation_history)} messages")
            api_compatible_messages = []
            for message in self.conversation_history:
                clean_message = {
                    "role": message["role"],
                    "content": message["content"]
                }
                api_compatible_messages.append(clean_message)
            return api_compatible_messages
        
        # CRITICAL FIX: Use summary + messages from current session only
        # When summary exists, we send: system + summary + current session messages
        system_prompt = self.conversation_history[0]
        raw_summary_message = self.conversation_history[latest_summary_index]
        
        # Include messages from current session (after the summary)
        messages_after_summary = self.conversation_history[latest_summary_index + 1:]
        
        # Check if these are truly current session or old accumulated messages
        # For now, include them but we need to track session boundaries properly
        filtered_messages = [system_prompt, raw_summary_message] + messages_after_summary
        print(f"📝 Using filtered conversation: system + summary + {len(messages_after_summary)} session messages = {len(filtered_messages)} total")
        
        # Apply file read deduplication to reduce token usage
        deduplicated_messages = self._deduplicate_file_reads(filtered_messages)
        print(f"📝 After deduplication: {len(deduplicated_messages)} messages (saved {len(filtered_messages) - len(deduplicated_messages)} messages)")
        
        # Remove metadata from messages for API compatibility
        api_compatible_messages = []
        for message in deduplicated_messages:
            clean_message = {
                "role": message["role"],
                "content": message["content"]
            }
            api_compatible_messages.append(clean_message)
        
        
        return api_compatible_messages

    def _deduplicate_file_reads(self, messages: list) -> list:
        """Remove duplicate file read results, keeping only the LATEST read of each file"""
        
        # STEP 1: Find all file reads and identify latest occurrence of each file
        file_reads = {}  # file_path -> [(index, message), ...]
        
        for i, message in enumerate(messages):
            content = message.get('content', '')
            role = message.get('role', '')
            
            # Check if this is a file content response
            if (role == 'user' and 
                content.startswith('File content for ') and 
                '```' in content):
                
                try:
                    # Extract file path from message
                    file_path = content.split('File content for ')[1].split(':')[0].strip()
                    
                    if file_path not in file_reads:
                        file_reads[file_path] = []
                    file_reads[file_path].append((i, message))
                    
                except Exception as e:
                    print(f"  ⚠️ Failed to parse file read message: {e}")
        
        # STEP 2: For each file, keep only the LATEST read, compress earlier ones
        indices_to_compress = set()
        
        for file_path, reads in file_reads.items():
            if len(reads) > 1:
                # Multiple reads of this file - compress all but the latest
                latest_index = max(reads, key=lambda x: x[0])[0]
                
                for index, message in reads:
                    if index != latest_index:
                        indices_to_compress.add(index)
                        print(f"  🔄 Will compress earlier read: {file_path} (message #{index})")
                
                print(f"  📖 Keeping latest read: {file_path} (message #{latest_index})")
        
        # STEP 3: Build deduplicated message list
        deduplicated = []
        
        for i, message in enumerate(messages):
            if i in indices_to_compress:
                # This is an earlier read that should be compressed
                content = message.get('content', '')
                try:
                    file_path = content.split('File content for ')[1].split(':')[0].strip()
                    short_message = {
                        "role": "user",
                        "content": f"File '{file_path}' content was read (earlier version, compressed). Latest version available in recent messages."
                    }
                    deduplicated.append(short_message)
                    print(f"  ✂️ Compressed: {file_path} ({len(content)} chars -> {len(short_message['content'])} chars)")
                except Exception:
                    # Fallback: keep original if parsing fails
                    deduplicated.append(message)
            else:
                # Keep message as-is (not a duplicate file read)
                deduplicated.append(message)
        
        return deduplicated

    def _generate_realtime_file_tree(self) -> str:
        """Generate real-time file tree for current project state"""
        try:
            # Refresh project files from VPS
            self._scan_project_files_via_api()
            
            if not self.project_files:
                return "No files found in project"
            
            # Define files/folders to exclude - comprehensive list
            exclude_patterns = [
                # Dependencies and build artifacts
                'node_modules', '__pycache__', '.git', '.vscode', '.idea',
                'dist', 'build', '.next', '.vite', 'coverage', '.mypy_cache',
                '.pytest_cache', '.tox', 'venv', '.venv', 'env', '.env',
                
                # Python virtual environments (all common names)
                'test_env', 'backend_env', 'frontend_env', 'myenv', 'virtualenv',
                'bin', 'lib', 'site-packages', 'Scripts', 'Include', 'Lib',
                'pyvenv.cfg', 'activate', 'activate.csh', 'activate.fish', 'Activate.ps1',
                
                # Lock files and package managers
                'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
                'Pipfile.lock', 'requirements-dev.txt', 'requirements.lock',
                
                # Environment and config files
                '.DS_Store', 'Thumbs.db', '.env.local', '.env.development', 
                '.env.production', '.env.test', '.env.staging',
                
                # Temporary and debug files
                '*.pyc', '*.pyo', '*.log', '*.tmp', '*.temp', '*.bak', '*.swp',
                'debug_output.txt', 'stderr.txt', 'stdout.txt', 'output.txt',
                'error.log', 'access.log', 'debug.log', 'test.log',
                
                # Old/backup files
                '*-old.py', '*-backup.py', '*-copy.py', '*.old', '*.backup',
                'python-error-checker-old.py', 'error-checker-backup.py',
                
                # IDE and editor files
                '.vscode', '.idea', '*.suo', '*.user', '.vs', '.eclipse',
                '*.code-workspace', '.sublime-project', '.sublime-workspace',
                
                # OS files
                '.DS_Store', 'Thumbs.db', 'desktop.ini', '.directory'
            ]
            
            # Sort files by path for consistent tree structure
            sorted_files = sorted(self.project_files.keys())
            
            # Track filtering for debugging
            total_files = len(sorted_files)
            filtered_count = 0
            
            # Build tree structure with better formatting
            tree_structure = {}
            
            # Build hierarchical structure
            for file_path in sorted_files:
                # Skip hidden files
                parts = file_path.split('/')
                if any(part.startswith('.') for part in parts):
                    filtered_count += 1
                    continue
                    
                # Skip excluded patterns - improved filtering
                should_skip = False
                for pattern in exclude_patterns:
                    # Handle directory exclusions (e.g., 'test_env/')
                    if f'/{pattern}/' in f'/{file_path}/':
                        should_skip = True
                        break
                    # Handle file extensions and specific files
                    if pattern.startswith('*'):
                        if file_path.endswith(pattern[1:]):
                            should_skip = True
                            break
                    # Handle exact matches and contains
                    elif pattern in file_path or file_path.endswith(pattern):
                        should_skip = True
                        break
                        
                if should_skip:
                    filtered_count += 1
                    continue
                
                # Build tree structure
                current = tree_structure
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                # Add file
                current[parts[-1]] = None
            
            # Convert tree structure to string
            def build_tree_lines(tree, prefix="", is_last=True):
                lines = []
                items = list(tree.items())
                for i, (name, subtree) in enumerate(items):
                    is_last_item = i == len(items) - 1
                    if subtree is None:  # It's a file
                        lines.append(f"{prefix}{'└── ' if is_last_item else '├── '}{name}")
                    else:  # It's a directory
                        lines.append(f"{prefix}{'└── ' if is_last_item else '├── '}{name}/")
                        extension = "    " if is_last_item else "│   "
                        lines.extend(build_tree_lines(subtree, prefix + extension, is_last_item))
                return lines
            
            tree_lines = ["Project Structure:"]
            tree_lines.extend(build_tree_lines(tree_structure))
            
            # Add filtering summary for debugging
            included_files = total_files - filtered_count
            print(f"📊 File tree filtering: {included_files}/{total_files} files included ({filtered_count} filtered out)")
            
            return '\n'.join(tree_lines)
            
        except Exception as e:
            print(f"⚠️ Error generating file tree: {e}")
            return f"Error loading file tree: {e}"

    def _load_read_files_tracking(self):
        """Load project-specific read files tracking from JSON file"""
        read_files_dir = self.backend_dir / "project_read_files"
        read_files_dir.mkdir(exist_ok=True)
        
        read_files_file = read_files_dir / f"{self.project_id}_read_files.json"
        
        if read_files_file.exists():
            with open(read_files_file, 'r', encoding='utf-8') as f:
                read_files_data = json.load(f)
                self.read_files_persistent = set(read_files_data.get('read_files', []))
            print(f"📚 Loaded read files tracking from: {read_files_file}")
            print(f"📖 Previously read files: {len(self.read_files_persistent)} files")
        else:
            print(f"⚠️  No read files tracking found at: {read_files_file}")
    
    def _save_read_files_tracking(self):
        """Save project-specific read files tracking to JSON file"""
        read_files_dir = self.backend_dir / "project_read_files"
        read_files_dir.mkdir(exist_ok=True)
        
        read_files_file = read_files_dir / f"{self.project_id}_read_files.json"
        
        read_files_data = {
            "project_id": self.project_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "read_files": list(self.read_files_persistent),
            "total_files_read": len(self.read_files_persistent)
        }
        
        with open(read_files_file, 'w', encoding='utf-8') as f:
            json.dump(read_files_data, f, indent=2, ensure_ascii=False)
        
        print(f"📚 Saved read files tracking to: {read_files_file}")


    def _setup_project_via_api(self, project_name: str) -> str:
        """Create project via API"""
        try:
            # Check if project already exists
            projects_response = requests.get(f"http://localhost:8000/api/projects")
            if projects_response.status_code == 200:
                existing_projects = projects_response.json().get('projects', [])
                for project in existing_projects:
                    # VPS API uses 'id' field directly
                    if project.get('id') == project_name or project.get('name') == project_name:
                        print(f"📂 Using existing project: {project_name} (ID: {project['id']})")
                        return project['id']
            
            # Create new project using VPS API format
            print(f"🔄 Creating new project via VPS API: {project_name}")
            create_payload = {
                "project_id": project_name,
                "files": {}  # Empty files initially, will be populated by AI
            }
            
            response = requests.post(f"http://localhost:8000/api/projects", json=create_payload)
            if response.status_code == 200:
                project_data = response.json()
                print(f"✅ Project created successfully via VPS API")
                
                # Check for both Python and TypeScript validation errors during project creation
                python_errors = project_data['project'].get('python_errors', '')
                python_check_status = project_data['project'].get('python_check_status', {})
                typescript_errors = project_data['project'].get('typescript_errors', '')
                typescript_check_status = project_data['project'].get('typescript_check_status', {})
                
                # Log Python check execution status
                if python_check_status.get("executed"):
                    status_msg = "✅ Success" if python_check_status.get("success") else "❌ Failed"
                    if python_check_status.get("error"):
                        status_msg += f" - {python_check_status['error']}"
                    print(f"🐍 Python error check during project creation: {status_msg}")
                
                # Log TypeScript check execution status
                if typescript_check_status.get("executed"):
                    status_msg = "✅ Success" if typescript_check_status.get("success") else "❌ Failed"
                    if typescript_check_status.get("error"):
                        status_msg += f" - {typescript_check_status['error']}"
                    print(f"📘 TypeScript error check during project creation: {status_msg}")
                
                # Collect all errors
                all_errors = []
                if python_errors:
                    print(f"⚠️ Python validation errors found during project creation:")
                    print(python_errors)
                    all_errors.append(f"Python errors:\n{python_errors}")
                    
                if typescript_errors:
                    print(f"⚠️ TypeScript validation errors found during project creation:")
                    print(typescript_errors)
                    all_errors.append(f"TypeScript errors:\n{typescript_errors}")
                
                # Add all errors to conversation history
                if all_errors:
                    error_message = {
                        "role": "user", 
                        "content": f"Project created but validation found issues:\n\n{'\n\n'.join(all_errors)}\n\nPlease fix these errors."
                    }
                    self.conversation_history.append(error_message)
                
                # VPS API returns the project info with 'id' field
                return project_data['project']['id']
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating project via API: {e}")
            raise

    def _read_file_via_api(self, file_path: str) -> str:
        """Read file content via API"""
        try:
            # VPS API uses GET with file path in URL
            response = requests.get(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}")
            
            if response.status_code == 200:
                return response.json().get('content', '')
            else:
                print(f"⚠️ Error reading file {file_path}: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"⚠️ Error reading file {file_path} via API: {e}")
            return ""

    def _read_file_via_api(self, file_path: str, start_line: str = None, end_line: str = None) -> str:
        """Read file content from project via VPS API"""
        try:
            # Call VPS API to read file
            response = requests.get(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', '')
                
                # Handle line ranges if specified
                if start_line or end_line:
                    lines = content.split('\n')
                    start_idx = int(start_line) - 1 if start_line else 0
                    end_idx = int(end_line) if end_line else len(lines)
                    
                    # Ensure valid range
                    start_idx = max(0, start_idx)
                    end_idx = min(len(lines), end_idx)
                    
                    if start_idx < end_idx:
                        content = '\n'.join(lines[start_idx:end_idx])
                    else:
                        content = ""
                
                return content
            else:
                print(f"❌ Error reading file {file_path}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return None

    def _write_file_via_api(self, file_path: str, content: str) -> dict:
        """Write file content via API and return result with Python errors if any"""
        try:
            # VPS API uses PUT with file path in URL
            payload = {"content": content}
            response = requests.put(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                
                # Log Python check execution status if available
                check_status = result.get("python_check_status", {})
                if check_status.get("executed"):
                    status_msg = "✅ Success" if check_status.get("success") else "❌ Failed"
                    if check_status.get("error"):
                        status_msg += f" - {check_status['error']}"
                    print(f"🐍 Python error check: {status_msg}")
                
                return {
                    "success": True,
                    "python_errors": result.get("python_errors", ""),
                    "python_check_status": check_status,
                    "typescript_errors": result.get("typescript_errors", ""),
                    "typescript_check_status": result.get("typescript_check_status", {})
                }
            else:
                print(f"⚠️ Error writing file {file_path}: {response.status_code} - {response.text}")
                return {"success": False, "python_errors": "", "python_check_status": {}, "typescript_errors": "", "typescript_check_status": {}}
        except Exception as e:
            print(f"⚠️ Error writing file {file_path} via API: {e}")
            return {"success": False, "python_errors": "", "python_check_status": {}}

    def _execute_command_via_api(self, command: str, cwd: str = None) -> dict:
        """Execute command via API"""
        try:
            payload = {
                "command": command,
                "cwd": cwd or "frontend"  # Default to frontend
            }
            response = requests.post(f"{self.api_base_url}/projects/{self.project_id}/execute", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "output": data.get('output', ''),
                    "error": data.get('error', None)
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"⚠️ Error executing command: {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"⚠️ Error executing command via API: {error_msg}")
            return {"success": False, "error": error_msg}

    def _update_file_via_api(self, file_path: str, content: str) -> dict:
        """Update file via API"""
        try:
            payload = {
                "content": content
            }
            response = requests.put(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "updated",
                    "file": data.get('file', file_path)
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"⚠️ Error updating file: {error_msg}")
                return {"status": "error", "error": error_msg}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"⚠️ Error updating file via API: {error_msg}")
            return {"status": "error", "error": error_msg}

    def _rename_file_via_api(self, old_path: str, new_name: str) -> dict:
        """Rename file via API"""
        try:
            payload = {
                "new_name": new_name
            }
            response = requests.patch(f"{self.api_base_url}/projects/{self.project_id}/files/{old_path}/rename", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "renamed",
                    "old_path": old_path,
                    "new_path": data.get('new_path', new_name)
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"⚠️ Error renaming file: {error_msg}")
                return {"status": "error", "error": error_msg}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"⚠️ Error renaming file via API: {error_msg}")
            return {"status": "error", "error": error_msg}

    def _delete_file_via_api(self, file_path: str) -> dict:
        """Delete file via API"""
        try:
            response = requests.delete(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "deleted", 
                    "file": data.get('file', file_path)
                }
            elif response.status_code == 405:
                # Method Not Allowed - file deletion not supported by API
                print(f"⚠️ File deletion not supported by API for: {file_path}")
                print(f"💡 Skipping file deletion - continuing with generation...")
                return {
                    "status": "skipped",
                    "message": "File deletion not supported by API",
                    "file": file_path
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"⚠️ Error deleting file: {error_msg}")
                return {"status": "error", "error": error_msg}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"⚠️ Error deleting file via API: {error_msg}")
            return {"status": "error", "error": error_msg}

    
    def _ensure_folder_structure(self):
        """Create proper folder structure for organized development"""
        folders = [
            'src/pages',
            'src/components/ui',  # Already exists
            'src/components/common',
            'src/hooks',
            'src/lib',
            'src/types'
        ]
        
        for folder in folders:
            (self.project_dir / folder).mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Ensured proper folder structure")
    
    def _clean_default_routes(self):
        """Remove default boilerplate routes and create clean starting point"""
        try:
            # Remove default page files
            default_pages = ['HomePage.tsx', 'SettingsPage.tsx', 'ProfilePage.tsx']
            for page in default_pages:
                page_file = self.project_dir / 'src' / 'pages' / page
                if page_file.exists():
                    page_file.unlink()
            
            # Create minimal App.tsx with no default routes
            app_content = '''import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from '@/components/ui/breadcrumb'
import { Separator } from '@/components/ui/separator'

function WelcomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <h1 className="text-4xl font-bold tracking-tight">Welcome</h1>
      <p className="text-muted-foreground text-lg text-center max-w-md">
        Your application is ready. New pages will appear here as you create them.
      </p>
    </div>
  )
}

function App() {
  return (
    <Router>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <AppSidebar />
          <main className="flex-1">
            <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
              <SidebarTrigger className="-ml-1" />
              <Separator orientation="vertical" className="mr-2 h-4" />
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbPage>Application</BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            </header>
            <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
              <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min p-6">
                <Routes>
                  <Route path="/" element={<WelcomePage />} />
                </Routes>
              </div>
            </div>
          </main>
        </div>
      </SidebarProvider>
    </Router>
  )
} 

export default App'''
            
            app_file = self.project_dir / 'src' / 'App.tsx'
            with open(app_file, 'w') as f:
                f.write(app_content)
            
            # Create minimal sidebar with no default routes
            sidebar_content = '''import { useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Home } from 'lucide-react'
import { cn } from '@/lib/utils'

// Routes will be dynamically added here by the AI system
const baseRoutes = [
  {
    title: 'Home',
    url: '/',
    icon: Home,
  },
]

export function AppSidebar() {
  const location = useLocation()

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600">
            <Home className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">My App</h2>
            <p className="text-xs text-muted-foreground">v1.0.0</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-4">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {baseRoutes.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton 
                    asChild
                    className={cn(
                      "w-full justify-start",
                      location.pathname === item.url && "bg-accent text-accent-foreground"
                    )}
                  >
                    <a href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarImage src="/placeholder-avatar.jpg" />
            <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xs">
              JD
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">John Doe</p>
            <p className="text-xs text-muted-foreground truncate">john@example.com</p>
          </div>
          <Badge variant="secondary" className="text-xs">Pro</Badge>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}'''
            
            sidebar_file = self.project_dir / 'src' / 'components' / 'app-sidebar.tsx'
            with open(sidebar_file, 'w') as f:
                f.write(sidebar_content)
            
            print(f"🧹 Cleaned default routes - project ready for new pages")
            
        except Exception as e:
            print(f"⚠️ Error cleaning default routes: {e}")

    def _scan_project_files_via_api(self):
        """Scan LOCAL project directory and build file tree"""
        self.project_files = {}
        
        # Local project path (matches local-api.py structure)
        local_projects_path = Path.home() / "local-projects" / "projects" / self.project_id
        
        print(f"🔍 Scanning LOCAL project directory: {local_projects_path}")
        
        if not local_projects_path.exists():
            print(f"⚠️ Local project directory not found: {local_projects_path}")
            return
            
        try:
            # AGGRESSIVE filtering - only include relevant files
            exclude_dirs = {
                'test_env', 'venv', '.venv', 'env', '.env', 'myenv', 'backend_env',
                'bin', 'lib', 'site-packages', 'Scripts', 'Include', 'Lib',
                'node_modules', '__pycache__', '.git', '.vscode', '.idea',
                'dist', 'build', '.next', '.vite', 'coverage', '.mypy_cache',
                '.pytest_cache', '.tox'
            }
            
            exclude_files = {
                'debug_output.txt', 'stderr.txt', 'stdout.txt', 'output.txt',
                'python-error-checker-old.py', 'error-checker-backup.py',
                'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                '.DS_Store', 'Thumbs.db', 'pyvenv.cfg'
            }
            
            total_found = 0
            filtered_out = 0
            
            # Recursively scan the local project directory
            for root, dirs, files in os.walk(local_projects_path):
                # Filter out excluded directories AT THE DIRECTORY LEVEL
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    total_found += 1
                    file_path = Path(root) / file
                    
                    # Skip excluded files
                    if file in exclude_files:
                        filtered_out += 1
                        continue
                        
                    # Skip files with excluded extensions
                    if file.endswith(('.pyc', '.pyo', '.log', '.tmp', '.bak', '.swp')):
                        filtered_out += 1
                        continue
                    
                    # Convert to relative path from project root
                    try:
                        rel_path = file_path.relative_to(local_projects_path)
                        rel_path_str = str(rel_path).replace('\\\\', '/')  # Normalize path separators
                        
                        self.project_files[rel_path_str] = {
                            'path': rel_path_str,
                            'name': file,
                            'size': file_path.stat().st_size if file_path.exists() else 0,
                            'type': 'file'
                        }
                    except Exception as e:
                        print(f"⚠️ Error processing file {file_path}: {e}")
                        filtered_out += 1
                        continue
            
            included_count = total_found - filtered_out
            print(f"📁 LOCAL scan complete: {included_count}/{total_found} files included ({filtered_out} filtered out)")
            
        except Exception as e:
            print(f"⚠️ Error scanning LOCAL project files: {e}")

    def get_project_context(self) -> str:
        """Generate comprehensive project context with file tree"""
        if not self.project_files:
            return ""
        
        context = "\n\nCURRENT PROJECT STATE:\n"
        context += f"Project Directory: {self.project_name}\n"
        context += "This is a complete Vite + React + TypeScript + shadcn/ui + React Router boilerplate.\n\n"
        
        context += "🏗️ BOILERPLATE INCLUDES:\n"
        context += "- ⚡ Vite for fast development\n"
        context += "- ⚛️ React 18 with TypeScript\n"
        context += "- 🎨 Tailwind CSS (fully configured)\n"
        context += "- 🧩 shadcn/ui components (ALL COMPONENTS AVAILABLE: accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toggle-group, toggle, tooltip)\n"
        context += "- 🛣️ React Router for navigation\n"
        context += "- 🎯 Lucide React icons\n"
        context += "- 📁 Proper TypeScript path aliases (@/*)\n"
        context += "- 🗂️ Organized folder structure (pages/, components/, hooks/, etc.)\n\n"
        
        # Get existing routes information
        routes_info = self._get_routes_info()
        
        context += f"🛣️ EXISTING ROUTES & PAGES:\n"
        if routes_info['routes'] and len(routes_info['routes']) > 1:
            for route in routes_info['routes']:
                if route['component'] != 'WelcomePage':  # Don't show internal welcome page
                    context += f"- {route['path']} → {route['component']} (in pages/{route['component']}.tsx)\n"
        else:
            context += "- / → WelcomePage (built-in welcome page)\n"
            context += "- 📝 This is a CLEAN project - no default routes\n"
            context += "- 🎯 New pages you create will automatically be added here\n"
        context += "\n"
        
        # Get route groups information
        route_groups_info = self._get_route_groups_info()
        context += f"📂 CURRENT ROUTE GROUPS:\n"
        if route_groups_info:
            for group_name, routes in route_groups_info.items():
                context += f"- {group_name}: {len(routes)} routes\n"
                for route in routes:
                    context += f"  └── {route['label']} ({route['url']})\n"
        else:
            context += "- No route groups configured yet\n"
        context += "\n"
        
        context += "📂 CURRENT FILE STRUCTURE:\n"
        
        # Create organized tree structure
        def build_tree():
            tree = {}
            for file_path in sorted(self.project_files.keys()):
                parts = Path(file_path).parts
                current = tree
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = "file"
            return tree
        
        def print_tree(tree, prefix="", is_last=True):
            result = ""
            items = list(tree.items())
            for i, (name, subtree) in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "
                result += f"{prefix}{current_prefix}{name}\n"
                
                if isinstance(subtree, dict):
                    extension = "    " if is_last_item else "│   "
                    result += print_tree(subtree, prefix + extension, is_last_item)
            return result
        
        tree = build_tree()
        context += f"{self.project_name}/\n"
        context += print_tree(tree)
        
        # Add file contents for key files to give model better context
        key_files = ['frontend/src/App.tsx', 'frontend/src/main.tsx', 'frontend/src/index.css']
        context += f"\n📄 KEY FILE CONTENTS:\n"
        
        for file_path in key_files:
            if file_path in self.project_files:
                try:
                    content = self._read_file_via_api(file_path)
                    if content:
                        context += f"\n{file_path}:\n```\n{content}\n```\n"
                except Exception as e:
                    context += f"\n{file_path}: (Error reading: {e})\n"
        
        # Add todo status if todos exist
        todo_status = self._get_todo_status_summary()
        if todo_status:
            context += todo_status
        
        context += f"\n📊 SUMMARY:\n"
        context += f"- Total files: {len(self.project_files)}\n"
        context += f"- Complete boilerplate with navigation, styling, and routing\n"
        context += f"- Ready for development with npm run dev\n"
        
        return context

    def _get_routes_info(self) -> dict:
        """Extract route information from App.tsx and sidebar"""
        routes = []
        
        # Try to read App.tsx to extract existing routes
        try:
            content = self._read_file_via_api('frontend/src/App.tsx')
            if content:
                # Extract route patterns
                import re
                route_pattern = r'<Route\s+path="([^"]+)"\s+element={<(\w+)\s*/?>}\s*/>'
                matches = re.findall(route_pattern, content)
                
                for path, component in matches:
                    routes.append({
                        'path': path,
                        'component': component
                    })
                    
        except Exception as e:
            print(f"⚠️ Could not read routes from App.tsx: {e}")
        
        return {'routes': routes}

    def _get_route_groups_info(self) -> dict:
        """Extract route groups information from sidebar"""
        route_groups = {}
        
        # Try to read app-sidebar.tsx to extract route groups
        try:
            content = self._read_file_via_api('frontend/src/components/app-sidebar.tsx')
            if content:
                # Extract routeGroups array
                import re
                groups_pattern = r'const routeGroups = \[(.*?)\]'
                groups_match = re.search(groups_pattern, content, re.DOTALL)
                
                if groups_match:
                    groups_content = groups_match.group(1)
                    
                    # Extract individual groups
                    group_pattern = r'{\s*title:\s*["\']([^"\']+)["\'][^}]*items:\s*\[(.*?)\]\s*}'
                    group_matches = re.findall(group_pattern, groups_content, re.DOTALL)
                    
                    for group_title, items_content in group_matches:
                        route_groups[group_title] = []
                        
                        # Extract individual items
                        item_pattern = r'{\s*title:\s*["\']([^"\']+)["\'][^}]*url:\s*["\']([^"\']+)["\'][^}]*}'
                        item_matches = re.findall(item_pattern, items_content)
                        
                        for item_title, item_url in item_matches:
                            route_groups[group_title].append({
                                'label': item_title,
                                'url': item_url
                            })
                    
        except Exception as e:
            print(f"⚠️ Could not read route groups from sidebar: {e}")
        
        return route_groups

    def _add_route_to_app(self, path: str, component: str, icon: str, label: str, group: str = None):
        """Automatically add a route to App.tsx and update sidebar"""
        # Update App.tsx with the route
        self._update_routes_in_app(path, component)

        
        # Check if route already exists
        if f'url: "{path}"' in content:
            print(f"🔄 Route {path} already exists in sidebar")
            return
        
        # Add icon import if not present
        if f'{icon}' not in content:
            # Find the lucide-react import and add the icon
            import_pattern = r"import \{\s*([^}]+)\s*\} from ['\"]lucide-react['\"]"
            match = re.search(import_pattern, content)
            if match:
                current_imports = match.group(1).strip()
                import_list = [imp.strip() for imp in current_imports.split(',')]
                if icon not in import_list:
                    import_list.append(icon)
                    new_imports = ',\n  '.join(import_list)
                    new_import_line = f"import {{ \n  {new_imports}\n}} from \"lucide-react\""
                    content = content.replace(match.group(0), new_import_line)
        
        # Now try to find the target group and add the route
        target_group = group or "Overview"
        
        # Look for the group and add the route item
        group_pattern = rf'(\{{[\s\S]*?title:\s*"{re.escape(target_group)}"[\s\S]*?items:\s*\[)([\s\S]*?)(\][\s\S]*?\}})'
        group_match = re.search(group_pattern, content)
        
        if group_match:
            # Add to existing group
            items_section = group_match.group(2)
            new_item = f'      {{ title: "{label}", url: "{path}", icon: {icon} }},'
            
            # Add the new item at the end of the items array
            if items_section.strip():
                updated_items = f"{items_section}\n{new_item}"
            else:
                updated_items = f"\n{new_item}\n      "
            
            content = content.replace(group_match.group(2), updated_items)
            
        else:
            # Create new group - find the routeGroups array end and add before it
            route_groups_match = re.search(r'const routeGroups = \[([\s\S]*?)\]', content)
            if route_groups_match:
                existing_groups = route_groups_match.group(1)
                new_group = f"""  {{
    title: "{target_group}",
    items: [
      {{ title: "{label}", url: "{path}", icon: {icon} }},
    ]
  }},
"""
                # Add the new group before the closing bracket
                updated_groups = f"{existing_groups}{new_group}"
                content = content.replace(route_groups_match.group(1), updated_groups)
                print(f"📝 Created new group: {target_group}")
        
        # Write updated content via API
        self._write_file_via_api('frontend/src/components/app-sidebar.tsx', content)

    def _apply_streaming_action(self, action: Dict):
        """Apply a single action from streaming response immediately using existing functions"""
        if action['type'] == 'file':
            file_path = action['path']
            content = action['content']
            
            # Use same protection logic as existing _process_actions
            protected_files = [
                'package.json', 'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json',
                'src/App.tsx', 'frontend/src/App.tsx', 'backend/app.py'
            ]
            if any(file_path.endswith(protected) or file_path == protected for protected in protected_files):
                print(f"\n🚫 BLOCKED: {file_path}")
                return
            
            # Clean content and apply file - same as existing logic
            cleaned_content = self._clean_file_content(content)
            result = self._write_file_via_api(file_path, cleaned_content)
            if result["success"]:
                success_msg = f"\n✅ Applied: {file_path}"
                if result["python_errors"]:
                    success_msg += f"\n\n{result['python_errors']}"
                print(success_msg)
                
        elif action['type'] == 'read_file':
            # Handle read_file action
            file_path = action.get('path')
            start_line = action.get('start_line')
            end_line = action.get('end_line')
            
            if file_path:
                file_content = self._read_file_via_api(file_path, start_line, end_line)
                if file_content is not None:
                    print(f"\n📖 Read: {file_path}")
                    if start_line or end_line:
                        print(f"   Lines: {start_line or 1}-{end_line or 'end'}")
                    
                    # Add the file content as an assistant message to continue the conversation
                    content_preview = file_content[:200] + "..." if len(file_content) > 200 else file_content
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": f"File content for `{file_path}`:\n\n```\n{file_content}\n```"
                    })
                else:
                    print(f"\n❌ Failed to read: {file_path}")
                    
        elif action['type'] == 'update_file':
            # Handle update_file action (similar to file but with different messaging)
            file_path = action.get('path')
            content = action.get('content', '')
            
            if file_path and content:
                # Clean content and apply file
                cleaned_content = self._clean_file_content(content)
                result = self._write_file_via_api(file_path, cleaned_content)
                if result["success"]:
                    success_msg = f"\n🔄 Updated: {file_path}"
                    if result["python_errors"]:
                        success_msg += f"\n\n{result['python_errors']}"
                    print(success_msg)
                else:
                    print(f"\n❌ Failed to update: {file_path}")
            else:
                print(f"\n❌ Invalid update_file action: missing path or content")
                
        elif action['type'] == 'route':
            # Use existing route processing function
            path = action.get('path')
            component = action.get('component') 
            icon = action.get('icon')
            label = action.get('label')
            group = action.get('group')
            
            if path and component and icon and label:
                try:
                    self._add_route_to_app(path, component, icon, label, group)
                    group_info = f" (group: {group})" if group else ""
                    print(f"\n🛣️ Route: {path} -> {component}{group_info}")
                except Exception as e:
                    print(f"\n❌ Route error: {e}")

    def _process_actions(self, response: str):
        """Extract and execute actions from AI response"""
        # Pattern to match <action type="file" filePath="...">content</action>
        file_action_pattern = r'<action\s+type="file"\s+filePath="([^"]+)">(.*?)</action>'
        file_actions = re.findall(file_action_pattern, response, re.DOTALL)
        
        # Pattern to match <action type="route" path="..." component="..." icon="..." label="...">
        route_action_pattern = r'<action\s+type="route"\s+path="([^"]+)"\s+component="([^"]+)"\s+icon="([^"]+)"\s+label="([^"]+)"(?:\s+group="([^"]+)")?\s*/>'
        route_actions = re.findall(route_action_pattern, response, re.DOTALL)
        
        # Process file actions
        for file_path, content in file_actions:
            try:
                # PROTECT CONFIG FILES AND INFRASTRUCTURE - DO NOT ALLOW MODIFICATIONS
                protected_files = [
                    'package.json', 'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json',
                    'backend/app.py'
                    # NOTE: App.tsx is now allowed for updates in update mode
                    # NOTE: src/components/app-sidebar.tsx is protected in prompt but allowed for route system updates
                ]
                if any(file_path.endswith(protected) or file_path == protected for protected in protected_files):
                    print(f"🚫 BLOCKED: Attempted to modify protected infrastructure file {file_path}")
                    continue
                
                # Clean content - remove markdown backticks and language identifiers
                cleaned_content = self._clean_file_content(content)
                
                # Write file content via API
                success = self._write_file_via_api(file_path, cleaned_content)
                if success:
                    print(f"✅ Updated: {file_path}")
                else:
                    print(f"❌ Failed to update: {file_path}")
                
            except Exception as e:
                print(f"❌ Error updating {file_path}: {e}")
        
        # Process route actions
        for route_match in route_actions:
            try:
                path, component, icon, label = route_match[:4]
                group = route_match[4] if len(route_match) > 4 and route_match[4] else None
                self._add_route_to_app(path, component, icon, label, group)
                group_info = f" (group: {group})" if group else ""
                print(f"🛣️ Added route: {path} -> {component}{group_info}")
            except Exception as e:
                print(f"❌ Error adding route {path}: {e}")
        
        # Refresh file scan after changes
        if file_actions or route_actions:
            self._scan_project_files_via_api()
            # Disabled to prevent package.json modifications
            # self._check_and_install_dependencies()
            print(f"📁 Project now has {len(self.project_files)} files")

    def _add_route_to_app(self, path: str, component: str, icon: str, label: str, group: str = None):
        """Automatically add a route to App.tsx and update sidebar"""
        # Update App.tsx with the route
        self._update_routes_in_app(path, component)
        
        # Update the sidebar with the new route
        self._update_sidebar_routes(path, component, icon, label, group)

    def _update_routes_in_app(self, path: str, component: str):
        """Add route to App.tsx Routes section"""
        content = self._read_file_via_api('frontend/src/App.tsx')
        if not content:
            return
        
        # Add import for the component if not already present
        if f'import {component}' not in content:
            # Add import after existing imports
            import_section = content.split('\n')
            last_import_line = -1
            for i, line in enumerate(import_section):
                if line.strip().startswith('import'):
                    last_import_line = i
            
            if last_import_line >= 0:
                import_section.insert(last_import_line + 1, f"import {component} from './pages/{component}'")
                content = '\n'.join(import_section)
        
        # Add route to Routes section (only if it doesn't exist)
        if f'path="{path}"' not in content:
            # Find the last Route line and add after it with proper indentation
            lines = content.split('\n')
            last_route_index = -1
            
            for i, line in enumerate(lines):
                if '<Route' in line and 'path=' in line:
                    last_route_index = i
            
            if last_route_index != -1:
                # Get indentation from the last route
                last_route_line = lines[last_route_index]
                indent = len(last_route_line) - len(last_route_line.lstrip())
                new_route = ' ' * indent + f'<Route path="{path}" element={{<{component} />}} />'
                
                # Insert the new route after the last route
                lines.insert(last_route_index + 1, new_route)
                content = '\n'.join(lines)
        
        # Write updated content via API
        self._write_file_via_api('frontend/src/App.tsx', content)

    def _update_sidebar_routes(self, path: str, component: str, icon: str, label: str, group: str = None):
        """Add route to AppSidebar component with group support"""
        # Skip dynamic routes (containing :parameter) from sidebar
        if ':' in path:
            print(f"🚫 Skipping dynamic route {path} from sidebar (dynamic routes shouldn't appear in navigation)")
            return
        
        content = self._read_file_via_api('frontend/src/components/app-sidebar.tsx')
        if not content:
            return
        
        # Check if route already exists
        if f'url: "{path}"' in content:
            print(f"🔄 Route {path} already exists in sidebar")
            return
        
        # Add icon import if not present
        if f'{icon}' not in content:
            # Find the lucide-react import and add the icon
            import_pattern = r"import \{\s*([^}]+)\s*\} from ['\"]lucide-react['\"]"
            match = re.search(import_pattern, content)
            if match:
                current_imports = match.group(1).strip()
                import_list = [imp.strip() for imp in current_imports.split(',')]
                if icon not in import_list:
                    import_list.append(icon)
                    new_imports = ',\n  '.join(import_list)
                    new_import_line = f"import {{ \n  {new_imports}\n}} from \"lucide-react\""
                    content = content.replace(match.group(0), new_import_line)
        
        # Convert from baseRoutes to routeGroups structure if needed
        if 'const baseRoutes' in content and 'const routeGroups' not in content:
            print("🔄 Converting sidebar from baseRoutes to routeGroups structure")
            
            # Replace baseRoutes with routeGroups structure
            base_routes_pattern = r'const baseRoutes = \[([\s\S]*?)\]'
            base_match = re.search(base_routes_pattern, content)
            
            if base_match:
                # Convert existing baseRoutes to routeGroups format
                route_groups_replacement = f"""const routeGroups = [
  {{
    title: "Overview",
    items: [
      {{ title: "Home", url: "/", icon: Home }},
    ]
  }},
]"""
                content = re.sub(base_routes_pattern, route_groups_replacement, content)
                
                # Update the rendering part completely
                # Find the SidebarContent section and replace it entirely
                sidebar_content_pattern = r'<SidebarContent className="px-4">([\s\S]*?)</SidebarContent>'
                new_sidebar_content = '''<SidebarContent className="px-4">
        {routeGroups.map((group) => (
          <SidebarGroup key={group.title}>
            <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton 
                      asChild
                      className={cn(
                        "w-full justify-start",
                        location.pathname === item.url && "bg-accent text-accent-foreground"
                      )}
                    >
                      <a href={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </a>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>'''
                content = re.sub(sidebar_content_pattern, new_sidebar_content, content)
                
                # Add SidebarGroupLabel import
                if 'SidebarGroupLabel' not in content:
                    content = content.replace('SidebarGroupContent,', 'SidebarGroupContent,\n  SidebarGroupLabel,')
        
        # Always ensure SidebarGroupLabel import is present when using routeGroups
        if 'const routeGroups' in content and 'SidebarGroupLabel' not in content:
            content = content.replace('SidebarGroupContent,', 'SidebarGroupContent,\n  SidebarGroupLabel,')
        
        # Now try to find the target group and add the route
        target_group = group or "Overview"
        
        # Look for the group and add the route item
        group_pattern = rf'(\{{[\s\S]*?title:\s*"{re.escape(target_group)}"[\s\S]*?items:\s*\[)([\s\S]*?)(\][\s\S]*?\}})'
        group_match = re.search(group_pattern, content)
        
        if group_match:
            # Add to existing group
            items_section = group_match.group(2)
            new_item = f'      {{ title: "{label}", url: "{path}", icon: {icon} }},'
            
            # Add the new item at the end of the items array
            if items_section.strip():
                updated_items = f"{items_section}\n{new_item}"
            else:
                updated_items = f"\n{new_item}\n      "
            
            content = content.replace(group_match.group(2), updated_items)
            
        else:
            # Create new group - find the routeGroups array end and add before it
            route_groups_match = re.search(r'const routeGroups = \[([\s\S]*?)\]', content)
            if route_groups_match:
                existing_groups = route_groups_match.group(1)
                new_group = f"""  {{
    title: "{target_group}",
    items: [
      {{ title: "{label}", url: "{path}", icon: {icon} }},
    ]
  }},
"""
                # Add the new group before the closing bracket
                updated_groups = f"{existing_groups}{new_group}"
                content = content.replace(route_groups_match.group(1), updated_groups)
                print(f"📝 Created new group: {target_group}")
        
        # Write updated content via API
        self._write_file_via_api('frontend/src/components/app-sidebar.tsx', content)

    def _clean_file_content(self, content: str) -> str:
        """Clean file content by removing markdown formatting"""
        content = content.strip()
        
        # Remove markdown code block markers
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line if it's ```language
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        return content.strip()

    def setup_project_environment(self) -> bool:
        """Setup project environment (venv, packages) without starting services"""
        try:
            # Setup the environment using new endpoint
            response = requests.post(f"{self.api_base_url}/projects/{self.project_id}/setup-environment")
            if response.status_code == 200:
                setup_data = response.json()
                
                print(f"🔧 Environment setup completed successfully!")
                print(f"🐍 Backend Ready: {'Yes' if setup_data.get('backend_ready') else 'No'}")
                print(f"⚛️  Frontend Ready: {'Yes' if setup_data.get('frontend_ready') else 'No'}")
                
                # Show any Python errors found during setup
                python_errors = setup_data.get('python_errors')
                if python_errors and python_errors.strip():
                    print(f"\n⚠️  Python errors found during setup:")
                    print(f"   {python_errors}")
                    print(f"   These will need to be fixed before backend can start")
                else:
                    print(f"✅ No Python errors detected")
                
                print(f"\n📝 Environment is ready for development.")
                print(f"🚀 Use <action type='start_backend'/> to start backend when needed")
                print(f"🌐 Use <action type='start_frontend'/> to start frontend when needed")
                
                return True
            else:
                print(f"❌ Error setting up environment: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error setting up environment: {e}")
            return False
    
    def start_preview_and_get_url(self) -> str:
        """DEPRECATED: Start the project preview and return the URL"""
        print("⚠️  WARNING: start_preview_and_get_url is deprecated. Use setup_project_environment() + action tags instead.")
        try:
            # Start the preview (still kept for backward compatibility)
            response = requests.post(f"{self.api_base_url}/projects/{self.project_id}/start-preview")
            if response.status_code == 200:
                preview_data = response.json()
                
                # Handle both old and new API response formats
                frontend_port = preview_data.get('frontend_port') or preview_data.get('port', 3001)
                backend_port = preview_data.get('backend_port', 8001)
                
                # Return the actual VPS IP with the ports
                frontend_url = f"http://localhost:{frontend_port}"
                backend_url = f"http://localhost:{backend_port}"
                
                print(f"🚀 Preview started successfully!")
                print(f"📱 Frontend: {frontend_url} (port {frontend_port})")
                print(f"🔧 Backend:  {backend_url} (port {backend_port})")
                print(f"🌐 Access your project at: {frontend_url}")
                
                # Store URLs for summary generation
                self.preview_url = frontend_url
                self.backend_url = backend_url

                self._write_file_via_api('backend/.env', f'BACKEND_URL={self.backend_url}')
                print('* Backend URL added to .env in backend *')
                
                return frontend_url
            else:
                print(f"❌ Error starting preview: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error starting preview: {e}")
            return None

    def generate_project_summary(self) -> str:
        """Generate comprehensive project summary using conversation history"""
        print(f"\n{'='*60}")
        print("📝 GENERATING PROJECT SUMMARY")
        print("="*60)
        
        # Create project_summaries directory if it doesn't exist
        summaries_dir = self.backend_dir / "project_summaries"
        summaries_dir.mkdir(exist_ok=True)
        
        # Build summary prompt from conversation history
        summary_prompt = _build_summary_prompt(self)
        
        try:
            # Call Groq to generate the summary
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical writer who creates comprehensive project documentation. Create a detailed summary of the implemented project based on the conversation history."},
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            summary_content = response.choices[0].message.content
            
            # Track token usage for non-streaming call
            if hasattr(response, 'usage'):
                usage = response.usage
                self.token_usage['prompt_tokens'] = usage.prompt_tokens
                self.token_usage['completion_tokens'] = usage.completion_tokens
                self.token_usage['total_tokens'] = usage.total_tokens
                
                print(f"📊 Token usage for summary: {usage.total_tokens} tokens")
            
            # Save summary to MD file
            summary_file = summaries_dir / f"{self.project_id}_summary.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            print(f"✅ Project summary generated: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            print(f"❌ Error generating project summary: {e}")
            return None


    def _check_and_install_dependencies(self):
        """Scan project files and add missing dependencies to package.json"""
        try:
            # Read current package.json
            package_json_path = self.project_dir / 'package.json'
            if not package_json_path.exists():
                return
                
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            current_deps = set(package_data.get('dependencies', {}).keys())
            current_dev_deps = set(package_data.get('devDependencies', {}).keys())
            all_current = current_deps | current_dev_deps
            
            # Scan all project files for imports
            needed_packages = set()
            
            for file_info in self.project_files.values():
                if file_info['path'].endswith(('.ts', '.tsx', '.js', '.jsx')):
                    try:
                        with open(file_info['full_path'], 'r') as f:
                            content = f.read()
                        
                        # Find import statements
                        import_pattern = r"import.*?from\s+['\"]([^'\"]+)['\"]"
                        imports = re.findall(import_pattern, content)
                        
                        for import_name in imports:
                            # Skip relative imports
                            if import_name.startswith('.'):
                                continue
                            
                            # Skip path aliases (like @/components, @/lib)
                            if import_name.startswith('@/'):
                                continue
                            
                            # Skip Node.js built-in modules
                            builtin_modules = {'path', 'fs', 'url', 'util', 'crypto', 'os', 'http', 'https', 'stream'}
                            if import_name in builtin_modules:
                                continue
                            
                            # Extract package name (handle scoped packages)
                            if import_name.startswith('@'):
                                # Scoped package like @radix-ui/react-button
                                parts = import_name.split('/')
                                if len(parts) >= 2:
                                    package_name = f"{parts[0]}/{parts[1]}"
                                else:
                                    package_name = import_name
                            else:
                                # Regular package - take first part
                                package_name = import_name.split('/')[0]
                            
                            needed_packages.add(package_name)
                    
                    except Exception as e:
                        print(f"⚠️ Error scanning {file_info['path']}: {e}")
            
            # Find missing packages
            missing_packages = needed_packages - all_current
            
            if missing_packages:
                print(f"📦 Adding missing dependencies to package.json: {', '.join(missing_packages)}")
                
                # Add missing packages to dependencies with latest version
                # BUT preserve existing versions from boilerplate
                if 'dependencies' not in package_data:
                    package_data['dependencies'] = {}
                
                for pkg in missing_packages:
                    # Only add if it's not already in the boilerplate
                    # This prevents overwriting correct versions like tailwindcss v4
                    if pkg not in package_data['dependencies']:
                        package_data['dependencies'][pkg] = 'latest'
                
                # Write updated package.json
                with open(package_json_path, 'w') as f:
                    json.dump(package_data, f, indent=2)
                
                print(f"✅ Added {len(missing_packages)} packages to package.json")
                print("💡 Run 'npm install' to install the new dependencies")
            
        except Exception as e:
            print(f"⚠️ Error checking dependencies: {e}")


    def _process_update_request_with_interrupts(self, user_message: str, mode: str = "update", step_info: dict = None):
        """Process request with interrupt-and-continue pattern - supports both update and step generation modes"""
        
        if mode == "step":
            step_number = step_info.get('step_number', 'N/A')
            step_name = step_info.get('name', 'Unknown Step')
            print(f"\n🎯 STEP MODE: Processing step {step_number} - {step_name}")
        else:
            print(f"\n📝 UPDATE MODE: Processing modification request with read-before-write enforcement")
        
        # Start with system prompt with runtime environment info
        system_prompt = self._load_system_prompt()
        
#         # Add runtime environment information if available
#         if hasattr(self, 'backend_url') and self.backend_url:
#             runtime_info = f"""

# ## RUNTIME ENVIRONMENT (Current Session)

# **IMPORTANT:** Your project is ALREADY running with these URLs:

# - **Backend URL:** {self.backend_url}
# - **Backend API URL:** {self.backend_url}
# - **Frontend URL:** {getattr(self, 'preview_url', 'Not available')}

# **For API Testing:** Use urllib with these actual URLs:
# ```python
# from urllib.request import urlopen
# import json

# # Health check
# response = urlopen("{self.backend_url}/health")
# print(json.loads(response.read()))

# # POST request example
# from urllib.request import Request
# data = json.dumps({{"key": "value"}}).encode()
# req = Request("{self.backend_url}/api/endpoint", data=data, headers={{"Content-Type": "application/json"}})
# response = urlopen(req)
# print(json.loads(response.read()))
# ```

# The backend is accessible at {self.backend_url} - use this for all API testing and internal requests.
# DO NOT try to start the backend or frontend again - they are already running on these accessible URLs.
# """
#             system_prompt += runtime_info
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Use filtered conversation history to manage token limits and summarization
        print("🧹 Using filtered conversation history (from latest summary onwards)...")
        filtered_history = self._get_filtered_conversation_history()
        
        # Apply filtering based on mode
        for msg in filtered_history:
            if msg.get('role') == 'system':
                continue  # Already added system prompt above
            elif msg.get('role') == 'user':
                messages.append(msg)
                print(f"  ✅ Kept user message: {msg['content'][:50]}...")
            elif msg.get('role') == 'assistant':
                # For update mode, skip creation-mode patterns to avoid copying
                if mode == "update" and '<action type="file"' in msg.get('content', ''):
                    print(f"  🚫 Skipped creation-mode assistant message")
                else:
                    messages.append(msg)
                    print(f"  ✅ Kept assistant message")
        
        # Add current user message with real-time file tree
        file_tree = self._generate_realtime_file_tree()
        enhanced_user_message = f"{user_message}\n\n<project_files>\n{file_tree}\n</project_files>"
        messages.append({"role": "user", "content": enhanced_user_message})
        
        # Add current user message to conversation history and save in real-time
        self.conversation_history.append({"role": "user", "content": enhanced_user_message})
        self._save_conversation_history()  # Real-time save - triggers summarization if needed
        
        print(f"🔍 Sending {len(messages)} messages to model:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content_preview = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
            print(f"  {i+1}. {role}: {content_preview}")
        print()
        
        # Start initial generation
        response_content = self._generate_with_interrupts(messages)
        
        # Add final response to conversation history and save in real-time
        if response_content:
            # self.conversation_history.append({"role": "assistant", "content": response_content})
            self._save_conversation_history()  # Real-time save - triggers summarization if needed
        
        if mode == "step":
            print(f"✅ Step {step_info.get('step_number', 'N/A')} processed successfully")
            return True
        else:
            print(f"✅ Update request processed successfully")
            return response_content

    def _generate_with_interrupts(self, messages: list) -> str:
        """Generate response with interrupt-and-continue pattern for read_file actions"""
        print(f"🔄 Starting generation with interrupt support...")
        
        full_response = coder(messages=messages, self=self)

        return full_response

    def _handle_read_file_interrupt(self, action: dict) -> str:
        """Handle read_file action during interrupt"""
        file_path = action.get('path')
        start_line = action.get('start_line')
        end_line = action.get('end_line')
        
        print(f"📖 Reading file: {file_path}")
        if start_line or end_line:
            print(f"   Lines: {start_line or 'start'} to {end_line or 'end'}")
        
        # Read file via API
        file_content = self._read_file_via_api(file_path, start_line, end_line)
        
        if file_content is not None:
            print(f"✅ Successfully read {len(file_content)} characters from {file_path}")
            
            # Track that this file has been read
            self.read_files_tracker.add(file_path)
            self.read_files_persistent.add(file_path)
            print(f"📚 Added '{file_path}' to read files tracker")
            
            # Save read files tracking immediately
            self._save_read_files_tracking()
            
            return file_content
        else:
            print(f"❌ Failed to read file {file_path}")
            return None

    def _handle_run_command_interrupt(self, action: dict) -> str:
        """Handle run_command action during interrupt"""
        command = action.get('command')
        cwd = action.get('cwd')
        
        print(f"💻 Running command: {command}")
        if cwd:
            print(f"   Working directory: {cwd}")

        if cwd not in ['frontend', 'backend']:
            return f"`cwd` must be 'frontend' or 'backend'. It cannot be {cwd}. Do you want to run the test for the frontend or backend?"
        
        # Execute command via API
        command_output = self._execute_command_via_api(command, cwd)
        
        if command_output and command_output.get('success'):
            output = command_output.get('output', '')
            print(f"✅ Command completed successfully")
            print(f"📄 Output length: {len(output)} characters")
            return output
        else:
            error = command_output.get('error', 'Unknown error') if command_output else 'Failed to execute command'
            print(f"❌ Command failed: {error}")
            return f"Command failed: {error}"

    def _handle_update_file_interrupt(self, action: dict) -> str:
        """Handle update_file action during interrupt - update file immediately"""
        file_path = action.get('path') or action.get('filePath')
        file_content = action.get('content', '')
        
        # Remove backticks if present
        file_content = self._remove_backticks_from_content(file_content)
        
        print(f"💾 Updating file: {file_path}")
        print(f"📄 Content length: {len(file_content)} characters")
        
        # Update file via API
        update_result = self._update_file_via_api(file_path, file_content)
        
        if update_result and update_result.get('status') == 'updated':
            print(f"✅ File updated successfully: {file_path}")
            
            # Check for validation errors
            python_errors = update_result.get('python_errors', '')
            typescript_errors = update_result.get('typescript_errors', '')
            
            error_messages = []
            if python_errors:
                print(f"⚠️ Python validation errors found")
                error_messages.append(f"Python errors:\n{python_errors}")
                
            if typescript_errors:
                print(f"⚠️ TypeScript validation errors found")
                error_messages.append(f"TypeScript errors:\n{typescript_errors}")
            
            if error_messages:
                success_msg = f"File '{file_path}' updated successfully.\n\n{'\n\n'.join(error_messages)}"
            else:
                success_msg = f"File '{file_path}' updated successfully"
            
            return success_msg
        else:
            error = update_result.get('error', 'Unknown error') if update_result else 'Failed to update file'
            print(f"❌ File update failed: {error}")
            return None

    def _handle_rename_file_interrupt(self, action: dict) -> str:
        """Handle rename_file action during interrupt - rename file immediately"""
        old_path = action.get('path')
        new_name = action.get('new_name')
        
        if not old_path or not new_name:
            print(f"❌ Missing path or new_name for rename action")
            return None
            
        print(f"🔄 Renaming file: {old_path} -> {new_name}")
        
        # Rename file via API
        rename_result = self._rename_file_via_api(old_path, new_name)
        
        if rename_result and rename_result.get('status') == 'renamed':
            print(f"✅ File renamed successfully: {old_path} -> {new_name}")
            return f"File '{old_path}' renamed to '{new_name}' successfully"
        else:
            error = rename_result.get('error', 'Unknown error') if rename_result else 'Failed to rename file'
            print(f"❌ File rename failed: {error}")
            return None

    def _handle_delete_file_interrupt(self, action: dict) -> str:
        """Handle delete_file action during interrupt - delete file immediately"""
        file_path = action.get('path')
        
        if not file_path:
            print(f"❌ Missing path for delete action")
            return None
            
        print(f"🗑️ Deleting file: {file_path}")
        
        # Delete file via API
        delete_result = self._delete_file_via_api(file_path)
        
        if delete_result and delete_result.get('status') == 'deleted':
            print(f"✅ File deleted successfully: {file_path}")
            return f"File '{file_path}' deleted successfully"
        elif delete_result and delete_result.get('status') == 'skipped':
            print(f"⏭️ File deletion skipped: {file_path}")
            return f"File deletion skipped for '{file_path}' (not supported by API)"
        else:
            error = delete_result.get('error', 'Unknown error') if delete_result else 'Failed to delete file'
            print(f"❌ File delete failed: {error}")
            return None

    def _remove_backticks_from_content(self, content: str) -> str:
        """Remove backticks from file content if they're present"""
        import re
        
        # Check for code block pattern: ```language\n...code...\n```
        backtick_pattern = r'^```[a-zA-Z]*\n(.*)\n```$'
        match = re.search(backtick_pattern, content.strip(), re.DOTALL)
        
        if match:
            print("🔧 Removing backticks from file content")
            return match.group(1)
        
        return content

    def _handle_create_file_realtime(self, action: dict):
        """Handle real-time file creation from streaming content"""
        content = action.get('content', '')
        
        # Parse the file action from the accumulated content
        import re
        
        # Look for <action type="file" filePath="...">content</action> or <action type="file" path="...">content</action>
        file_pattern = r'<action\s+type="file"\s+(?:filePath|path)="([^"]*)"[^>]*>(.*?)(?:</action>|$)'
        match = re.search(file_pattern, content, re.DOTALL)
        
        if not match:
            print("❌ Could not parse file creation action")
            print(f"🔍 Content snippet: {content[:200]}...")
            return None
            
        file_path = match.group(1)
        file_content = match.group(2).strip()
        
        if not file_path or not file_content:
            print("❌ Missing file path or content in creation action")
            return None
            
        # Remove backticks if present
        file_content = self._remove_backticks_from_content(file_content)
        
        print(f"🚀 Creating file in real-time: {file_path}")
        
        # Use the existing working file creation function
        result = self._write_file_via_api(file_path, file_content)
        
        if result["success"]:
            print(f"✅ Successfully created file: {file_path}")
            
            # Check both Python and TypeScript errors
            if result["python_errors"]:
                print(f"⚠️ Python validation errors found:")
                print(result["python_errors"])
                
            if result.get("typescript_errors"):
                print(f"⚠️ TypeScript validation errors found:")
                print(result["typescript_errors"])
                
            return {
                'file_path': file_path, 
                'success': True,
                'python_errors': result["python_errors"],
                'typescript_errors': result.get("typescript_errors", "")
            }
        else:
            print(f"❌ File creation failed")
            return None

    def _process_remaining_actions(self, content: str):
        """Process any remaining actions from the complete response"""
        parser = StreamingXMLParser()
        parser.buffer = content
        
        file_actions = []
        route_actions = []
        
        # Extract all actions from the complete response
        while True:
            actions_found = list(parser.process_chunk(""))
            if not actions_found:
                break
            
            for action in actions_found:
                if action.get('type') == 'file':
                    file_actions.append(action)
                elif action.get('type') == 'update_file':
                    file_actions.append(action)
                elif action.get('type') == 'route':
                    route_actions.append(action)
        
        # Process file actions
        for action in file_actions:
            self._process_file_action(action)
        
        # Process route actions
        for action in route_actions:
            self._process_route_action(action)

    def _process_file_action(self, action: dict):
        """Process a single file action (create/update)"""
        file_path = action.get('filePath') or action.get('path')
        content = action.get('content', '')
        
        if not file_path:
            print("❌ File action missing path")
            return
            
        try:
            # Use existing file processing logic
            self._write_file_via_api(file_path, content)
            print(f"✅ Updated: {file_path}")
        except Exception as e:
            print(f"❌ Error processing file {file_path}: {e}")

    def _process_route_action(self, action: dict):
        """Process a single route action"""
        try:
            path = action.get('path')
            component = action.get('component')
            icon = action.get('icon', 'Home')
            label = action.get('label', component)
            group = action.get('group')
            
            if path and component:
                self._add_route_to_app(path, component, icon, label, group)
                group_info = f" (group: {group})" if group else ""
                print(f"🛣️ Added route: {path} -> {component}{group_info}")
        except Exception as e:
            print(f"❌ Error adding route: {e}")
    
    def _handle_start_backend_interrupt(self, action: dict) -> dict:
        """Handle start_backend action during interrupt"""
        print(f"🚀 Starting backend service...")
        
        try:
            # Call the local API to start backend
            import requests
            url = f"{self.api_base_url}/projects/{self.project_id}/start-backend"
            response = requests.post(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Backend started successfully on port {result.get('backend_port')}")
                print(f"🔗 Backend URL: {result.get('backend_url')}")
                
                # Update backend URL in state
                self.backend_url = result.get('backend_url')
                
                self._write_file_via_api('backend/.env', f'BACKEND_URL={self.backend_url}')
                
                return result
            else:
                print(f"❌ Failed to start backend: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting backend: {e}")
            return None
    
    def _handle_start_frontend_interrupt(self, action: dict) -> dict:
        """Handle start_frontend action during interrupt"""
        print(f"🚀 Starting frontend service...")
        
        try:
            # Call the local API to start frontend
            import requests
            url = f"{self.api_base_url}/projects/{self.project_id}/start-frontend"
            response = requests.post(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Frontend started successfully on port {result.get('frontend_port')}")
                print(f"🔗 Frontend URL: {result.get('frontend_url')}")
                
                # Update preview URL in state
                self.preview_url = result.get('frontend_url')
                
                return result
            else:
                print(f"❌ Failed to start frontend: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting frontend: {e}")
            return None
    
    def _handle_restart_backend_interrupt(self, action: dict) -> dict:
        """Handle restart_backend action during interrupt"""
        print(f"🔄 Restarting backend service...")
        
        try:
            # Call the local API to restart backend
            import requests
            url = f"{self.api_base_url}/projects/{self.project_id}/restart-backend"
            response = requests.post(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Backend restarted successfully on port {result.get('backend_port')}")
                print(f"🔗 Backend URL: {result.get('backend_url')}")
                
                # Update backend URL in state
                self.backend_url = result.get('backend_url')
                
                return result
            else:
                print(f"❌ Failed to restart backend: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error restarting backend: {e}")
            return None
    
    def _handle_restart_frontend_interrupt(self, action: dict) -> dict:
        """Handle restart_frontend action during interrupt"""
        print(f"🔄 Restarting frontend service...")
        
        try:
            # Call the local API to restart frontend
            import requests
            url = f"{self.api_base_url}/projects/{self.project_id}/restart-frontend"
            response = requests.post(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Frontend restarted successfully on port {result.get('frontend_port')}")
                print(f"🔗 Frontend URL: {result.get('frontend_url')}")
                
                # Update preview URL in state
                self.preview_url = result.get('frontend_url')
                
                return result
            else:
                print(f"❌ Failed to restart frontend: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error restarting frontend: {e}")
            return None

    def _handle_todo_actions(self, action: dict):
        """Handle todo-related actions"""
        action_type = action.get('type')
        
        if action_type == 'todo_create':
            # Get attributes from raw_attrs if available
            attrs = action.get('raw_attrs', {})
            todo = {
                'id': attrs.get('id') or action.get('id'),
                'description': action.get('content', ''),
                'priority': attrs.get('priority', 'medium'),
                'integration': attrs.get('integration', 'false') == 'true',
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            self.todos.append(todo)
            print(f"📋 Created todo: {todo['id']} - {todo['description']}")
            
        elif action_type == 'todo_update':
            attrs = action.get('raw_attrs', {})
            todo_id = attrs.get('id') or action.get('id')
            new_status = attrs.get('status') or action.get('status')
            
            for todo in self.todos:
                if todo['id'] == todo_id:
                    old_status = todo['status']
                    todo['status'] = new_status
                    print(f"🔄 Updated todo {todo_id}: {old_status} → {new_status}")
                    
                    # If todo moved to in_progress, provide work guidance
                    if new_status == 'in_progress':
                        print(f"🎯 TODO IN PROGRESS: {todo['description']}")
                        print(f"💡 Instructions: Start working on this todo now. Create the necessary files, implement the functionality, and test it works.")
                        if todo.get('integration'):
                            print(f"🔗 Integration Required: This todo requires testing with other components")
                    break
                    
        elif action_type == 'todo_complete':
            attrs = action.get('raw_attrs', {})
            todo_id = attrs.get('id') or action.get('id')
            integration_tested = attrs.get('integration_tested', 'false') == 'true'
            
            for todo in self.todos:
                if todo['id'] == todo_id:
                    todo['status'] = 'completed'
                    todo['integration_tested'] = integration_tested
                    todo['completed_at'] = datetime.now().isoformat()
                    
                    if integration_tested:
                        print(f"✅ Completed todo: {todo_id}")
                        print(f"   🔗 Integration tested: Yes")
                    else:
                        print(f"✅ Completed todo: {todo_id}")
                        print(f"   🔗 Integration tested: No")
                    break
                    
        elif action_type == 'todo_list':
            self._display_todos()
    
    def _display_todos(self):
        """Display current todo status"""
        if not self.todos:
            print("📋 No todos created yet")
            return
        
        print("\n📋 CURRENT TODO STATUS:")
        print("=" * 50)
        
        completed = [t for t in self.todos if t['status'] == 'completed']
        in_progress = [t for t in self.todos if t['status'] == 'in_progress'] 
        pending = [t for t in self.todos if t['status'] == 'pending']
        
        if completed:
            print(f"✅ COMPLETED ({len(completed)}):")
            for todo in completed:
                integration_icon = "🔗✅" if todo.get('integration_tested') else "📝✅"
                print(f"   {integration_icon} {todo['id']}")
        
        if in_progress:
            print(f"🔄 IN PROGRESS ({len(in_progress)}):")
            for todo in in_progress:
                print(f"   🔄 {todo['id']} - {todo['description']}")
        
        if pending:
            print(f"⏳ PENDING ({len(pending)}):")
            for todo in pending:
                print(f"   ⏳ {todo['id']} - {todo['description']}")
        
        print("=" * 50)

    def _get_todo_status_summary(self) -> str:
        """Generate structured todo status summary for model awareness"""
        if not self.todos:
            return ""
        
        summary = "\n📋 **CURRENT TODO STATUS:**\n"
        summary += "=" * 50 + "\n"
        
        # Group todos by status
        completed = [t for t in self.todos if t['status'] == 'completed']
        in_progress = [t for t in self.todos if t['status'] == 'in_progress'] 
        pending = [t for t in self.todos if t['status'] == 'pending']
        
        # Show completed todos
        if completed:
            summary += f"\n✅ **COMPLETED ({len(completed)}):**\n"
            for i, todo in enumerate(completed, 1):
                integration_status = "🔗 Integrated" if todo.get('integration_tested') else "📝 Not integrated"
                summary += f"   {i}. [{todo['id']}] {todo['description']} ({integration_status})\n"
        
        # Show in progress todos  
        if in_progress:
            summary += f"\n🔄 **IN PROGRESS ({len(in_progress)}):**\n"
            for i, todo in enumerate(in_progress, 1):
                summary += f"   {i}. [{todo['id']}] {todo['description']}\n"
        
        # Show pending todos
        if pending:
            summary += f"\n⏳ **PENDING ({len(pending)}):**\n"
            for i, todo in enumerate(pending, 1):
                priority = todo.get('priority', 'medium')
                integration = "🔗 Integration required" if todo.get('integration') else "📝 Standalone"
                summary += f"   {i}. [{todo['id']}] {todo['description']} (Priority: {priority}, {integration})\n"
        
        summary += "\n" + "=" * 50 + "\n"
        summary += "**INSTRUCTIONS:** Use the todo IDs above when updating status. Continue working systematically through pending todos.\n"
        
        return summary

def main():
    """Main function supporting both creation and update modes"""
    print("🐛 DEBUG: Entered main function")
    
    # Parse command line arguments
    print("🐛 DEBUG: Creating argument parser")
    parser = argparse.ArgumentParser(description='Groq Project Creation and Update System')
    parser.add_argument('--project-id', type=str, help='Existing project ID for updates')
    parser.add_argument('--message', type=str, help='Update message/request for existing project')
    parser.add_argument('--create', action='store_true', help='Force creation mode (default if no project-id)')
    
    print("🐛 DEBUG: Parsing arguments")
    args = parser.parse_args()
    print(f"🐛 DEBUG: Args parsed - project_id: {args.project_id}, message: {args.message}")
    
    # Check for API key
    print("🐛 DEBUG: Getting API key")
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable is required")
        return
    
    # Determine mode based on arguments
    print("🐛 DEBUG: Determining mode")
    if args.project_id and args.message:
        # UPDATE MODE
        print("🐛 DEBUG: Entering update mode")
        print("🔄 Starting Project Update Mode")
        print("=" * 60)
        print(f"📋 Project ID: {args.project_id}")
        print(f"💬 Update Request: {args.message}")
        
        # Initialize system
        system = BoilerplatePersistentGroq(
            api_key='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',
            project_id=args.project_id
        )
        
        # Process the update request
        print(f"\n{'='*60}")
        print("🔄 PROCESSING UPDATE REQUEST")
        print("="*60)
        
        # Send the update message with interrupt support
        system._process_update_request_with_interrupts(args.message)
        
        # Save updated conversation history
        system._save_conversation_history()
        
        print(f"\n✅ UPDATE COMPLETED!")
        print(f"🔄 Project updated successfully")
        return
        
    else:
        # CREATION MODE (default behavior)
        print("🚀 Starting Enhanced Groq Persistent Conversation System")
        print("=" * 60)
        
        # Use provided message or demo request
        if args.message:
            user_request = args.message
        else:
            # Demo request for testing
            user_request = "Create a notes app for me simialr to notion where i can just write my notes and save them."
        
        # Generate project name based on the request with timestamp for uniqueness
        print("🐛 DEBUG: Generating project name")
        base_project_name = generate_project_name(user_request)
        timestamp = datetime.now().strftime("%H%M%S")  # Add time for uniqueness
        project_name = f"{base_project_name}-{timestamp}"
        print(f"🐛 DEBUG: Project name: {project_name}")
        print("🐛 DEBUG: Creating BoilerplatePersistentGroq instance")
        system = BoilerplatePersistentGroq(api_key, project_name)
        print("🐛 DEBUG: BoilerplatePersistentGroq instance created successfully")
        
        print("\n" + "="*60)
        print("🚀 Enhanced Boilerplate Persistent Groq System")
        print("="*60)
        print("This system:")
        print("✅ Starts with complete Vite + React + shadcn/ui boilerplate")
        print("✅ Always passes full file tree to model")
        print("✅ Maintains context across multiple requests")
        print("✅ Creates/modifies files in real project")
        print("✅ Model knows all packages are pre-installed")
        print()
        
        print(f"\n{'='*20} PROJECT CREATION {'='*20}")
        print(f"📝 {user_request}")
        print(f"\n{'='*50}")
        
        # Phase 2.5: Setup project environment (venv, packages) but DON'T start services
        print("🔧 Phase 2.5: Setting up project environment (venv, packages)...")
        setup_success = system.setup_project_environment()
        if setup_success:
            print("✅ Project environment setup completed")
            print("ℹ️  Services will start only when model uses action tags like <action type='start_backend'/>")
        else:
            print("⚠️ Warning: Environment setup had issues, but continuing with generation")
        
        # Use natural todo workflow with direct coder call
        print("🧠 Using natural todo workflow with coder system...")
        
        system.conversation_history.append({"role": "system", "content": system._load_system_prompt()})
        
        # Add the user request to conversation history
        system.conversation_history.append({"role": "user", "content": user_request})
        
        # Use the coder system directly with current conversation history
        from coder.index import coder
        response = coder(messages=system.conversation_history, self=system)
        
        # Add model response to conversation history
        if response:
            system.conversation_history.append({"role": "assistant", "content": response})
            
            # Add current todo status as user message for next iteration awareness
            todo_status = system._get_todo_status_summary()
            if todo_status:
                system.conversation_history.append({"role": "user", "content": todo_status})
        
        # Save full raw response to markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = system.backend_dir / f"groq_chunks_response_{timestamp}.md"
        
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"# Groq Model Response - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Request\n{user_request}\n\n")
            f.write(f"## Response Summary\n{response}\n\n")
            
            # Save the actual plan XML if available
            if hasattr(system, '_last_plan_response'):
                f.write(f"## Full Plan XML\n\n")
                f.write(system._last_plan_response)
        
        print(f"💾 Full raw response saved to: {response_file}")
        
        # Show clean response (without XML tags for demo)
        lines = response.split('\n')
        clean_lines = []
        in_action = False
        
        for line in lines:
            if '<action type="file"' in line:
                in_action = True
                continue
            elif '</action>' in line:
                in_action = False
                continue
            elif not in_action and not line.strip().startswith('<'):
                clean_lines.append(line)
        
        clean_response = '\n'.join(clean_lines).strip()
        if clean_response:
            print(f"🤖 {clean_response}")
        
        print(f"\n📊 Project Status: {len(system.project_files)} files")
        
        # Show project structure after each request
        context = system.get_project_context()
        if context:
            structure_lines = [line for line in context.split('\n') 
                             if '📂 CURRENT FILE STRUCTURE:' in line or 
                                line.startswith(('├──', '└──', 'demo_dashboard/'))]
            if len(structure_lines) > 1:
                print("\n📁 Updated Structure:")
                for line in structure_lines[1:]:  # Skip the header
                    print(line)
    
    print('Project done ✅')    

if __name__ == "__main__":
    main()