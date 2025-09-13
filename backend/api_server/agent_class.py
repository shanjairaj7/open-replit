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
from click.termui import prompt
import requests
import asyncio
import aiohttp
import time
import argparse
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from datetime import datetime
from pathlib import Path
from cloud_storage import AzureBlobStorage
from vm_api import vm_api
from tools.package_manager import PackageManager
import sys

# Removed enhance_user_message import - using raw user messages now
from utils.token_tracking import OpenRouterTokenTracker, create_token_tracker
from utils.tokenizer import get_tokenizer, count_messages_tokens

# Add the parent directory to sys.path to enable imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# from groq import Groq  # Removed - not using Groq anymore
from typing import Generator, Dict, Optional, List
from shared_models import GroqAgentState, StreamingXMLParser
from openai import OpenAI, AzureOpenAI

# Azure OpenAI - GPT-4.1 deployment
gpt_endpoint = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com"
gpt_model_name = "grok-3"
gpt_deployment = "grok-3"
gpt_api_version = "2024-12-01-preview"

# Azure OpenAI - DeepSeek R1 deployment
deepseek_endpoint = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com"
deepseek_model_name = "DeepSeek-R1-0528"
deepseek_api_version = "2024-05-01-preview"

subscription_key = os.environ.get('AZURE_SUBSCRIPTION_KEY', 'FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1')

# Default model selection (can be overridden with MODEL_TYPE=deepseek)
model_type = os.environ.get("MODEL_TYPE", "gpt").lower()

if model_type == "deepseek":
    endpoint = deepseek_endpoint
    model_name = deepseek_model_name
    api_version = deepseek_api_version
    deployment = deepseek_model_name
else:
    # Default to GPT-4.1
    endpoint = gpt_endpoint
    model_name = gpt_model_name
    api_version = gpt_api_version
    deployment = gpt_deployment

azure_client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

openai_client = OpenAI(
    base_url='https://openrouter.ai/api/v1', 
    api_key=os.environ.get('OPENAI_KEY', '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'), 
    default_headers={"x-include-usage": 'true'},
    timeout=30.0  # 30 second timeout
)

# Default to Azure mode in API server (can be overridden with USE_AZURE_MODE=false)
USE_AZURE_MODE = os.environ.get("USE_AZURE_MODE", "true").lower() == "true"

from prompts import simpler_prompt

# Custom exception for frontend command interrupts
class FrontendCommandInterrupt(Exception):
    """Exception raised when frontend terminal command should interrupt the stream"""
    def __init__(self, command: str, cwd: str, action: dict, project_id: str):
        self.command = command
        self.cwd = cwd
        self.action = action
        self.project_id = project_id
        super().__init__(f"Frontend command interrupt: {command} in {cwd}")

# Import the appropriate coder based on mode
if USE_AZURE_MODE:
    from agent import coder  # Use local API server version
    print("🔵 Using Azure OpenAI mode with hybrid compatibility")
else:
    # Fallback to Azure mode for Modal deployment
    from agent import coder
    print("🟢 Using OpenRouter mode (fallback to Azure)")


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



# Import shared utility function
from utils.basic import generate_short_app_name



class BoilerplatePersistentGroq:
    """
    Main orchestrator class for Groq-based project generation and updates.

    State Model: GroqAgentState (Pydantic model defined above)
    """

    def __init__(self, api_key: str = None, project_name: str = None, api_base_url: str = "http://localhost:8000/api", project_id: str = None):
        print("🐛 DEBUG: Starting BoilerplatePersistentGroq __init__")

        # Initialize background cloud operations
        self.cloud_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cloud-ops")
        self.cloud_tasks_active = 0
        self._cloud_lock = threading.Lock()
        
        # Initialize dedicated executor for model operations to prevent server blocking
        self.model_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="model-ops")

        # Configure client and model based on mode
        if USE_AZURE_MODE:
            self.client = azure_client
            self.model = deployment  # Use deployment name for Azure
            self.is_azure_mode = True
            print(f"🔵 DEBUG: Azure OpenAI client created with model: {self.model}")
        else:
            self.client = openai_client
            self.model = 'qwen/qwen3-coder'  # Use model path for OpenRouter
            # qwen/qwen3-coder
            # moonshotai/kimi-k2-0905
            self.is_azure_mode = False
            print(f"🟢 DEBUG: OpenRouter client created with model: {self.model}")
        self.conversation_history = []  # Store conversation messages
        self.api_base_url = api_base_url

        # Set project_id early - needed for todo storage
        self.project_id = project_id
        print(f"🐛 DEBUG: Initial project_id set to: {self.project_id}")

        # Initialize cloud storage
        try:
            self.cloud_storage = AzureBlobStorage()
            print("☁️ Cloud storage initialized successfully")
        except Exception as e:
            print(f"⚠️ Warning: Cloud storage initialization failed: {e}")
            self.cloud_storage = None

        # Track files that have been read - project-specific persistence
        self.read_files_tracker = set()  # Files read in current session
        self.read_files_persistent = set()  # Files read across all sessions for THIS project

        # Initialize available files list for cloud-first architecture
        self.available_files = []  # Files available in cloud storage (no content loaded)

        self.todos = []
        # Initialize persistent todo storage
        self._ensure_todos_loaded()

        # Initialize token tracking using centralized module with project_id
        api_key = None
        if hasattr(self.client, 'api_key'):
            api_key = self.client.api_key

        self._token_tracker = create_token_tracker(api_key, self.project_id)

        # Keep backward compatibility with existing token_usage references
        self.token_usage = self._token_tracker.get_token_usage()
        
        # Initialize tokenizer for manual token estimation
        model_for_tokenizer = self.model if hasattr(self, 'model') else "gpt-4"
        self.tokenizer = get_tokenizer(model_for_tokenizer)
        
        # Initialize message count tracking for automatic token counting
        self._last_tracked_message_count = 0

        # Paths (for local boilerplate reference)
        print("🐛 DEBUG: Setting up paths")
        self.backend_dir = Path(__file__).parent
        print(f"🐛 DEBUG: Backend dir: {self.backend_dir}")
        self.boilerplate_path = self.backend_dir / "boilerplate" / "shadcn-boilerplate"
        print("🐛 DEBUG: Paths set up successfully")

        print(f"🐛 DEBUG: About to check project_id condition, value is: {self.project_id}")
        if self.project_id:
            # Load existing project with already set project_id
            print(f"🐛 DEBUG: Using existing project_id: {self.project_id}")
            self.project_name = self.project_id  # Use project_id as name for now
            self.project_files = {}

            # Only call API if this looks like a real project (not a test)
            # Skip scanning for simple unit tests but allow cloud scanning tests
            if not self.project_id.startswith('test-project-'):  # Only skip very basic test projects
                self._scan_project_files_via_cloud_storage()

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
                # Test project - minimal setup
                self.system_prompt = "Test system prompt"
                print(f"✅ Test project initialized: {self.project_name} (ID: {self.project_id})")

                # Initialize empty todos for new projects
                self.todos = []

        else:
            # Create new project
            if project_name:
                self.project_name = project_name
                self.project_id = self.create_project_via_cloud_storage(project_name)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.project_name = f"project_{timestamp}"
                self.project_id = self.create_project_via_cloud_storage(self.project_name)

            self.project_files = {}
            # Initialize empty todos for new projects
            self.todos = []
            # Use cloud storage scanning for existing projects
            if self.cloud_storage:
                self._scan_project_files_via_cloud_storage()
            else:
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

        # Initialize ToolsManager for new tools
        try:
            from tools import ToolsManager
            self.tools_manager = ToolsManager(
                cloud_storage=self.cloud_storage,
                project_id=self.project_id,
                read_files_tracker=self.read_files_tracker,
                read_files_persistent=self.read_files_persistent
            )
        except Exception as e:
            print(f"⚠️ Failed to initialize ToolsManager: {e}")
            self.tools_manager = None

    def _show_read_files_status(self):
        """Display current read files tracking status"""
        print(f"📚 READ FILES TRACKING:")
        print(f"   📖 Current session: {len(self.read_files_tracker)} files")
        print(f"   💾 Persistent total: {len(self.read_files_persistent)} files")
        if self.read_files_persistent:
            print(f"   📋 Previously read: {', '.join(sorted(list(self.read_files_persistent)[:5]))}{'...' if len(self.read_files_persistent) > 5 else ''}")

    def _load_system_prompt(self) -> str:
        """Load system prompt from file with project context"""

        # base_prompt = grok_system_prompt.prompt
        base_prompt = simpler_prompt.prompt

        # any additions to system prompt based on project context, can be added here
        return base_prompt

    def _load_project_context(self):
        """Load existing project summary and conversation history for update mode"""
        # Initialize project summary (cloud storage only)
        self.project_summary = "No project summary available."
        print(f"📋 Project summary: cloud storage only (no local files)")

        # Load conversation history - CLOUD FIRST, LOCAL FALLBACK
        conversation_loaded = False

        # Try loading from cloud storage first
        if self.cloud_storage and self.project_id:
            try:
                print(f"☁️ Attempting to load conversation history from cloud storage for project: {self.project_id}")
                cloud_conversation_history = self.cloud_storage.load_conversation_history(self.project_id)

                if cloud_conversation_history and len(cloud_conversation_history) > 0:
                    self.conversation_history = cloud_conversation_history
                    conversation_loaded = True
                    print(f"☁️ ✅ Loaded conversation history from cloud storage: {len(self.conversation_history)} messages")

                    # Try to load token usage from cloud metadata
                    project_metadata = self.cloud_storage.load_project_metadata(self.project_id)
                    if project_metadata and 'token_usage' in project_metadata:
                        self._token_tracker.load_token_usage(project_metadata['token_usage'])
                        # Update backward compatibility reference
                        self.token_usage = self._token_tracker.get_token_usage()
                        print(f"💰 Loaded token usage from cloud metadata: {self.token_usage['total_tokens']:,} total tokens")

                    # Load todos from cloud storage
                    self._ensure_todos_loaded()
                else:
                    print(f"☁️ No conversation history found in cloud storage")

            except Exception as e:
                print(f"⚠️ Failed to load conversation history from cloud: {str(e)}")


        # Final status
        if conversation_loaded:
            print(f"✅ Conversation history loaded successfully: {len(self.conversation_history)} messages")
            print(f"📚 Read files tracker: {len(self.read_files_persistent)} files previously read")
            
            # Update message count tracking after loading conversation
            self._last_tracked_message_count = len(self.conversation_history)
        else:
            print(f"⚠️ No conversation history found in cloud or local storage - starting fresh")
            self.conversation_history = []  # Ensure it's initialized
            self._last_tracked_message_count = 0

    def _save_conversation_history(self):
        """Save current conversation history to JSON file"""
        conversations_dir = self.backend_dir / "project_conversations"
        conversations_dir.mkdir(exist_ok=True)

        conversation_file = conversations_dir / f"{self.project_id}_messages.json"

        # Check if we need to summarize conversation
        should_summarize_tokens = False
        if hasattr(self, '_token_tracker'):
            should_summarize_tokens = self._token_tracker.should_summarize()
            # Sync token usage for accurate logging
            self.token_usage = self._token_tracker.get_token_usage()
        else:
            should_summarize_tokens = self.token_usage['total_tokens'] >= 500000

        if should_summarize_tokens:
            # Mid-task summarization (token limit reached)
            print(f"🔄 Triggering summarization: {self.token_usage['total_tokens']:,} total tokens")
            self._check_and_summarize_conversation(is_mid_task=True)
        # if length of conversation is more than 60 messages from the point of last summary
        elif len(self._get_filtered_conversation_history()) > 120:
            # Check if conversation has grown large
            print(f"🔄 Conversation has grown large: More than 60 messages from latest summary")
            self._check_and_summarize_conversation(is_mid_task=True)

        # Sync token usage from tracker for accurate saving
        if hasattr(self, '_token_tracker'):
            self.token_usage = self._token_tracker.get_token_usage()

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

        # Save to cloud storage in background - non-blocking
        if self.cloud_storage and self.project_id:
            # Save conversation history in background
            self._save_conversation_background()

            # Prepare metadata in background
            try:
                # We need existing metadata, but this read is quick
                existing_metadata = self.cloud_storage.load_project_metadata(self.project_id) or {}

                metadata_to_save = {
                    **existing_metadata,  # Preserve existing data like backend_deployment
                    "token_usage": self.token_usage,
                    "project_state": conversation_data["project_state"],
                    "last_conversation_update": datetime.now().isoformat()
                }

                # Include todos if they exist
                if hasattr(self, 'todos') and self.todos:
                    metadata_to_save["todos"] = self.todos
                    metadata_to_save["todos_last_updated"] = datetime.now().isoformat()

                # Save metadata in background
                self._save_metadata_background(metadata_to_save)
                print(f"🌥️ Started background save of conversation and metadata")

            except Exception as e:
                print(f"❌ Error preparing background save: {e}")
        else:
            print(f"❌ No cloud storage available - conversation not saved")

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

            # CRITICAL FIX: Mark session boundary when creating summary
            # Add a session marker to track where the new session starts
            session_marker = {
                "role": "assistant",
                "content": "--- SESSION BOUNDARY: Messages before this were summarized ---",
                "metadata": {
                    "type": "session_boundary",
                    "created_at": datetime.now().isoformat(),
                    "summary_index": len(self.conversation_history)  # Points to where summary will be
                }
            }

            self.conversation_history.append(summary_message)
            self.conversation_history.append(session_marker)
            print(f"✅ Added detailed summary to conversation ({len(summary_content)} characters)")
            print(f"📍 Added session boundary marker for proper message filtering")

            # Reset token counter to start fresh count from this point
            self._reset_token_tracking_after_summary()
        else:
            print(f"❌ Failed to generate conversation summary")

    def _update_manual_token_usage(self, input_messages: List = None, output_message: str = None):
        """
        Manually update token usage when Azure usage is not available
        
        Args:
            input_messages: List of messages sent to model (for input tokens) 
                          - These are the TOTAL messages sent (including history)
            output_message: Assistant response message (for output tokens only)
        """
        if not hasattr(self, 'tokenizer'):
            print("⚠️ Tokenizer not initialized, skipping manual token tracking")
            return
        
        input_tokens = 0
        output_tokens = 0
        
        # Calculate input tokens (all messages sent to model)
        if input_messages:
            input_tokens = count_messages_tokens(input_messages, self.tokenizer.model_name)
            print(f"📊 Estimated input tokens (total conversation): {input_tokens:,}")
        
        # Calculate output tokens (only new assistant response)
        if output_message:
            output_tokens = self.tokenizer.count_text_tokens(output_message)
            print(f"📊 Estimated output tokens (new response): {output_tokens:,}")
        
        # For cumulative tracking, we need to add only the NEW tokens
        # Input tokens: Use the TOTAL input tokens for this API call
        # Output tokens: Add only the new output tokens
        
        # Update token tracker manually
        if hasattr(self, '_token_tracker') and (input_tokens > 0 or output_tokens > 0):
            # For input tokens, we track the total conversation size each time
            # For output tokens, we add only the new response
            
            # Get current token usage
            current_usage = self._token_tracker.get_token_usage()
            
            # Calculate incremental tokens
            # Input tokens represent the FULL conversation sent to model
            # Output tokens are just the new assistant response
            
            # The token tracker expects a single API call usage
            # But we want cumulative tracking, so we'll simulate it
            
            class MockUsage:
                def __init__(self, prompt_tokens, completion_tokens):
                    self.prompt_tokens = prompt_tokens
                    self.completion_tokens = completion_tokens
                    self.total_tokens = prompt_tokens + completion_tokens
            
            class MockResponse:
                def __init__(self, usage):
                    self.usage = usage
            
            # For proper cumulative tracking:
            # - Input tokens: represent full conversation cost for this API call  
            # - Output tokens: just the new response tokens
            mock_usage = MockUsage(input_tokens if input_tokens > 0 else 0, 
                                 output_tokens if output_tokens > 0 else 0)
            mock_response = MockResponse(mock_usage)
            
            # Update using existing token tracker logic
            self._token_tracker.process_usage_from_response(mock_response)
            self.token_usage = self._token_tracker.get_token_usage()
            
            if input_tokens > 0 and output_tokens > 0:
                print(f"💰 Updated token usage - Input: {input_tokens:,}, Output: {output_tokens:,}, Total: {self.token_usage['total_tokens']:,}")
            elif input_tokens > 0:
                print(f"💰 Updated token usage - Input: {input_tokens:,}, Total: {self.token_usage['total_tokens']:,}")  
            elif output_tokens > 0:
                print(f"💰 Updated token usage - Output: {output_tokens:,}, Total: {self.token_usage['total_tokens']:,}")

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

1. Current Work:
   [Detailed description]

2. Key Technical Concepts:
   - [Concept 1]
   - [Concept 2]
   - [...]

3. Relevant Files and Code:
   - [File Name 1]
      - [Summary of why this file is important]
      - [Summary of the changes made to this file, if any]
      - [Important Code Snippet]
   - [File Name 2]
      - [Important Code Snippet]
   - [...]

4. Problem Solving:
   [Detailed description]

5. Pending Tasks and Next Steps:
   - [Task 1 details & next steps]
   - [Task 2 details & next steps]
   - [...]

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
                # temperature=0.1,   # Keep it factual and consistent
            )

            summary_content = response.choices[0].message.content

            # Track token usage for summary generation
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                if hasattr(self, '_token_tracker'):
                    self._token_tracker.process_usage_from_response(response)
                    # Update backward compatibility reference
                    self.token_usage = self._token_tracker.get_token_usage()
                else:
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
        if hasattr(self, '_token_tracker'):
            self._token_tracker.reset_token_tracking()
            # Update backward compatibility reference
            self.token_usage = self._token_tracker.get_token_usage()
        else:
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

        # Find session boundary marker (if it exists)
        session_boundary_index = -1
        for i in range(latest_summary_index + 1, len(self.conversation_history)):
            message = self.conversation_history[i]
            if (message.get('metadata', {}).get('type') == 'session_boundary'):
                session_boundary_index = i
                print(f"📍 Found session boundary at index {i}")
                break

        # Include only messages after the session boundary (true current session)
        if session_boundary_index != -1:
            # Messages after session boundary are the true current session
            messages_after_summary = self.conversation_history[session_boundary_index + 1:]
            print(f"📍 Using messages after session boundary: {len(messages_after_summary)} messages")
        else:
            # Fallback: if no session boundary, use all messages after summary (old behavior)
            messages_after_summary = self.conversation_history[latest_summary_index + 1:]
            print(f"⚠️ No session boundary found, using all messages after summary: {len(messages_after_summary)} messages")

        filtered_messages = [system_prompt, raw_summary_message] + messages_after_summary
        print(f"📝 Using filtered conversation: system + summary + {len(messages_after_summary)} session messages = {len(filtered_messages)} total")

        # Apply file read deduplication to reduce token usage
        deduplicated_messages = self._deduplicate_file_reads(filtered_messages)
        print(f"📝 After deduplication: {len(deduplicated_messages)} messages (saved {len(filtered_messages) - len(deduplicated_messages)} messages)")

        # Remove metadata from messages for API compatibility and filter out session boundaries
        api_compatible_messages = []
        for message in deduplicated_messages:
            # Skip session boundary markers - they're for internal use only
            if message.get('metadata', {}).get('type') == 'session_boundary':
                continue

            # Handle content that might be a list
            content = message["content"]
            if isinstance(content, list):
                content = '\n'.join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)
                
            clean_message = {
                "role": message["role"],
                "content": content
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

            # Ensure content is a string (handle case where it might be a list)
            if isinstance(content, list):
                content = '\n'.join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)

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
            print(f"🐛 FILETREE DEBUG: hasattr available_files: {hasattr(self, 'available_files')}")
            print(f"🐛 FILETREE DEBUG: available_files length: {len(getattr(self, 'available_files', []))}")
            print(f"🐛 FILETREE DEBUG: project_files length: {len(self.project_files)}")
            print(f"🐛 FILETREE DEBUG: cloud_storage available: {self.cloud_storage is not None}")

            # Use cloud-first approach - check available_files first
            if hasattr(self, 'available_files') and self.available_files:
                files_to_process = self.available_files
                print(f"📁 Using available_files from cloud storage: {len(files_to_process)} files")
            else:
                print(f"🐛 FILETREE DEBUG: available_files is empty or missing, falling back to local scan")
                # Fallback to local scanning if cloud files not available
                self._scan_project_files_via_api()
                if not self.project_files:
                    return "No files found in project"
                files_to_process = list(self.project_files.keys())
                print(f"📁 Using project_files from local scan: {len(files_to_process)} files")

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
            sorted_files = sorted(files_to_process)

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
        """Load project-specific read files tracking from cloud storage"""
        # Load from cloud storage if available, fallback to local file
        if self.cloud_storage and self.project_id:
            read_files_set = self.cloud_storage.load_read_files_tracking(self.project_id)
            if read_files_set:
                self.read_files_persistent = read_files_set
                print(f"☁️ Loaded read files tracking from cloud storage")
                print(f"📖 Previously read files: {len(self.read_files_persistent)} files")
                return
            else:
                print(f"📄 No read files tracking found in cloud storage")

    def _save_read_files_tracking(self):
        """Save project-specific read files tracking to cloud storage in background"""
        # Save to cloud storage in background if available, fallback to local file
        if self.cloud_storage and self.project_id:
            self._run_cloud_operation_background(
                "Save read files tracking",
                self.cloud_storage.save_read_files_tracking,
                self.project_id,
                self.read_files_persistent.copy()  # Make a copy to avoid race conditions
            )
            print(f"🌥️ Started background save of read files tracking")
        else:
            print(f"❌ No cloud storage available - read files tracking not saved")


    def create_project_via_cloud_storage(self, project_name: str) -> str:
        """Create project using cloud storage and GitHub repositories"""
        try:
            if not self.cloud_storage:
                print("⚠️ Cloud storage not available, falling back to API method")
                return self.create_project_via_api(project_name)

            project_id = project_name

            # Check if project already exists in cloud storage
            existing_metadata = self.cloud_storage.load_project_metadata(project_id)
            if existing_metadata:
                print(f"☁️ Using existing cloud project: {project_name} (ID: {project_id})")
                return project_id

            print(f"🚀 Creating new project in cloud storage: {project_name}")

            # Clone GitHub repositories to cloud storage
            frontend_repo = "https://github.com/shanjairaj7/frontend-boilerplate.git"
            backend_repo = "https://github.com/shanjairaj7/backend-boilerplate.git"

            print(f"📡 Cloning frontend boilerplate from GitHub...")
            frontend_success = self.cloud_storage.clone_from_github(project_id, frontend_repo, "frontend")

            print(f"📡 Cloning backend boilerplate from GitHub...")
            backend_success = self.cloud_storage.clone_from_github(project_id, backend_repo, "backend")

            if frontend_success and backend_success:
                # Create project metadata
                metadata = {
                    "project_id": project_id,
                    "project_name": project_name,
                    "created_at": datetime.now().isoformat(),
                    "frontend_repo": frontend_repo,
                    "backend_repo": backend_repo,
                    "creation_method": "cloud_storage_github",
                    "status": "initialized"
                }

                # Save project metadata (async background)
                self._run_cloud_operation_background(
                    "Save project metadata",
                    self.cloud_storage.save_project_metadata,
                    project_id,
                    metadata.copy()  # Make a copy to avoid race conditions
                )

                print(f"✅ Project created successfully in cloud storage")
                print(f"📁 Frontend: Cloned from {frontend_repo}")
                print(f"📁 Backend: Cloned from {backend_repo}")
                print(f"🌥️ Background save of project metadata initiated")
                return project_id
            else:
                print(f"❌ Failed to clone repositories, falling back to API method")
                return self.create_project_via_api(project_name)

        except Exception as e:
            print(f"❌ Error creating project in cloud storage: {e}")
            print(f"🔄 Falling back to API method")
            return self.create_project_via_api(project_name)

    def create_project_via_api(self, project_name: str) -> str:
        """Create project via API (fallback method)"""
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
                    errors_text = '\n\n'.join(all_errors)
                    error_message = {
                        "role": "user",
                        "content": f"Project created but validation found issues:\n\n{errors_text}\n\nPlease fix these errors."
                    }
                    self.conversation_history.append(error_message)

                # VPS API returns the project info with 'id' field
                return project_data['project']['id']
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Error creating project via API: {e}")
            raise

    def _read_file_via_api(self, file_path: str, start_line: str = None, end_line: str = None) -> str:
        """Read file content from Azure Blob Storage"""
        try:
            # Use cloud storage if available, fallback to API
            if self.cloud_storage and self.project_id:
                content = self.cloud_storage.download_file(self.project_id, file_path)

                if content is not None:
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
                    print(f"📄 File not found in cloud storage: {file_path}")
                    return None

            # Fallback to VPS API if cloud storage not available
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
        """Write file content to Azure Blob Storage and return result with Python errors if any"""
        try:
            # Use cloud storage if available, fallback to API
            if self.cloud_storage and self.project_id:
                # For write operations, treat as new file (will overwrite if exists)
                success = self.cloud_storage.upload_file(self.project_id, file_path, content, is_new_file=True)

                if success:
                    print(f"☁️ Successfully wrote to cloud storage: {file_path}")
                    return {
                        "success": True,
                        "python_errors": "",
                        "python_check_status": {"executed": False, "success": True},
                        "typescript_errors": "",
                        "typescript_check_status": {"executed": False, "success": True}
                    }
                else:
                    print(f"❌ Failed to write to cloud storage: {file_path}")
                    return {"success": False, "error": "Failed to upload to cloud storage"}

            # Fallback to VPS API if cloud storage not available
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
        """Update file via Azure Blob Storage with API fallback"""
        try:
            # Use cloud storage if available, fallback to API
            if self.cloud_storage and self.project_id:
                # This is an update operation, so is_new_file = False
                success = self.cloud_storage.upload_file(self.project_id, file_path, content, is_new_file=False)

                if success:
                    print(f"☁️ Successfully updated via cloud storage: {file_path}")
                    return {
                        "status": "updated",
                        "file": file_path,
                        "python_errors": "",
                        "python_check_status": {"executed": False, "success": True},
                        "typescript_errors": "",
                        "typescript_check_status": {"executed": False, "success": True}
                    }
                else:
                    print(f"⚠️ Cloud storage update failed, trying API fallback")

            # Fallback to API if cloud storage not available or failed
            payload = {
                "content": content
            }
            response = requests.put(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}", json=payload)

            if response.status_code == 200:
                data = response.json()
                print(f"📡 Successfully updated via API fallback: {file_path}")
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
            print(f"⚠️ Error updating file: {error_msg}")
            return {"status": "error", "error": error_msg}

    def _rename_file_via_api(self, old_path: str, new_name: str) -> dict:
        """Rename file via Azure Blob Storage with API fallback"""
        try:
            # Use cloud storage if available
            if self.cloud_storage and self.project_id:
                # Read the current file content
                content = self.cloud_storage.download_file(self.project_id, old_path)
                if content is not None:
                    # Create the new file path
                    path_parts = old_path.split('/')
                    path_parts[-1] = new_name  # Replace filename with new name
                    new_path = '/'.join(path_parts)

                    # Upload to new location and delete old file
                    upload_success = self.cloud_storage.upload_file(self.project_id, new_path, content)
                    delete_success = self.cloud_storage.delete_file(self.project_id, old_path)

                    if upload_success and delete_success:
                        print(f"☁️ Successfully renamed via cloud storage: {old_path} -> {new_path}")
                        return {
                            "status": "renamed",
                            "old_path": old_path,
                            "new_path": new_path
                        }
                    else:
                        print(f"⚠️ Cloud storage rename failed, trying API fallback")
                else:
                    print(f"⚠️ Could not read file for rename, trying API fallback")

            # Fallback to API if cloud storage not available or failed
            payload = {
                "new_name": new_name
            }
            response = requests.patch(f"{self.api_base_url}/projects/{self.project_id}/files/{old_path}/rename", json=payload)

            if response.status_code == 200:
                data = response.json()
                print(f"📡 Successfully renamed via API fallback: {old_path}")
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
            print(f"⚠️ Error renaming file: {error_msg}")
            return {"status": "error", "error": error_msg}

    def _delete_file_via_api(self, file_path: str) -> dict:
        """Delete file via Azure Blob Storage with API fallback"""
        try:
            # Use cloud storage if available
            if self.cloud_storage and self.project_id:
                success = self.cloud_storage.delete_file(self.project_id, file_path)

                if success:
                    print(f"☁️ Successfully deleted via cloud storage: {file_path}")
                    return {
                        "status": "deleted",
                        "file": file_path
                    }
                else:
                    print(f"⚠️ Cloud storage deletion failed, trying API fallback")

            # Fallback to API if cloud storage not available or failed
            response = requests.delete(f"{self.api_base_url}/projects/{self.project_id}/files/{file_path}")

            if response.status_code == 200:
                data = response.json()
                print(f"📡 Successfully deleted via API fallback: {file_path}")
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
            print(f"⚠️ Error deleting file: {error_msg}")
            return {"status": "error", "error": error_msg}


    def _scan_project_files_via_cloud_storage(self):
        """Scan project files from Azure Blob Storage - get file list only, NO content download"""
        self.project_files = {}  # Keep empty - files accessed directly from cloud when needed

        print(f"🔍 DEBUG: cloud_storage available: {self.cloud_storage is not None}")
        print(f"🔍 DEBUG: project_id: {self.project_id}")

        if not self.cloud_storage:
            print("⚠️ Cloud storage not available, falling back to API scanning")
            self._scan_project_files_via_api()
            return

        print(f"☁️ Scanning project file structure in cloud storage: {self.project_id}")

        try:
            # Get file list from cloud storage (metadata only, no content)
            all_files = self.cloud_storage.list_files(self.project_id)

            if not all_files:
                print(f"📂 No files found in cloud storage for project: {self.project_id}")
                return

            # Filter and organize files (same filtering as before)
            exclude_patterns = [
                'node_modules/', '__pycache__/', '.git/', '.vscode/', '.idea/',
                'dist/', 'build/', '.next/', '.vite/', 'coverage/', '.mypy_cache/',
                '.pytest_cache/', '.tox/', 'venv/', '.env', 'test_env/',
                '.DS_Store', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'
            ]

            filtered_files = []
            for file_path in all_files:
                # Skip system/config files that shouldn't be in project tree
                should_skip = False
                file_lower = file_path.lower()

                for pattern in exclude_patterns:
                    if pattern.endswith('/') and pattern in f"/{file_lower}/":
                        should_skip = True
                        break
                    elif not pattern.endswith('/') and pattern in file_lower:
                        should_skip = True
                        break

                if not should_skip and not file_path.startswith('.'):
                    filtered_files.append(file_path)

            # Store file list for reference, but NO CONTENT DOWNLOAD
            self.available_files = filtered_files  # Track available files without loading content

            print(f"📁 Found {len(filtered_files)} available files (filtered from {len(all_files)} total)")
            print(f"☁️ Files will be loaded from cloud storage only when accessed via _read_file_via_api")
            print(f"🎯 Cloud-first architecture: No local file caching, direct cloud access only")

        except Exception as e:
            print(f"❌ Error scanning cloud storage: {e}")
            print("🔄 Falling back to API scanning method")
            self._scan_project_files_via_api()

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
        context += "This is a complete Vite + React + TypeScript + Router setup.\n\n"

        context += "🏗️ BOILERPLATE INCLUDES:\n"
        context += "- ⚡ Vite for fast development\n"
        context += "- ⚛️ React with TypeScript\n"
        context += "- 🗂️ Organized folder structure (pages/, components/, hooks/, etc.)\n\n"

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

        return context


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
                # temperature=0.3
            )

            summary_content = response.choices[0].message.content

            # Track token usage for non-streaming call
            if hasattr(response, 'usage'):
                usage = response.usage
                if hasattr(self, '_token_tracker'):
                    self._token_tracker.process_usage_from_response(response)
                    # Update backward compatibility reference
                    self.token_usage = self._token_tracker.get_token_usage()
                else:
                    self.token_usage['prompt_tokens'] = usage.prompt_tokens
                    self.token_usage['completion_tokens'] = usage.completion_tokens
                    self.token_usage['total_tokens'] = usage.total_tokens

                print(f"📊 Token usage for summary: {usage.total_tokens} tokens")

            print(f"✅ Project summary generated (cloud storage only)")
            return "summary_generated_cloud_only"

        except Exception as e:
            print(f"❌ Error generating project summary: {e}")
            return None

    def _query_generation_usage(self, generation_id):
        """Query usage statistics for a generation using OpenRouter API via token tracker"""
        if hasattr(self, '_token_tracker') and hasattr(self._token_tracker, 'query_generation_usage'):
            result = self._token_tracker.query_generation_usage(generation_id)
            if result:
                # Update backward compatibility reference
                self.token_usage = self._token_tracker.get_token_usage()
            return result
        else:
            print(f"💰 CODER: Would query generation ID: {generation_id} for usage stats")
            return None

    async def _async_http_get(self, url, timeout=30):
        """Async HTTP GET request"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                text = await response.text()
                return {
                    'status_code': response.status,
                    'json': lambda: json.loads(text) if text.strip() else {},
                    'text': text
                }

    async def _async_http_post(self, url, json_data=None, timeout=30):
        """Async HTTP POST request"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post(url, json=json_data) as response:
                text = await response.text()
                return {
                    'status_code': response.status,
                    'json': lambda: json.loads(text) if text.strip() else {},
                    'text': text
                }

    async def _async_http_put(self, url, json_data=None, timeout=30):
        """Async HTTP PUT request"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.put(url, json=json_data) as response:
                text = await response.text()
                return {
                    'status_code': response.status,
                    'json': lambda: json.loads(text) if text.strip() else {},
                    'text': text
                }

    async def _async_coder(self, messages, streaming_callback=None):
        """Async wrapper for AI model calls to prevent blocking other requests"""
        import asyncio

        # Run the synchronous coder function in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def run_coder():
            from agent import coder
            return coder(messages=messages, self=self, streaming_callback=streaming_callback)

        # Execute in dedicated model thread pool to prevent server blocking
        response_content = await loop.run_in_executor(self.model_executor, run_coder)
        return response_content

    async def _process_update_request_with_interrupts(self, user_message: str, mode: str = "update", step_info: dict = None, streaming_callback=None):
        """Process request with interrupt-and-continue pattern - supports both update and step generation modes (async for concurrency)"""

        if mode == "step":
            step_number = step_info.get('step_number', 'N/A')
            step_name = step_info.get('name', 'Unknown Step')
            print(f"\n🎯 STEP MODE: Processing step {step_number} - {step_name}")
        else:
            print(f"\n📝 UPDATE MODE: Processing modification request with read-before-write enforcement")

        # Use raw user message directly without enhancement
        print('====')
        print('Using raw user message directly')
        print('====')
        print(user_message)
        print('=========')

        # user_message stays as original

        # Start with system prompt with runtime environment info
        system_prompt = self._load_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # CRITICAL FIX: For new projects, add system prompt to conversation history
        if not self.conversation_history:
            print("📋 New project: Adding system prompt to conversation history")
            self.conversation_history.append({"role": "system", "content": system_prompt})

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
        print(f"🐛 DEBUG: About to generate file tree...")
        print(f"🐛 DEBUG: available_files count: {len(getattr(self, 'available_files', []))}")
        print(f"🐛 DEBUG: project_files count: {len(self.project_files)}")

        file_tree = self._generate_realtime_file_tree()
        print(f"🐛 DEBUG: Generated file_tree length: {len(file_tree)} characters")
        print(f"🐛 DEBUG: File tree preview: {file_tree[:200]}...")

        # Build service status context
        service_status = self._build_service_status_context()
        print(f"🐛 DEBUG: Generated service_status length: {len(service_status)} characters")

        # Combine all context for enhanced user message
        if service_status:
            enhanced_user_message = f"{user_message}\n\n{service_status}\n\n<project_files>\n{file_tree}\n</project_files>"
        else:
            enhanced_user_message = f"{user_message}\n\n<project_files>\n{file_tree}\n</project_files>"

        # Handle both string messages and content arrays from streaming API
        if isinstance(user_message, list):
            # Already in OpenAI content array format - extract text and enhance it
            original_text = ""
            image_items = []
            
            for item in user_message:
                if item.get("type") == "text":
                    original_text = item.get("text", "")
                elif item.get("type") == "image_url":
                    image_items.append(item)
            
            # Enhance the text portion with project context
            if mode == "step" and step_info and step_info.get('show_service_status', False):
                enhanced_text = f"{original_text}\n\n{service_status}\n\n<project_files>\n{file_tree}\n</project_files>"
            else:
                enhanced_text = f"{original_text}\n\n<project_files>\n{file_tree}\n</project_files>"
            
            # Create enhanced content array
            content_array = [{"type": "text", "text": enhanced_text}] + image_items
            
            messages.append({"role": "user", "content": content_array})
            self.conversation_history.append({"role": "user", "content": content_array})
            
            # Count images for logging
            image_count = len(image_items)
            if image_count > 0:
                print(f"📷 Added message with {image_count} images to LLM (OpenAI format)")
            else:
                print(f"📝 Added text message to LLM")
        else:
            # String message - convert to text-only content array for consistency  
            content_array = [{"type": "text", "text": enhanced_user_message}]
            messages.append({"role": "user", "content": content_array})
            self.conversation_history.append({"role": "user", "content": content_array})
            print(f"📝 Added text message to LLM")
        self._save_conversation_history()  # Real-time save - triggers summarization if needed

        print(f"🔍 Sending {len(messages)} messages to model:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content_preview = msg.get('content', '')[:100] + '...' if len(msg.get('content', '')) > 100 else msg.get('content', '')
            print(f"  {i+1}. {role}: {content_preview}")
        print()

        # Start initial generation (async to allow concurrent requests)
        response_content = await self._async_coder(messages=messages, streaming_callback=streaming_callback)

        # Add final response to conversation history and save in real-time
        if response_content:
            self.conversation_history.append({"role": "assistant", "content": response_content})
            self._save_conversation_history()  # Real-time save - triggers summarization if needed

        if mode == "step":
            print(f"✅ Step {step_info.get('step_number', 'N/A')} processed successfully")
            return True
        else:
            print(f"✅ Update request processed successfully")
            return response_content


    def _handle_check_errors_interrupt(self, action: dict) -> dict:
        """Handle check_errors action by calling the comprehensive error check API"""
        print(f"🔍 CODER: Handling check_errors interrupt")

        try:
            project_id = getattr(self, 'project_id', None)
            if not project_id:
                print("❌ CODER: No project_id found for error checking")
                return None

            print(f"📡 CODER: Calling error check API for project: {project_id}")

            # Import requests for API call
            import requests
            import json

            # Call the error check API we implemented
            api_base_url = getattr(self, 'api_base_url', 'http://localhost:8000')
            if api_base_url.endswith('/api'):
                api_base_url = api_base_url[:-4]  # Remove '/api' suffix

            error_check_url = f"{api_base_url}/api/projects/{project_id}/error-check"

            print(f"📡 CODER: Calling {error_check_url}")

            response = requests.get(error_check_url, timeout=60)

            if response.status_code == 200:
                result = response.json()
                print(f"✅ CODER: Error check completed successfully")
                print(f"📊 CODER: Overall status: {result.get('summary', {}).get('overall_status', 'unknown')}")
                print(f"📈 CODER: Total errors: {result.get('summary', {}).get('total_errors', 0)}")

                # Log summary of errors found
                backend_errors = result.get('backend', {}).get('error_count', 0)
                frontend_errors = result.get('frontend', {}).get('error_count', 0)

                if backend_errors > 0:
                    print(f"🐍 CODER: Backend has {backend_errors} errors")
                else:
                    print("🐍 CODER: Backend is clean")

                if frontend_errors > 0:
                    print(f"⚛️  CODER: Frontend has {frontend_errors} errors")
                else:
                    print("⚛️  CODER: Frontend is clean")

                return result
            else:
                print(f"❌ CODER: Error check API failed with status {response.status_code}")
                print(f"❌ CODER: Response: {response.text}")
                return None

        except requests.exceptions.ConnectionError:
            print("❌ CODER: Connection error - is the API server running?")
            return None
        except requests.exceptions.Timeout:
            print("❌ CODER: Error check request timed out")
            return None
        except Exception as e:
            print(f"❌ CODER: Exception during error check: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _handle_check_logs_interrupt(self, action: dict) -> dict:
        """Handle check_logs action using Modal app logs command for serverless backend"""
        print(f"📋 CODER: Handling check_logs interrupt for serverless backend")

        try:
            project_id = getattr(self, 'project_id', None)
            if not project_id:
                print("❌ CODER: No project_id found for log checking")
                return None

            # Get parameters from action
            service = action.get('service', 'backend')

            if service == 'backend':
                print(f"🔍 Getting backend info for project: {project_id}")

                import subprocess

                # Get backend deployment info using reusable function
                backend_info = self._get_backend_deployment_info(project_id)

                if backend_info['status'] == 'success':
                    app_name = generate_short_app_name(project_id)

                    if app_name:
                        print(f"✅ Found backend app name: {app_name}")

                        # Find actual app ID for reliability (app names sometimes fail)
                        print(f"🔍 Finding app ID for app name: {app_name}")
                        app_identifier = app_name  # Default fallback

                        try:
                            # Get app list to find the actual app ID
                            list_cmd = ["modal", "app", "list", "--json"]
                            list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=10)

                            if list_result.returncode == 0:
                                import json
                                apps = json.loads(list_result.stdout)

                                # Find matching app by name or description
                                for app in apps:
                                    app_desc = app.get('description', '')
                                    if app_name in app_desc or project_id in app_desc:
                                        app_id = app.get('app_id')
                                        app_state = app.get('state', 'unknown')
                                        print(f"✅ Found app: {app_id} (state: {app_state})")
                                        app_identifier = app_id
                                        break
                                else:
                                    print(f"⚠️ No matching app found, using app name: {app_name}")
                            else:
                                print(f"⚠️ Failed to list apps, using app name: {app_name}")
                        except Exception as e:
                            print(f"⚠️ Error finding app ID: {e}, using app name: {app_name}")

                        # Use Modal CLI to get logs (latest 200 lines max)
                        # print(f"📡 Getting logs from Modal app: {app_identifier}")

                        try:
                            # Use Popen to properly handle streaming logs
                            cmd = ["modal", "app", "logs", app_identifier, "--timestamps"]
                            print(f"🔍 Getting recent logs from Modal (will collect for 5s): {app_identifier}")

                            import time
                            import threading

                            # Start the process
                            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                            # Collect output for 5 seconds
                            output_lines = []

                            def read_output():
                                try:
                                    while True:
                                        line = process.stdout.readline()
                                        if not line:
                                            break
                                        output_lines.append(line.strip())
                                except:
                                    pass

                            # Start reading in a separate thread
                            reader_thread = threading.Thread(target=read_output)
                            reader_thread.daemon = True
                            reader_thread.start()

                            # Wait for 5 seconds
                            time.sleep(5)

                            # Terminate the process
                            process.terminate()

                            # Wait a bit for thread to finish
                            reader_thread.join(timeout=1)

                            # Process the collected logs
                            if output_lines:
                                # Limit to last 200 lines if we have too many
                                log_lines = output_lines[-200:] if len(output_lines) > 200 else output_lines
                                logs_output = '\n'.join(log_lines)

                                # Extract errors and warnings for service status
                                error_lines = [line for line in log_lines if '❌' in line or 'error' in line.lower() or 'failed' in line.lower()]
                                warning_lines = [line for line in log_lines if '⚠️' in line or 'warning' in line.lower()]
                                success_lines = [line for line in log_lines if '✅' in line or 'success' in line.lower()]

                                print(f"✅ Retrieved {len(log_lines)} log lines from Modal")
                                print(f"📊 Found {len(error_lines)} errors, {len(warning_lines)} warnings")

                                return {
                                    'status': 'success',
                                    'service': service,
                                    'app_name': app_name,
                                    'app_id': app_identifier,
                                    'logs': logs_output,
                                    'line_count': len(log_lines),
                                    'error_count': len(error_lines),
                                    'warning_count': len(warning_lines),
                                    'success_count': len(success_lines),
                                    'recent_errors': error_lines[-5:] if error_lines else [],  # Last 5 errors
                                    'recent_warnings': warning_lines[-3:] if warning_lines else [],  # Last 3 warnings
                                    'source': 'modal_cli_streaming'
                                }
                            else:
                                # No output collected - check if there was an error
                                try:
                                    stderr_output = process.stderr.read() if process.stderr else ""
                                    error_msg = stderr_output.strip() if stderr_output else "No logs collected from Modal"
                                except:
                                    error_msg = "No logs collected and stderr unavailable"

                                print(f"❌ No logs collected from Modal: {error_msg}")
                                return {
                                    'status': 'error',
                                    'error': f"No logs collected: {error_msg}",
                                    'service': service
                                }

                        except Exception as e:
                            print(f"❌ Error getting Modal logs: {e}")
                            return {
                                'status': 'error',
                                'error': f"Error getting Modal logs: {str(e)}",
                                'service': service
                            }
                    else:
                        print("❌ No app_name found in backend deployment metadata")
                        return {
                            'status': 'error',
                            'error': "No app_name found in backend deployment metadata",
                            'service': service
                        }
                else:
                    error_msg = backend_info['error']
                    print(f"❌ {error_msg}")
                    return {
                        'status': 'error',
                        'error': error_msg,
                        'service': service
                    }

            elif service == 'frontend':
                # Frontend logs from browser console (stored in Cosmos DB via server_info API)
                print(f"🔍 Getting frontend console logs for project: {project_id}")

                try:
                    import requests
                    import time

                    # Call our server_info API to get stored frontend logs
                    api_url = f"http://localhost:8084/{project_id}/logs/logs?limit=50"

                    print(f"📡 Fetching frontend logs from: {api_url}")
                    response = requests.get(api_url, timeout=10)

                    if response.status_code == 200:
                        data = response.json()

                        if data.get('status') == 'success':
                            entries = data.get('entries', [])
                            total_count = data.get('total_count', 0)

                            print(f"✅ Retrieved {len(entries)} frontend console logs")

                            # Format logs for display
                            formatted_logs = []
                            error_count = 0
                            warning_count = 0

                            for entry in entries:
                                log_type = entry.get('logType', 'log')
                                message = entry.get('message', '')
                                time_str = entry.get('time', '')

                                # Count errors and warnings
                                if log_type == 'error':
                                    error_count += 1
                                elif log_type == 'warn':
                                    warning_count += 1

                                # Format log line
                                formatted_logs.append(f"[{time_str}] {log_type.upper()}: {message}")

                            logs_output = '\n'.join(formatted_logs) if formatted_logs else "No console logs found"

                            # Extract recent errors for quick diagnosis
                            recent_errors = [log for log in formatted_logs if 'ERROR:' in log][-5:]
                            recent_warnings = [log for log in formatted_logs if 'WARN:' in log][-3:]

                            return {
                                'status': 'success',
                                'service': service,
                                'logs': logs_output,
                                'line_count': len(entries),
                                'error_count': error_count,
                                'warning_count': warning_count,
                                'total_stored': total_count,
                                'recent_errors': recent_errors,
                                'recent_warnings': recent_warnings,
                                'source': 'cosmos_db_console_logs'
                            }
                        else:
                            error_msg = data.get('error', 'Unknown error from logs API')
                            print(f"❌ Logs API returned error: {error_msg}")
                            return {
                                'status': 'error',
                                'error': f"Logs API error: {error_msg}",
                                'service': service
                            }
                    else:
                        print(f"❌ HTTP error getting frontend logs: {response.status_code}")
                        return {
                            'status': 'error',
                            'error': f"HTTP {response.status_code} from logs API",
                            'service': service
                        }

                except Exception as e:
                    print(f"❌ Error getting frontend logs: {e}")
                    return {
                        'status': 'error',
                        'error': f"Error getting frontend logs: {str(e)}",
                        'service': service
                    }

            else:
                print(f"❌ Unknown service type: {service}")
                return {
                    'status': 'error',
                    'error': f"Unknown service type: {service}. Use 'backend' or 'frontend'",
                    'service': service
                }
        except Exception as e:
            print(f"❌ CODER: Exception during log check: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _handle_check_network_interrupt(self, action: dict) -> dict:
        """Handle check_network action for frontend network requests from Cosmos DB"""
        print(f"📋 CODER: Handling check_network interrupt for frontend")
        try:
            project_id = getattr(self, 'project_id', None)
            if not project_id:
                print("❌ CODER: No project_id found for network checking")
                return None

            # Frontend network requests from browser (stored in Cosmos DB via server_info API)
            print(f"🔍 Getting frontend network requests for project: {project_id}")
            try:
                import requests
                # Call our server_info API to get stored frontend network requests
                api_url = f"http://localhost:8084/{project_id}/logs/network?limit=50"
                print(f"📡 Fetching network requests from: {api_url}")
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        entries = data.get('entries', [])
                        total_count = data.get('total_count', 0)
                        print(f"✅ Retrieved {len(entries)} frontend network requests")

                        # Format network requests for display
                        formatted_requests = []
                        error_count = 0
                        warning_count = 0
                        success_count = 0

                        for entry in entries:
                            method = entry.get('method', 'GET')
                            url = entry.get('url', '')
                            status = entry.get('status', 0)
                            response_time = entry.get('responseTime', 0)
                            time_str = entry.get('time', '')

                            # Count by status codes
                            if status >= 400:
                                error_count += 1
                                status_indicator = "❌"
                            elif status >= 300:
                                warning_count += 1
                                status_indicator = "⚠️"
                            elif status >= 200:
                                success_count += 1
                                status_indicator = "✅"
                            else:
                                status_indicator = "❓"

                            formatted_requests.append(
                                f"[{time_str}] {status_indicator} {method} {url} - {status} ({response_time}ms)"
                            )

                        requests_output = '\n'.join(formatted_requests) if formatted_requests else "No network requests found"

                        # Extract recent errors for quick diagnosis
                        recent_errors = [req for req in formatted_requests if '❌' in req][-5:]
                        recent_warnings = [req for req in formatted_requests if '⚠️' in req][-3:]

                        return {
                            'status': 'success',
                            'service': 'frontend',
                            'requests': requests_output,
                            'request_count': len(entries),
                            'error_count': error_count,
                            'warning_count': warning_count,
                            'success_count': success_count,
                            'total_stored': total_count,
                            'recent_errors': recent_errors,
                            'recent_warnings': recent_warnings,
                            'source': 'cosmos_db_network_requests'
                        }
                    else:
                        error_msg = data.get('error', 'Unknown error from network API')
                        print(f"❌ Network API returned error: {error_msg}")
                        return {
                            'status': 'error',
                            'error': f"Network API error: {error_msg}",
                            'service': 'frontend'
                        }
                else:
                    print(f"❌ HTTP error getting frontend network requests: {response.status_code}")
                    return {
                        'status': 'error',
                        'error': f"HTTP {response.status_code} from network API",
                        'service': 'frontend'
                    }
            except Exception as e:
                print(f"❌ Error getting frontend network requests: {e}")
                return {
                    'status': 'error',
                    'error': f"Error getting frontend network requests: {str(e)}",
                    'service': 'frontend'
                }

        except Exception as e:
            print(f"❌ CODER: Exception during network check: {e}")
            import traceback
            traceback.print_exc()
            return None

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
        """Handle run_command action with VM API integration"""
        command = action.get('command')
        working_dir = action.get('working_dir') or action.get('cwd')

        print(f"💻 Processing terminal command: {command}")
        if working_dir:
            print(f"   Working directory: {working_dir}")

        # Normalize working_dir: treat '.', '', or None as None (project root)
        if working_dir in ['.', '']:
            working_dir = None

        # Validate working_dir if specified
        if working_dir and working_dir not in ['frontend', 'backend']:
            return f"`working_dir` must be 'frontend', 'backend', or null for root. It cannot be {working_dir}."

        # Use PackageManager to extract and handle packages
        if command:
            package_manager = PackageManager(self.cloud_storage, self.project_id)
            package_info = package_manager.extract_packages_from_command(command)
            
            if package_info:
                package_type = package_info['type']
                packages = package_info['packages']
                
                # Log extracted packages with versions
                package_strs = []
                for pkg_name, version in packages:
                    if version:
                        package_strs.append(f"{pkg_name}{version}")
                    else:
                        package_strs.append(pkg_name)
                
                print(f"📦 Detected {package_type} packages: {package_strs}")
                
                # Asynchronously update dependency files
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        update_result = loop.run_until_complete(
                            package_manager.update_dependency_files(command, working_dir)
                        )
                        if update_result:
                            print(f"✅ {update_result}")
                    finally:
                        loop.close()
                except Exception as e:
                    print(f"⚠️ Failed to update dependency files: {e}")

        # Unescape JSON in curl commands (LLM often escapes quotes)
        if command and 'curl' in command and '\\"' in command:
            # Unescape JSON quotes in curl commands for proper execution
            original_command = command
            command = command.replace('\\"', '"')
            print(f"🔧 Unescaped curl command JSON quotes")
            print(f"   Original: {original_command[:100]}...")
            print(f"   Fixed: {command[:100]}...")

        # # Prepend cd command if working_dir is specified
        # if working_dir:
        #     original_command = command
        #     command = f"cd {working_dir} && {command}"
        #     print(f"🔧 Prepended cd command for working directory")
        #     print(f"   Original: {original_command}")
        #     print(f"   Modified: {command}")

        # Execute command using VM API
        return self._execute_command_on_vm(command, working_dir, action)

    def _execute_command_on_vm(self, command: str, working_dir: str, action: dict) -> str:
        """Execute command on VM using the VM API"""
        try:
            # Run async VM API call in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(vm_api.execute_command(self.project_id, command, working_dir))
            finally:
                loop.close()

            # The VM API returns format: {stdout, stderr, return_code, working_directory}
            # Check if command succeeded (return_code 0 means success)
            success = result["return_code"] == 0
            output = result["stdout"]
            stderr = result["stderr"]

            if stderr:
                output += f"\n[stderr]: {stderr}"

            if success:
                print(f"✅ VM Command completed successfully (return code {result['return_code']})")
                print(f"📄 Output: {len(output)} characters")
            else:
                print(f"❌ VM Command failed (return code {result['return_code']})")
                if stderr:
                    print(f"📄 Error: {stderr}")

            # Return the command output directly
            return output

        except Exception as e:
            error_msg = f"VM API Error: {str(e)}"
            print(f"❌ {error_msg}")

            # Return error message directly
            return error_msg

    def _handle_frontend_command_interrupt(self, command: str, cwd: str, action: dict) -> str:
        """Handle frontend commands with ACTUAL interrupt and cloud storage flow"""
        print(f"🌐 FRONTEND COMMAND DETECTED: {command}")
        print(f"📤 INTERRUPTING STREAM - Frontend will execute this command...")

        # Save current conversation state to cloud storage before interrupt (async background)
        if self.cloud_storage and self.project_id:
            try:
                print(f"☁️ Starting background save of conversation state before frontend interrupt...")
                self._run_cloud_operation_background(
                    "Save conversation history before interrupt",
                    self.cloud_storage.save_conversation_history,
                    self.project_id,
                    self.conversation_history.copy()  # Make a copy to avoid race conditions
                )
                print(f"✅ Background save of conversation state initiated")
            except Exception as e:
                print(f"⚠️ Error initiating background save of conversation state: {e}")

        # CRITICAL: Raise special exception to interrupt the stream
        # This will break out of the coder iteration loop and end streaming
        # Frontend will receive this command via the stream and execute it
        # Then frontend will send action_result back via chatstream API
        raise FrontendCommandInterrupt(command, cwd, action, self.project_id)

    def _get_backend_deployment_info(self, project_id: str = None) -> dict:
        """
        Reusable function to get backend deployment information for a project
        Returns backend deployment metadata including URL, app_name, etc.
        """
        if not project_id:
            project_id = getattr(self, 'project_id', None)

        if not project_id:
            return {
                'status': 'error',
                'error': 'No project_id provided or available'
            }

        try:
            project_metadata = self.cloud_storage.load_project_metadata(project_id)

            if not project_metadata:
                return {
                    'status': 'error',
                    'error': f'No metadata found for project {project_id}'
                }

            backend_deployment = project_metadata.get('backend_deployment')
            if not backend_deployment:
                return {
                    'status': 'error',
                    'error': 'No backend deployment found for this project'
                }

            return {
                'status': 'success',
                'project_id': project_id,
                'backend_deployment': backend_deployment,
                'app_name': backend_deployment.get('app_name'),
                'url': backend_deployment.get('url'),
                'docs_url': backend_deployment.get('docs_url'),
                'secret_name': backend_deployment.get('secret_name'),
                'deployed_at': backend_deployment.get('deployed_at')
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': f'Error loading backend deployment info: {str(e)}'
            }

    def _build_service_status_context(self, project_id: str = None) -> str:
        """Build service status context for model to understand current backend health"""

        if not project_id:
            project_id = getattr(self, 'project_id', None)

        if not project_id:
            return ""

        try:
            # Get backend deployment info
            backend_info = self._get_backend_deployment_info(project_id)

            context_parts = ['<service_status>']

            if backend_info['status'] == 'success':
                # Backend is deployed, check for errors using our enhanced log handler
                try:
                    # Temporarily set project_id for log checking
                    original_project_id = getattr(self, 'project_id', None)
                    self.project_id = project_id

                    log_result = self._handle_check_logs_interrupt({'service': 'backend'})

                    # Restore original project_id
                    self.project_id = original_project_id

                    if log_result and log_result.get('status') == 'success':
                        error_count = log_result.get('error_count', 0)
                        warning_count = log_result.get('warning_count', 0)
                        recent_errors = log_result.get('recent_errors', [])

                        # Determine health status
                        health = 'healthy' if error_count == 0 else 'degraded'

                        context_parts.extend([
                            '',
                            '## Backend',
                            f'- **Status**: deployed',
                            f'- **URL**: {backend_info.get("url", "N/A")}',
                            f'- **Health**: {health}',
                            f'- **Errors**: {error_count}',
                            f'- **Warnings**: {warning_count}'
                        ])

                        # Add recent error snippets if any (limited to keep context manageable)
                        if recent_errors:
                            context_parts.extend([
                                '',
                                '### Recent Issues',
                                ''
                            ])
                            for error in recent_errors[:3]:  # Limit to 3 most recent
                                # Clean error message for context
                                clean_error = error.replace('❌', '').replace('🚨', '').strip()
                                # Truncate long errors
                                if len(clean_error) > 100:
                                    clean_error = clean_error[:97] + '...'
                                context_parts.append(f'- {clean_error}')

                            if error_count > 0:
                                context_parts.extend([
                                    '',
                                    '> Use check_logs action to see full error details',
                                    '> After fixing errors, call restart_backend to redeploy with latest changes'
                                ])
                    else:
                        # Log check failed, but backend is deployed
                        context_parts.extend([
                            '',
                            '## Backend',
                            f'- **Status**: deployed',
                            f'- **URL**: {backend_info.get("url", "N/A")}',
                            f'- **Health**: unknown',
                            '- **Note**: Backend is deployed and starting up (normal behavior)'
                        ])

                except Exception as log_error:
                    # Log error checking failed, but backend deployment exists
                    context_parts.extend([
                        '',
                        '## Backend',
                        f'- **Status**: deployed',
                        f'- **URL**: {backend_info.get("url", "N/A")}',
                        f'- **Health**: unknown',
                        f'- **Check Error**: Log check failed: {str(log_error)[:50]}...'
                    ])
            else:
                # Backend deployment error or not found
                context_parts.extend([
                    '',
                    '## Backend',
                    '- **Status**: error',
                    f'- **Error**: {backend_info.get("error", "Unknown deployment error")}'
                ])

            # Add basic frontend status (limited info available)
            context_parts.extend([
                '',
                '## Frontend',
                '- **Status**: webcontainer',
                '- **Preview Available**: true',
                '- **Note**: Frontend runs in WebContainer - logs will be available after this inital version is completed and the user has used it',
                ''
            ])

            context_parts.append('</service_status>')

            return '\n'.join(context_parts)

        except Exception as e:
            # Fallback if service status building fails
            return f'<service_status><error>Failed to get service status: {str(e)}</error></service_status>'

    def _update_backend_deployment_info(self, backend_url: str, app_name: str, project_id: str = None):
        """
        Update backend deployment information in project metadata
        """
        if not project_id:
            project_id = getattr(self, 'project_id', None)

        if not project_id:
            print("⚠️  No project_id available to save backend deployment info")
            return

        try:
            from datetime import datetime

            # Load existing metadata
            project_metadata = self.cloud_storage.load_project_metadata(project_id) or {}

            # Update backend deployment info
            project_metadata['backend_deployment'] = {
                'url': backend_url,
                'app_name': app_name,
                'docs_url': f"{backend_url}/docs",
                'secret_name': f"{app_name}-secrets",
                'deployed_at': datetime.now().isoformat()
            }

            # Save updated metadata in background
            future = self._save_metadata_background(project_metadata)
            print(f"🌥️ Started background save of backend deployment info for project {project_id}")

        except Exception as e:
            print(f"❌ Error saving backend deployment info: {str(e)}")

    def _handle_backend_command_interrupt(self, command: str, cwd: str, action: dict) -> str:
        """Handle backend commands by calling the deployed backend's terminal API"""
        print(f"🔧 BACKEND COMMAND DETECTED: {command}")
        print(f"📡 Executing command in deployed backend container...")

        # Get backend deployment info using reusable function
        backend_info = self._get_backend_deployment_info()

        if backend_info['status'] != 'success':
            error_msg = backend_info['error']
            print(f"❌ {error_msg}")
            return f"❌ {error_msg}. Deploy backend first using the backend deployment action."

        backend_url = backend_info['url']
        app_name = backend_info['app_name']

        print(f"🎯 Calling backend terminal API: {backend_url} (app: {app_name})")

        try:
            import requests

            # Call the hidden terminal API endpoint
            terminal_url = f"{backend_url}/_internal/terminal"
            command_data = {
                'command': command,
                'cwd': '/root' if cwd == 'backend' else '/root',  # Map to backend container paths
                'timeout': 60  # 1 minute timeout for backend commands
            }

            print(f"📤 Sending command to backend: {command}")

            response = requests.post(terminal_url, json=command_data, timeout=70)  # Slightly longer than backend timeout

            if response.status_code == 200:
                result = response.json()

                if result.get('status') == 'success':
                    stdout = result.get('stdout', '')
                    stderr = result.get('stderr', '')
                    exit_code = result.get('exit_code', 0)

                    output_parts = []
                    if stdout:
                        output_parts.append(f"STDOUT:\n{stdout}")
                    if stderr and exit_code != 0:
                        output_parts.append(f"STDERR:\n{stderr}")

                    if not output_parts:
                        output_parts.append("Command executed successfully (no output)")

                    result_text = f"✅ Backend command executed successfully (exit code {exit_code}):\n\n" + "\n\n".join(output_parts)
                    print(f"✅ Backend command completed with exit code {exit_code}")
                    return result_text
                else:
                    # Command failed
                    error = result.get('error', 'Unknown error')
                    stderr = result.get('stderr', '')
                    exit_code = result.get('exit_code', 1)

                    error_text = f"❌ Backend command failed (exit code {exit_code}): {error}"
                    if stderr and stderr != error:
                        error_text += f"\n\nSTDERR:\n{stderr}"

                    print(f"❌ Backend command failed: {error}")
                    return error_text
            else:
                error_msg = f"Backend terminal API returned HTTP {response.status_code}: {response.text}"
                print(f"❌ API call failed: {error_msg}")
                return f"❌ Failed to execute backend command: {error_msg}"

        except requests.exceptions.Timeout:
            error_msg = "Backend command timed out (>60s)"
            print(f"❌ {error_msg}")
            return f"❌ {error_msg}"
        except Exception as e:
            error_msg = f"Error executing backend command: {str(e)}"
            print(f"❌ {error_msg}")
            return f"❌ {error_msg}"

    def _handle_backend_command_placeholder(self, command: str, cwd: str, action: dict) -> str:
        """Handle backend commands with realistic placeholder responses"""
        import time

        print(f"⚙️ BACKEND COMMAND: {command}")
        print(f"🔧 Generating realistic placeholder response...")

        # Add 2-second delay as specified in requirements
        print(f"⏱️ Simulating backend command execution (2s delay)...")
        time.sleep(2.0)

        # Generate realistic placeholder based on command type
        placeholder_response = self._generate_backend_command_placeholder(command)

        print(f"📋 Generated backend command placeholder response")
        print(f"📄 Response length: {len(placeholder_response)} characters")

        # TODO: Phase 6 Implementation - Backend Command Integration
        # In the complete implementation, this should:
        # 1. Send command to VPS backend service
        # 2. Execute command in proper backend container/environment
        # 3. Return real command output
        # 4. Handle errors and edge cases properly
        # Currently using placeholder responses to prepare for VPS integration

        return placeholder_response

    def _generate_frontend_command_placeholder(self, command: str) -> str:
        """Generate realistic frontend command placeholder responses"""
        command_lower = command.lower().strip()

        # npm/yarn commands
        if 'npm install' in command_lower or 'npm i' in command_lower:
            return """npm WARN deprecated some-package@1.0.0: Package deprecated
npm WARN deprecated another-package@2.0.0: Use new-package instead

added 1234 packages, and audited 1235 packages in 12s

156 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities"""

        elif 'npm run dev' in command_lower or 'npm start' in command_lower:
            return """
> vite


  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help

🎯 Frontend development server started successfully!
⚡ Hot reload enabled - your changes will appear instantly
📝 Edit src/App.tsx to see live updates"""

        elif 'npm run build' in command_lower:
            return """> build
> tsc && vite build

vite v5.1.0 building for production...
✓ 34 modules transformed.
dist/index.html                   0.46 kB │ gzip:  0.30 kB
dist/assets/index-DiwrgTda.css    1.23 kB │ gzip:  0.65 kB
dist/assets/index-BNzLxOAB.js    143.21 kB │ gzip: 46.13 kB
✓ built in 1.45s

✅ Frontend build completed successfully!
📦 Production files ready in /dist folder"""

        elif 'npm test' in command_lower:
            return """> test
> vitest run

 RUN  v1.2.0
 ✓ src/App.test.tsx (3)
   ✓ renders calculator component
   ✓ performs basic calculations
   ✓ handles edge cases

 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  10:30:15 AM
   Duration  892ms

✅ All tests passed!"""

        elif 'yarn' in command_lower and 'install' in command_lower:
            return """yarn install v1.22.19
info No lockfile found.
[1/4] Resolving packages...
[2/4] Fetching packages...
[3/4] Linking dependencies...
[4/4] Building fresh packages...
success Saved lockfile.
Done in 8.45s."""

        elif any(cmd in command_lower for cmd in ['ls', 'dir']):
            return """node_modules/
public/
src/
  components/
  pages/
  stores/
  App.css
  App.tsx
  index.css
  main.tsx
.gitignore
eslint.config.js
index.html
package.json
tsconfig.json
vite.config.ts"""

        # Default frontend command response
        else:
            return f"""Command executed in frontend environment
Working directory: frontend/
Command: {command}
Exit code: 0

✅ Frontend command completed successfully"""

    def _generate_backend_command_placeholder(self, command: str) -> str:
        """Generate realistic backend command placeholder responses"""
        command_lower = command.lower().strip()

        # Python/pip commands
        if 'pip install' in command_lower:
            if '-r requirements.txt' in command_lower:
                return """Collecting fastapi==0.104.1
  Using cached fastapi-0.104.1-py3-none-any.whl (92 kB)
Collecting uvicorn[standard]==0.24.0
  Using cached uvicorn-0.24.0-py3-none-any.whl (59 kB)
Collecting sqlalchemy==2.0.23
  Using cached SQLAlchemy-2.0.23-py3-none-any.whl (3.1 MB)
Collecting pydantic==2.5.0
  Using cached pydantic-2.5.0-py3-none-any.whl (381 kB)
Installing collected packages: fastapi, uvicorn, sqlalchemy, pydantic
Successfully installed fastapi-0.104.1 pydantic-2.5.0 sqlalchemy-2.0.23 uvicorn-0.24.0

✅ Backend dependencies installed successfully!"""
            else:
                package = command_lower.split('pip install')[-1].strip()
                return f"""Collecting {package}
  Using cached {package}-1.0.0-py3-none-any.whl
Installing collected packages: {package}
Successfully installed {package}-1.0.0

✅ Package {package} installed successfully!"""

        elif 'python app.py' in command_lower or 'python -m uvicorn' in command_lower:
            return """INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.

🚀 Backend server started successfully!
📡 API endpoints available at http://localhost:8000
📚 API documentation at http://localhost:8000/docs
🔧 Admin interface at http://localhost:8000/redoc"""

        elif 'python -c' in command_lower:
            return """Python 3.10.12 (main, Nov 20 2023, 15:14:05) [GCC 11.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.

✅ Python environment ready"""

        elif any(cmd in command_lower for cmd in ['pytest', 'python -m pytest']):
            return """========================= test session starts ==========================
platform linux -- Python 3.10.12, pytest-7.4.3
rootdir: /app/backend
collected 8 items

test_auth_api.py ........                                           [100%]

========================== 8 passed in 2.34s ==========================

✅ All backend tests passed!"""

        elif 'curl' in command_lower and 'health' in command_lower:
            return """{
  "status": "healthy",
  "timestamp": "2025-08-19T19:00:00Z",
  "version": "1.0.0",
  "database": "connected",
  "services": {
    "auth": "operational",
    "api": "operational"
  }
}

✅ Backend health check passed!"""

        elif any(cmd in command_lower for cmd in ['ls', 'dir']):
            return """app.py
requirements.txt
database/
  __init__.py
  user.py
models/
  __init__.py
  auth_models.py
routes/
  __init__.py
  calculator.py
services/
  __init__.py
  auth_service.py
  health_service.py
utils/
  __init__.py
  auth.py
docs/
  DATABASE_GUIDE.md
AUTH_README.md
PROJECT_STRUCTURE.md
README.md
test_auth_api.py"""

        elif 'docker' in command_lower and 'ps' in command_lower:
            return """CONTAINER ID   IMAGE          COMMAND                  CREATED       STATUS       PORTS                    NAMES
abc123def456   backend:latest "python app.py"         2 hours ago   Up 2 hours   0.0.0.0:8000->8000/tcp   backend-container
def789abc012   postgres:13    "docker-entrypoint.s…"  2 hours ago   Up 2 hours   0.0.0.0:5432->5432/tcp   postgres-db

✅ Backend containers running successfully"""

        # Default backend command response
        else:
            return f"""Command executed in backend environment
Working directory: backend/
Command: {command}
Exit code: 0

✅ Backend command completed successfully"""

    def _handle_update_file_interrupt(self, action: dict) -> str:
        """Handle update_file action - supports both diff blocks and legacy format"""
        try:
            # Lazy import and initialize the update file handler
            if not hasattr(self, '_update_handler'):
                import sys
                import os

                # Import from local directory
                from update_file_handler import UpdateFileHandler

                # Initialize handler with our callback methods
                self._update_handler = UpdateFileHandler(
                    read_file_callback=self._read_file_via_api,
                    update_file_callback=self._update_file_via_api
                )
                print("✅ Update file handler initialized with diff support")

            # Use the handler to process the update
            result = self._update_handler.handle_update_file(action)

            # Handle the new return format (dict with success/message)
            if isinstance(result, dict):
                return result
            else:
                # Fallback for legacy string return format
                return {"success": True, "message": result}

        except Exception as e:
            print(f"❌ Error initializing update handler: {e}")
            print("🔄 Falling back to legacy update method")
            legacy_result = self._handle_legacy_update_file(action)
            return {"success": False, "message": f"Handler error: {e}. Fallback result: {legacy_result}"}

    def _handle_legacy_update_file(self, action: dict) -> str:
        """Fallback legacy update file method"""
        file_path = action.get('path') or action.get('filePath')
        file_content = action.get('content', '')

        # Remove backticks if present
        file_content = self._remove_backticks_from_content(file_content)

        # Check if file content is empty after processing
        if not file_content or file_content.strip() == '':
            print(f"⚠️ Empty file content detected for update: {file_path}")
            return f"❌ File update blocked: Empty content detected for '{file_path}'"

        print(f"💾 Updating file (legacy): {file_path}")
        print(f"📄 Content length: {len(file_content)} characters")

        # Update file via API
        update_result = self._update_file_via_api(file_path, file_content)

        if update_result and update_result.get('status') == 'updated':
            print(f"✅ File updated successfully: {file_path}")
            return f"File '{file_path}' updated successfully (legacy mode)"
        else:
            error = update_result.get('error', 'Unknown error') if update_result else 'Failed to update file'
            print(f"❌ File update failed: {error}")
            return f"Failed to update file '{file_path}': {error}"

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

        if not file_path:
            print("❌ Missing file path in creation action")
            return None

        # Remove backticks if present
        file_content = self._remove_backticks_from_content(file_content)

        # Check if file content is empty after processing
        if not file_content or file_content.strip() == '':
            print(f"⚠️ Empty file content detected for: {file_path}")
            return {
                'file_path': file_path,
                'success': False,
                'empty_file_warning': True,
                'message': f"""❌ File creation blocked: Empty content detected for '{file_path}'

Are you sure you want to create an empty file? If not, please add the actual content inside the action tag.

Example of proper usage:
<action type="file" path="{file_path}">
# Your actual file content goes here
print("Hello, World!")

def example_function():
    return "This is actual content"
</action>

If you really want to create an empty file, please confirm by responding with the action again and explicitly stating it should be empty."""
            }

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
                'typescript_errors': result.get("typescript_errors", ""),
                'file_content': file_content  # ✅ Include actual file content
            }
        else:
            print(f"❌ File creation failed")
            return None

    # if no action is triggered, process the remaining actions
    def _process_remaining_actions(self, content: str):
        """Process any remaining actions from the complete response"""
        parser = StreamingXMLParser()
        parser.buffer = content

        file_actions = []
        route_actions = []
        todo_actions = []

        # Extract all actions from the complete response
        web_search_actions = []

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
                elif action.get('type') == 'web_search':
                    web_search_actions.append(action)
                elif action.get('type', '').startswith('todo_'):
                    todo_actions.append(action)

        # Process file actions
        for action in file_actions:
            self._process_file_action(action)

        # Process web search actions
        for action in web_search_actions:
            if hasattr(self, '_handle_web_search_interrupt'):
                search_result = self._handle_web_search_interrupt(action)
                if search_result and search_result.get('success'):
                    print(f"🔍 Processed web search: {search_result.get('query')}")
                else:
                    print(f"❌ Failed web search: {search_result.get('error') if search_result else 'Unknown error'}")

        # Process todo actions
        for action in todo_actions:
            if hasattr(self, '_handle_todo_actions'):
                self._handle_todo_actions(action)
                print(f"📋 Processed remaining todo action: {action.get('type')}")

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

    def _handle_start_backend_interrupt(self, action: dict) -> dict:
        """Handle start_backend action during interrupt - Deploy backend to Modal.com"""
        print(f"🚀 Deploying backend service to Modal.com...")

        try:
            # Always check for existing backend deployment info
            backend_info = self._get_backend_deployment_info()
            has_deployment_history = backend_info.get('status') == 'success'

            # If backend exists and has a working URL, return it
            if has_deployment_history and backend_info.get('url'):
                existing_url = backend_info.get('url')
                print(f"🔍 Found existing backend deployment: {existing_url}")

                # Quick health check to see if it's still working
                try:
                    import requests
                    health_response = requests.get(f"{existing_url}/health", timeout=5)
                    if health_response.status_code == 200:
                        print(f"✅ Backend already deployed and healthy at: {existing_url}")
                        self.backend_url = existing_url
                        return {"status": "success", "result": {"backend_url": self.backend_url, "already_deployed": True}}
                    else:
                        print(f"⚠️  Backend exists but not healthy (HTTP {health_response.status_code}), will redeploy...")
                except Exception as e:
                    print(f"⚠️  Backend exists but health check failed: {e}, will redeploy...")

            # Deploy backend to Modal.com - Call deployment function directly
            import subprocess
            import asyncio
            app_name = f"{self.project_id}"
            # Import the secret name generator
            from streaming_api import generate_modal_secret_name
            secret_name = generate_modal_secret_name(app_name)

            # Use backend deployment info as the source of truth
            # If backend info shows deployment exists, use redeployment mode
            is_redeployment = has_deployment_history
            if is_redeployment:
                print(f"✅ Backend deployment info confirms deployment exists - using redeployment mode")
            else:
                print(f"🆕 No deployment history found - deploying fresh backend")

            deploy_type = "Redeploying" if is_redeployment else "Deploying new"
            print(f"🔄 {deploy_type} {app_name} to Modal.com (redeployment={is_redeployment})...")

            # Import and call the Modal deployment function directly (no HTTP API call)
            try:
                from streaming_api import _execute_modal_deployment, ModalDeploymentRequest

                # Create deployment request with default secrets for new deployments
                secrets = {} if is_redeployment else None  # Let deployment function handle default secrets
                deployment_request = ModalDeploymentRequest(
                    project_id=self.project_id,
                    app_name=app_name,
                    app_title="AI Generated Backend",
                    app_description="Auto-generated FastAPI backend",
                    redeployment=is_redeployment,
                    database_name=f"{app_name}_database.db",
                    secrets=secrets
                )

                print(f"🚀 Calling deployment function directly...")

                # Call the deployment function directly using asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(_execute_modal_deployment(deployment_request))
                finally:
                    loop.close()

                print(f"✅ Direct deployment completed: {result.status}")

                if result.status == "success":
                    backend_url = result.url
                    stdout = result.stdout or ''
                    stderr = result.stderr or ''

                    print(f"✅ Backend deployed successfully!")
                    print(f"🔗 Backend URL: {backend_url}")

                    # Print STDOUT/STDERR for visibility
                    if stdout:
                        print(f"📤 DEPLOYMENT STDOUT:\n{stdout}")
                    if stderr:
                        print(f"📥 DEPLOYMENT STDERR:\n{stderr}")

                    # Update backend URL in state
                    self.backend_url = backend_url

                    # Update .env file with BACKEND_URL
                    try:
                        env_file_path = "backend/.env"
                        print(f"📝 Updating {env_file_path} with BACKEND_URL...")
                        
                        # Read existing .env content or create new
                        existing_env_content = ""
                        try:
                            existing_env_content = self.cloud_storage.download_file(self.project_id, env_file_path)
                            if existing_env_content is None:
                                existing_env_content = ""
                        except:
                            existing_env_content = ""
                        
                        # Parse existing content into lines
                        env_lines = existing_env_content.split('\n') if existing_env_content else []
                        
                        # Check if BACKEND_URL exists and update or add it
                        backend_url_found = False
                        for i, line in enumerate(env_lines):
                            if line.startswith('BACKEND_URL='):
                                env_lines[i] = f'BACKEND_URL={backend_url}'
                                backend_url_found = True
                                print(f"✅ Updated existing BACKEND_URL in .env")
                                break
                        
                        if not backend_url_found:
                            # Add BACKEND_URL if it doesn't exist
                            env_lines.append(f'BACKEND_URL={backend_url}')
                            print(f"✅ Added BACKEND_URL to .env")
                        
                        # Write back the updated .env content
                        updated_env_content = '\n'.join(env_lines)
                        self.cloud_storage.upload_file(self.project_id, env_file_path, updated_env_content)
                        print(f"✅ Successfully updated {env_file_path} with BACKEND_URL={backend_url}")
                        
                    except Exception as e:
                        print(f"⚠️ Warning: Could not update .env file with BACKEND_URL: {e}")
                        # Don't fail the deployment if .env update fails

                    # Update backend info in project metadata
                    if hasattr(self, 'project_id') and self.project_id:
                        try:
                            self._update_backend_deployment_info(backend_url, app_name)
                        except Exception as e:
                            print(f"⚠️  Warning: Could not save backend deployment info: {e}")

                    return {
                        "status": "success",
                        "result": {
                            "backend_url": backend_url,
                            "app_name": app_name,
                            "stdout": stdout,  # Include STDOUT in result
                            "stderr": stderr   # Include STDERR in result
                        }
                    }
                else:
                    error_msg = result.error or 'Unknown deployment error'
                    stdout = result.stdout or ''
                    stderr = result.stderr or ''

                    print(f"❌ Deployment failed: {error_msg}")

                    # Print STDOUT/STDERR for debugging
                    if stdout:
                        print(f"📤 DEPLOYMENT STDOUT:\n{stdout}")
                        error_msg += f"\nSTDOUT:\n{stdout}"
                    if stderr:
                        print(f"📥 DEPLOYMENT STDERR:\n{stderr}")
                        error_msg += f"\nSTDERR:\n{stderr}"

                    return {
                        "status": "error",
                        "error": error_msg,
                        "stdout": stdout,  # Include STDOUT in error response
                        "stderr": stderr   # Include STDERR in error response
                    }

            except ImportError as e:
                print(f"❌ Could not import deployment functions: {e}")
                return {"status": "error", "error": f"Could not import deployment functions: {e}"}
            except Exception as e:
                print(f"❌ Direct deployment failed: {e}")
                return {"status": "error", "error": f"Direct deployment failed: {e}"}

        except Exception as e:
            error_details = f"Exception: {str(e)}"
            print(f"❌ Error deploying backend: {error_details}")
            return {"status": "error", "error": error_details}

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

                return {"status": "success", "result": result}
            else:
                error_details = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Failed to start frontend: {error_details}")
                return {"status": "error", "error": error_details, "status_code": response.status_code}

        except Exception as e:
            error_details = f"Exception: {str(e)}"
            print(f"❌ Error starting frontend: {error_details}")
            return {"status": "error", "error": error_details}

    def _handle_restart_backend_interrupt(self, action: dict) -> dict:
        """Handle restart_backend action using Modal redeploy API"""
        print(f"🔄 Restarting backend service via Modal redeploy...")

        try:
            # Get backend deployment info to get current app name
            backend_info = self._get_backend_deployment_info()

            if backend_info['status'] != 'success':
                error_msg = backend_info['error']
                print(f"❌ {error_msg}")
                return {
                    "status": "error",
                    "error": f"{error_msg}. Deploy backend first before restarting."
                }

            app_name = backend_info['app_name']
            current_url = backend_info['url']

            print(f"🎯 Redeploying Modal app: {app_name}")
            print(f"📡 Current URL: {current_url}")

            import requests

            # Call the streaming API's Modal redeploy endpoint
            redeploy_url = "http://localhost:8084/modal/deploy"
            redeploy_data = {
                "project_id": self.project_id,
                "app_name": app_name,
                "redeployment": True  # This is a redeployment, not a new deployment
            }

            print(f"📤 Calling redeploy API: {redeploy_url}")

            # Use short timeout for starting redeploy
            response = requests.post(redeploy_url, json=redeploy_data, timeout=30)  # Short timeout for starting deployment

            if response.status_code == 200:
                result = response.json()

                if result.get('status') == 'started':
                    # New background deployment system
                    deployment_id = result.get('deployment_id')
                    status_url = f"http://localhost:8084/modal/deploy/status/{deployment_id}"

                    print(f"🔄 Modal redeployment started in background...")
                    print(f"📋 Deployment ID: {deployment_id}")

                    # Poll deployment status
                    import time
                    max_wait_time = 600  # 10 minutes total
                    start_time = time.time()
                    check_interval = 5

                    while time.time() - start_time < max_wait_time:
                        try:
                            status_response = requests.get(status_url, timeout=10)
                            if status_response.status_code == 200:
                                status_result = status_response.json()
                                deployment_status = status_result.get('status')
                                progress = status_result.get('progress', 'No progress info')

                                print(f"📊 Redeployment Status: {deployment_status} - {progress}")

                                if deployment_status == 'success':
                                    deployment_result = status_result.get('result', {})
                                    new_url = deployment_result.get('url')
                                    docs_url = deployment_result.get('docs_url')
                                    
                                    # Update .env file with BACKEND_URL
                                    try:
                                        env_file_path = "backend/.env"
                                        print(f"📝 Updating {env_file_path} with BACKEND_URL...")
                                        
                                        existing_env_content = ""
                                        try:
                                            existing_env_content = self.cloud_storage.download_file(self.project_id, env_file_path)
                                            if existing_env_content is None:
                                                existing_env_content = ""
                                        except:
                                            existing_env_content = ""
                                        
                                        env_lines = existing_env_content.split('\n') if existing_env_content else []
                                        
                                        backend_url_found = False
                                        for i, line in enumerate(env_lines):
                                            if line.startswith('BACKEND_URL='):
                                                env_lines[i] = f'BACKEND_URL={new_url}'
                                                backend_url_found = True
                                                print(f"✅ Updated existing BACKEND_URL in .env")
                                                break
                                        
                                        if not backend_url_found:
                                            env_lines.append(f'BACKEND_URL={new_url}')
                                            print(f"✅ Added BACKEND_URL to .env")
                                        
                                        updated_env_content = '\n'.join(env_lines)
                                        self.cloud_storage.upload_file(self.project_id, env_file_path, updated_env_content)
                                        print(f"✅ Successfully updated {env_file_path} with BACKEND_URL={new_url}")
                                        
                                    except Exception as e:
                                        print(f"⚠️ Warning: Could not update .env file with BACKEND_URL: {e}")
                                    
                                    break  # Exit polling loop

                                elif deployment_status == 'error':
                                    error_msg = status_result.get('error', 'Unknown redeployment error')
                                    print(f"❌ Modal redeployment failed: {error_msg}")
                                    return {"status": "error", "error": f"Modal redeployment failed: {error_msg}"}

                                time.sleep(check_interval)
                                check_interval = min(check_interval * 1.2, 30)
                            else:
                                print(f"⚠️ Status check failed: {status_response.status_code}")
                                time.sleep(5)
                        except requests.RequestException as e:
                            print(f"⚠️ Status check request failed: {e}")
                            time.sleep(5)
                    else:
                        return {"status": "error", "error": "Redeployment timeout: exceeded 10 minutes"}

                elif result.get('status') == 'success':
                    new_url = result.get('url')
                    docs_url = result.get('docs_url')
                    stdout = result.get('stdout', '')
                    stderr = result.get('stderr', '')

                    print(f"✅ Backend redeployed successfully!")
                    print(f"🔗 Backend URL: {new_url}")
                    print(f"📚 API Docs: {docs_url}")

                    # Print STDOUT/STDERR for visibility
                    if stdout:
                        print(f"📤 DEPLOYMENT STDOUT:\n{stdout}")
                    if stderr:
                        print(f"📥 DEPLOYMENT STDERR:\n{stderr}")

                    # Update backend URL in state
                    self.backend_url = new_url
                    
                    # Update .env file with BACKEND_URL
                    try:
                        env_file_path = "backend/.env"
                        print(f"📝 Updating {env_file_path} with BACKEND_URL...")
                        
                        existing_env_content = ""
                        try:
                            existing_env_content = self.cloud_storage.download_file(self.project_id, env_file_path)
                            if existing_env_content is None:
                                existing_env_content = ""
                        except:
                            existing_env_content = ""
                        
                        env_lines = existing_env_content.split('\n') if existing_env_content else []
                        
                        backend_url_found = False
                        for i, line in enumerate(env_lines):
                            if line.startswith('BACKEND_URL='):
                                env_lines[i] = f'BACKEND_URL={new_url}'
                                backend_url_found = True
                                print(f"✅ Updated existing BACKEND_URL in .env")
                                break
                        
                        if not backend_url_found:
                            env_lines.append(f'BACKEND_URL={new_url}')
                            print(f"✅ Added BACKEND_URL to .env")
                        
                        updated_env_content = '\n'.join(env_lines)
                        self.cloud_storage.upload_file(self.project_id, env_file_path, updated_env_content)
                        print(f"✅ Successfully updated {env_file_path} with BACKEND_URL={new_url}")
                        
                    except Exception as e:
                        print(f"⚠️ Warning: Could not update .env file with BACKEND_URL: {e}")

                    return {
                        "status": "success",
                        "result": {
                            "backend_url": new_url,
                            "docs_url": docs_url,
                            "app_name": app_name,
                            "redeployed": True,
                            "deployment_output": result.get('deployment_output', 'Backend redeployed successfully'),
                            "stdout": stdout,  # Include STDOUT in result
                            "stderr": stderr   # Include STDERR in result
                        }
                    }
                else:
                    error_msg = result.get('error', 'Unknown deployment error')
                    stdout = result.get('stdout', '')
                    stderr = result.get('stderr', '')

                    print(f"❌ Backend redeploy failed: {error_msg}")

                    # Print STDOUT/STDERR for debugging
                    if stdout:
                        print(f"📤 DEPLOYMENT STDOUT:\n{stdout}")
                    if stderr:
                        print(f"📥 DEPLOYMENT STDERR:\n{stderr}")

                    return {
                        "status": "error",
                        "error": f"Modal redeploy failed: {error_msg}",
                        "stdout": stdout,  # Include STDOUT in error response
                        "stderr": stderr   # Include STDERR in error response
                    }
            else:
                error_details = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Redeploy API call failed: {error_details}")
                return {
                    "status": "error",
                    "error": f"Redeploy API call failed: {error_details}"
                }

        except requests.exceptions.Timeout:
            error_msg = "Backend redeploy timed out (>3 minutes)"
            print(f"❌ {error_msg}")
            return {"status": "error", "error": error_msg}
        except Exception as e:
            error_details = f"Exception during backend restart: {str(e)}"
            print(f"❌ {error_details}")
            return {"status": "error", "error": error_details}

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

                return {"status": "success", "result": result}
            else:
                error_details = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Failed to restart frontend: {error_details}")
                return {"status": "error", "error": error_details, "status_code": response.status_code}

        except Exception as e:
            error_details = f"Exception: {str(e)}"
            print(f"❌ Error restarting frontend: {error_details}")
            return {"status": "error", "error": error_details}

    def _handle_web_search_interrupt(self, action: dict) -> dict:
        """Handle web search action with Exa AI API"""
        try:
            from openai import OpenAI

            # Extract query from action
            query = action.get('query') or action.get('content', '')
            if not query:
                return {
                    'success': False,
                    'error': 'No search query provided',
                    'query': '',
                    'results': ''
                }

            print(f"🔍 Searching web for: {query}")

            # Initialize Exa AI client
            client = OpenAI(
                base_url="https://api.exa.ai",
                api_key="16fe8779-7264-44c1-a911-e8187cb629c6"
            )

            # Make the search request
            completion = client.chat.completions.create(
                model="exa",
                messages=[{"role": "user", "content": query}]
            )

            # Extract the response
            search_results = completion.choices[0].message.content if completion.choices else "No results found"

            print(f"✅ Web search completed successfully")
            print(f"📊 Results length: {len(search_results)} characters")

            return {
                'success': True,
                'query': query,
                'results': search_results,
                'source': 'exa_ai'
            }

        except ImportError:
            print("❌ OpenAI package not available for web search")
            return {
                'success': False,
                'error': 'OpenAI package not installed',
                'query': query if 'query' in locals() else '',
                'results': ''
            }
        except Exception as e:
            print(f"❌ Web search failed: {str(e)}")
            return {
                'success': False,
                'error': f"Search failed: {str(e)}",
                'query': query if 'query' in locals() else '',
                'results': ''
            }

    def _handle_attempt_completion_interrupt(self, action: dict, accumulated_content: str) -> dict:
        """Handle attempt_completion action - ends the session with completion message

        Handles multiple formats:
        1. <action type="attempt_completion">content</action>
        2. Plain text "attempt_completion"
        3. Other variations in action structure
        """
        print(f"🎯 Processing attempt completion...")

        try:
            completion_message = ""

            # Method 1: Extract from action content directly
            if action.get('content'):
                completion_message = action.get('content', '')
                print(f"📄 Method 1 - Found content in action: {len(completion_message)} chars")

            # Method 2: Extract from action text (for different parser results)
            if not completion_message and action.get('text'):
                completion_message = action.get('text', '')
                print(f"📄 Method 2 - Found text in action: {len(completion_message)} chars")

            # Method 3: Extract from raw XML action tag in accumulated content
            if not completion_message and accumulated_content:
                import re
                # Look for <action type="attempt_completion">content</action>
                action_match = re.search(r'<action[^>]*type="attempt_completion"[^>]*>(.*?)</action>', accumulated_content, re.DOTALL | re.IGNORECASE)
                if action_match:
                    completion_message = action_match.group(1)
                    print(f"📄 Method 3 - Extracted from XML action tag: {len(completion_message)} chars")

                # Look for other attempt_completion patterns in content
                elif 'attempt_completion' in accumulated_content.lower():
                    # Try to extract content after attempt_completion markers
                    lines = accumulated_content.split('\n')
                    capture_content = False
                    captured_lines = []

                    for line in lines:
                        line_lower = line.lower()
                        if 'attempt_completion' in line_lower:
                            capture_content = True
                            # Skip the line with the marker itself unless it has substantial content
                            if len(line.strip()) > len('attempt_completion') + 20:  # Has more than just the marker
                                captured_lines.append(line.strip())
                        elif capture_content:
                            # Stop capturing if we hit another action or XML tag
                            if line.strip().startswith('<') or 'type=' in line:
                                break
                            if line.strip():  # Non-empty line
                                captured_lines.append(line.strip())

                    if captured_lines:
                        completion_message = '\n'.join(captured_lines)
                        print(f"📄 Method 4 - Extracted from content patterns: {len(completion_message)} chars")

            # Method 5: Extract from different action formats that parsers might create
            if not completion_message:
                # Check for nested content in action details
                details = action.get('action_details', {}) or action.get('actionDetails', {})
                if details and isinstance(details, dict):
                    completion_message = details.get('content', '') or details.get('message', '')
                    if completion_message:
                        print(f"📄 Method 5 - Found in action details: {len(completion_message)} chars")

            # Method 6: Look for completion message in action raw attributes
            if not completion_message:
                raw_attrs = action.get('raw_attrs', {})
                if raw_attrs and isinstance(raw_attrs, dict):
                    completion_message = raw_attrs.get('content', '') or raw_attrs.get('message', '')
                    if completion_message:
                        print(f"📄 Method 6 - Found in raw attributes: {len(completion_message)} chars")

            # Parse suggest_next_tasks if present and clean up the completion message
            suggest_next_tasks = None
            if completion_message and '<suggest_next_tasks>' in completion_message:
                print(f"🎯 Found suggest_next_tasks in completion message - parsing")

                # Extract suggest_next_tasks content
                import re
                suggest_match = re.search(r'<suggest_next_tasks>(.*?)</suggest_next_tasks>', completion_message, re.DOTALL)
                if suggest_match:
                    suggest_content = suggest_match.group(1)
                    print(f"📋 Extracted suggest_next_tasks content ({len(suggest_content)} chars)")

                    # Parse individual suggestions
                    suggestions = []
                    suggestion_matches = re.findall(r'<suggestion\s+for="([^"]*)"(?:\s+goto="([^"]*)")?[^>]*>(.*?)</suggestion>', suggest_content, re.DOTALL)

                    for match in suggestion_matches:
                        for_attr, goto_attr, content = match
                        suggestion = {
                            "for": for_attr.strip(),
                            "content": content.strip()
                        }
                        if goto_attr:
                            suggestion["goto"] = goto_attr.strip()

                        suggestions.append(suggestion)
                        print(f"📌 Parsed suggestion - for: {for_attr}, goto: {goto_attr or 'none'}, content: {content.strip()[:50]}...")

                    if suggestions:
                        suggest_next_tasks = suggestions
                        print(f"✅ Successfully parsed {len(suggestions)} suggestions")

                # Remove suggest_next_tasks from completion message
                completion_message = re.sub(r'<suggest_next_tasks>.*?</suggest_next_tasks>', '', completion_message, flags=re.DOTALL)

            # Clean up the completion message
            if completion_message:
                # Remove any remaining XML tags
                completion_message = re.sub(r'<[^>]+>', '', completion_message)

            # Fallback to default message
            if not completion_message:
                completion_message = "Task completed successfully."
                print(f"📄 Using fallback completion message")

            print(f"📝 Final completion message ({len(completion_message)} chars): {completion_message[:100]}...")

            # Create completion result
            result = {
                'success': True,
                'message': completion_message,
                'session_ended': True,
                'timestamp': datetime.now().isoformat()
            }

            # Add suggest_next_tasks if parsed
            if suggest_next_tasks:
                result['suggest_next_tasks'] = suggest_next_tasks
                print(f"📤 Including suggest_next_tasks with {len(suggest_next_tasks)} suggestions in result")

            print(f"✅ Attempt completion processed successfully")
            return result

        except Exception as e:
            print(f"❌ Error processing attempt completion: {e}")
            return {
                'success': False,
                'error': f"Failed to process completion: {str(e)}",
                'message': 'Task completion failed',
                'session_ended': False
            }

    def _handle_ast_analyze_interrupt(self, action: dict) -> dict:
        """Handle AST analysis action during interrupt by calling the API"""
        print(f"🧠 Running AST analysis via API...")

        try:
            target = action.get('target', 'backend')  # backend or frontend
            focus = action.get('focus', 'all')  # routes, imports, env, database, structure, all

            print(f"🎯 Target: {target}, Focus: {focus}")

            # Call the AST analysis API endpoint instead of accessing files directly
            import requests

            api_url = f"{self.api_base_url}/projects/{self.project_id}/ast-analyze"
            params = {
                'target': target,
                'focus': focus
            }

            print(f"📝 Calling AST API: {api_url}")
            print(f"📝 Parameters: {params}")

            response = requests.post(
                api_url,
                params=params,
                timeout=35  # Slightly longer than the API timeout
            )

            if response.status_code == 200:
                analysis_result = response.json()
                if analysis_result.get('success', False):
                    print(f"✅ AST analysis completed successfully via API")
                    files_analyzed = analysis_result.get('summary', {}).get('files_analyzed', 0)
                    print(f"📊 Analyzed {files_analyzed} files")
                    return analysis_result
                else:
                    print(f"❌ AST analysis API returned error: {analysis_result.get('error', 'Unknown error')}")
                    return analysis_result
            else:
                print(f"❌ AST analysis API failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}: {error_data.get('detail', 'Unknown error')}",
                        "status_code": response.status_code
                    }
                except:
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}: {response.text[:200]}",
                        "status_code": response.status_code
                    }

        except requests.Timeout:
            print(f"❌ AST analysis API timed out")
            return {
                "success": False,
                "error": "AST analysis API timed out after 35 seconds"
            }
        except requests.RequestException as e:
            print(f"❌ AST analysis API request failed: {e}")
            return {
                "success": False,
                "error": f"API request failed: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error calling AST analysis API: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"AST analysis error: {str(e)}"
            }

    def _get_todo_file_path(self):
        """Todo system integrated with cloud storage - no local files needed"""
        return None

    def _load_todos(self):
        """Load todos from project metadata in cloud storage"""
        try:
            if not self.project_id or not self.cloud_storage:
                return []

            project_metadata = self.cloud_storage.load_project_metadata(self.project_id)
            if not project_metadata:
                return []

            todos = project_metadata.get('todos', [])
            if todos:
                print(f"📋 Loaded {len(todos)} todos from cloud storage")
            return todos

        except Exception as e:
            print(f"❌ Error loading todos from cloud storage: {e}")
            return []

    def _save_todos(self, todos):
        """Save todos to project metadata in cloud storage"""
        try:
            if not self.project_id or not self.cloud_storage:
                print("⚠️ Cannot save todos - no project_id or cloud_storage available")
                return

            # Load existing metadata
            project_metadata = self.cloud_storage.load_project_metadata(self.project_id) or {}

            # Update todos
            project_metadata['todos'] = todos
            project_metadata['todos_last_updated'] = datetime.now().isoformat()

            # Save updated metadata in background
            future = self._save_metadata_background(project_metadata)
            success = True  # Assume success since it's background

            if success:
                print(f"✅ Saved {len(todos)} todos to cloud storage")
            else:
                print(f"❌ Failed to save todos to cloud storage")

        except Exception as e:
            print(f"❌ Error saving todos to cloud storage: {e}")

    def _ensure_todos_loaded(self):
        """Ensure todos are loaded from persistent storage"""
        self.todos = self._load_todos()

    def _clean_duplicate_todos(self):
        """Clean up duplicate todos by content and ID"""
        if not self.todos:
            return

        print("🧹 Cleaning duplicate todos...")
        original_count = len(self.todos)

        # Track seen todos by normalized content
        seen_content = {}
        seen_ids = set()
        cleaned_todos = []

        for todo in self.todos:
            todo_id = todo.get('id', '')
            description = todo.get('description', '').strip()

            # Normalize description for comparison (remove extra whitespace, case insensitive)
            normalized_desc = ' '.join(description.lower().split())

            # Check for duplicate ID
            if todo_id in seen_ids:
                print(f"📋 Removing duplicate ID: {todo_id}")
                continue

            # Check for duplicate content
            if normalized_desc in seen_content:
                existing_todo = seen_content[normalized_desc]
                # Keep the one with higher priority or more recent
                if todo.get('status') == 'completed' and existing_todo.get('status') != 'completed':
                    # Keep completed version, remove the existing incomplete one
                    cleaned_todos = [t for t in cleaned_todos if t['id'] != existing_todo['id']]
                    cleaned_todos.append(todo)
                    seen_content[normalized_desc] = todo
                    seen_ids.add(todo_id)
                    print(f"📋 Replaced incomplete with completed: {todo_id}")
                elif existing_todo.get('status') == 'completed' and todo.get('status') != 'completed':
                    # Keep existing completed version, skip this one
                    print(f"📋 Skipping incomplete duplicate: {todo_id}")
                    continue
                else:
                    # Keep the first one encountered
                    print(f"📋 Removing content duplicate: {todo_id}")
                    continue
            else:
                # New unique todo
                cleaned_todos.append(todo)
                seen_content[normalized_desc] = todo
                seen_ids.add(todo_id)

        self.todos = cleaned_todos

        if original_count != len(self.todos):
            print(f"🧹 Cleaned {original_count - len(self.todos)} duplicate todos ({original_count} → {len(self.todos)})")
            self._save_todos(self.todos)
        else:
            print("🧹 No duplicates found")

    def _handle_todo_actions(self, action: dict):
        """Handle todo-related actions"""
        action_type = action.get('type')

        # Ensure todos are loaded from file
        self._ensure_todos_loaded()

        # Clean duplicates before processing new actions
        self._clean_duplicate_todos()

        if action_type == 'todo_create':
            # Get attributes from raw_attrs if available
            attrs = action.get('raw_attrs', {})
            todo_id = attrs.get('id') or action.get('id')
            todo_description = action.get('content', '').strip()

            # Normalize description for comparison
            normalized_desc = ' '.join(todo_description.lower().split())

            # Check for duplicates by ID or normalized content
            existing_todo = None
            for existing in self.todos:
                if existing['id'] == todo_id:
                    existing_todo = existing
                    print(f"📋 Duplicate todo by ID detected: {todo_id}")
                    break
                elif ' '.join(existing['description'].lower().split()) == normalized_desc:
                    existing_todo = existing
                    print(f"📋 Duplicate todo by content detected: {todo_description[:50]}...")
                    break

            if existing_todo:
                print(f"📋 Skipping duplicate todo creation: {todo_id}")
                return

            todo = {
                'id': todo_id,
                'description': todo_description,
                'priority': attrs.get('priority', 'medium'),
                'integration': attrs.get('integration', 'false') == 'true',
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            self.todos.append(todo)
            self._save_todos(self.todos)
            print(f"📋 Created todo: {todo['id']} - {todo['description']}")

        elif action_type == 'todo_update':
            attrs = action.get('raw_attrs', {})
            todo_id = attrs.get('id') or action.get('id')
            new_status = attrs.get('status') or action.get('status')

            for i, todo in enumerate(self.todos):
                if todo['id'] == todo_id:
                    old_status = todo['status']
                    self.todos[i]['status'] = new_status
                    self._save_todos(self.todos)
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

            for i, todo in enumerate(self.todos):
                if todo['id'] == todo_id:
                    self.todos[i]['status'] = 'completed'
                    self.todos[i]['integration_tested'] = integration_tested
                    self.todos[i]['completed_at'] = datetime.now().isoformat()
                    self._save_todos(self.todos)

                    if integration_tested:
                        print(f"✅ Completed todo: {todo_id}")
                        print(f"   🔗 Integration tested: Yes")
                    else:
                        print(f"✅ Completed todo: {todo_id}")
                        print(f"   🔗 Integration tested: No")
                    break

    def _display_todos(self):
        """Display current todo status and return structured todo list"""
        # Ensure todos are loaded from file
        self._ensure_todos_loaded()

        # Clean duplicates every time we display todos
        self._clean_duplicate_todos()

        if not self.todos:
            todo_tree = "📋 todos/\n└── (no todos created yet)"
            print("📋 No todos created yet")
            return todo_tree

        # Build structured todo tree
        todo_tree = "📋 todos/\n"

        # Group todos by status
        completed = [t for t in self.todos if t['status'] == 'completed']
        in_progress = [t for t in self.todos if t['status'] == 'in_progress']
        pending = [t for t in self.todos if t['status'] == 'pending']

        # Always show completed todos section
        todo_tree += f"├── ✅ completed/ ({len(completed)} items)\n"
        if completed:
            for i, todo in enumerate(completed):
                is_last = i == len(completed) - 1
                integration_icon = "🔗" if todo.get('integration_tested') else "📝"
                connector = "└──" if is_last else "├──"
                # Clean description - remove newlines and limit length
                clean_desc = todo['description'].replace('\n', ' ').replace('\r', ' ').strip()
                if len(clean_desc) > 80:
                    clean_desc = clean_desc[:77] + "..."
                todo_tree += f"│   {connector} {integration_icon} {todo['id']} - {clean_desc}\n"
        else:
            todo_tree += f"│   └── (no completed todos yet)\n"

        # Always show in progress todos section
        todo_tree += f"├── 🔄 in_progress/ ({len(in_progress)} items)\n"
        if in_progress:
            for i, todo in enumerate(in_progress):
                is_last = i == len(in_progress) - 1
                priority_icon = "🔥" if todo.get('priority') == 'high' else "⚡" if todo.get('priority') == 'medium' else "📌"
                connector = "└──" if is_last else "├──"
                # Clean description - remove newlines and limit length
                clean_desc = todo['description'].replace('\n', ' ').replace('\r', ' ').strip()
                if len(clean_desc) > 80:
                    clean_desc = clean_desc[:77] + "..."
                todo_tree += f"│   {connector} {priority_icon} {todo['id']} - {clean_desc}\n"
        else:
            todo_tree += f"│   └── (no todos in progress)\n"

        # Always show pending todos section
        todo_tree += f"└── ⏳ pending/ ({len(pending)} items)\n"
        if pending:
            for i, todo in enumerate(pending):
                is_last = i == len(pending) - 1
                priority_icon = "🔥" if todo.get('priority') == 'high' else "⚡" if todo.get('priority') == 'medium' else "📌"
                connector = "└──" if is_last else "├──"
                indent = "    " if is_last else "│   "
                # Clean description - remove newlines and limit length
                clean_desc = todo['description'].replace('\n', ' ').replace('\r', ' ').strip()
                if len(clean_desc) > 80:
                    clean_desc = clean_desc[:77] + "..."
                todo_tree += f"{indent}{connector} {priority_icon} {todo['id']} - {clean_desc}\n"
        else:
            todo_tree += f"    └── (no pending todos)\n"

        # Print the tree structure
        print("\n📋 CURRENT TODO STATUS:")
        print("=" * 50)
        print(todo_tree.rstrip())
        print("=" * 50)

        return todo_tree.rstrip()

    def _has_incomplete_todos(self):
        """Check if there are any incomplete todos (pending or in_progress)"""
        self._ensure_todos_loaded()

        if not self.todos:
            return False

        incomplete_todos = [t for t in self.todos if t['status'] in ['pending', 'in_progress']]

        print(f"📋 Checking for incomplete todos: {len(incomplete_todos)} found")
        for todo in incomplete_todos:
            print(f"   - {todo['status']}: {todo['id']} - {todo['description'][:50]}...")

        return len(incomplete_todos) > 0

    def _get_incomplete_todos_message(self):
        """Get a detailed message about incomplete todos"""
        self._ensure_todos_loaded()

        if not self.todos:
            return ""

        incomplete_todos = [t for t in self.todos if t['status'] in ['pending', 'in_progress']]

        if not incomplete_todos:
            return ""

        message = f"\n🚨 **WARNING: {len(incomplete_todos)} incomplete todos found!**\n\n"
        message += "The model attempted to complete the conversation, but there are still pending tasks:\n\n"

        for todo in incomplete_todos:
            status_icon = "🔄" if todo['status'] == 'in_progress' else "⏳"
            priority_icon = "🔥" if todo.get('priority') == 'high' else "⚡" if todo.get('priority') == 'medium' else "📌"
            clean_desc = todo['description'].replace('\n', ' ').replace('\r', ' ').strip()
            message += f"{status_icon} {priority_icon} **{todo['id']}** ({todo['status']}): {clean_desc}\n"

        message += "\n**The model needs to:**\n"
        message += "1. Complete all remaining todos by implementing the required functionality\n"
        message += "2. Update each todo status to 'completed' using todo_update\n"
        message += "3. Verify the implementation works by reading/testing the files\n"
        message += "4. Only then use attempt_completion to end the conversation\n\n"
        message += "**Continuing the conversation to complete these tasks...**\n"

        return message

    def _handle_integration_docs_interrupt(self, action: dict) -> dict:
        """Handle integration_docs interrupt by using ToolsManager"""
        print(f"📚 Integration docs interrupt triggered")
        if not self.tools_manager:
            print("❌ ToolsManager not available")
            return {"status": "error", "message": "ToolsManager not initialized"}

        return self.tools_manager.handle_integration_docs(action)

    def _handle_list_files_interrupt(self, action: dict) -> dict:
        """Handle list_files interrupt by using ToolsManager"""
        print(f"📁 List files interrupt triggered")
        if not self.tools_manager:
            print("❌ ToolsManager not available")
            return {"status": "error", "message": "ToolsManager not initialized"}

        return self.tools_manager.handle_list_files(action)

    def _handle_parallel_interrupt(self, action: dict) -> dict:
        """Handle parallel tool execution using dedicated handler"""
        print(f"⚡ Parallel tool interrupt triggered")

        # Lazy import and initialize parallel tool handler
        if not hasattr(self, '_parallel_handler'):
            try:
                from tools.parallel_tools import ParallelToolHandler
                self._parallel_handler = ParallelToolHandler(self)
                print("✅ Parallel tool handler initialized")
            except ImportError as e:
                print(f"❌ Failed to import parallel tool handler: {e}")
                return {"status": "error", "message": "Parallel tool handler not available"}

        return self._parallel_handler.handle_parallel_execution(action)

    def _handle_add_starter_kit_interrupt(self, action: dict) -> dict:
        """Handle add_starter_kit action during interrupt"""
        print(f"🛠️ Adding starter kit interrupt triggered")
        
        # Check raw_attrs first for the actual kit value
        raw_attrs = action.get('raw_attrs', {})
        kit_name = raw_attrs.get('kit') or action.get('kit')
        target = raw_attrs.get('target') or action.get('target')  # optional: backend or frontend
        
        if not kit_name:
            return {
                "success": False,
                "error": "No kit name provided. Use kit='stripe' to add a starter kit",
                "action_type": "add_starter_kit"
            }
        
        try:
            # Lazy import and initialize starter kit manager
            if not hasattr(self, '_starter_kit_manager'):
                try:
                    from starter_kits import get_starter_kit_manager
                    self._starter_kit_manager = get_starter_kit_manager(self.cloud_storage)
                    print("✅ Starter kit manager initialized")
                except ImportError as e:
                    print(f"❌ Failed to import starter kit manager: {e}")
                    return {
                        "success": False,
                        "error": "Starter kit manager not available",
                        "action_type": "add_starter_kit"
                    }
            
            # Add the starter kit
            result = self._starter_kit_manager.add_starter_kit(
                project_id=self.project_id,
                kit_name=kit_name,
                target=target
            )
            
            # Add action_type for consistency
            result["action_type"] = "add_starter_kit"
            
            if result.get("success"):
                print(f"🎉 Starter kit '{kit_name}' added successfully!")
            else:
                print(f"❌ Failed to add starter kit '{kit_name}': {result.get('error')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Exception in add_starter_kit: {e}")
            return {
                "success": False,
                "error": f"Exception while adding starter kit: {str(e)}",
                "action_type": "add_starter_kit"
            }

    def _run_cloud_operation_background(self, operation_name: str, operation_func, *args, **kwargs):
        """Run cloud operation in background thread"""
        def _execute():
            try:
                with self._cloud_lock:
                    self.cloud_tasks_active += 1

                print(f"🌥️ Background: {operation_name}")
                result = operation_func(*args, **kwargs)
                print(f"✅ Background: {operation_name} completed")
                return result
            except Exception as e:
                print(f"❌ Background: {operation_name} failed: {e}")
                return None
            finally:
                with self._cloud_lock:
                    self.cloud_tasks_active -= 1

        # Submit to thread pool but don't wait for result
        future = self.cloud_executor.submit(_execute)
        return future

    def _save_conversation_background(self):
        """Save conversation history in background with automatic token tracking"""
        if not self.cloud_storage:
            return
        
        # Check if the last message is a new assistant message (for output token tracking)
        if (self.conversation_history and 
            len(self.conversation_history) > 0 and
            self.conversation_history[-1].get('role') == 'assistant' and
            hasattr(self, '_last_tracked_message_count')):
            
            # If we have more messages than before, the last one is new
            current_message_count = len(self.conversation_history)
            if current_message_count > getattr(self, '_last_tracked_message_count', 0):
                last_message = self.conversation_history[-1]
                assistant_content = last_message.get('content', '')
                
                if assistant_content:
                    print(f"📊 Auto-tracking output tokens for new assistant message ({len(assistant_content)} chars)...")
                    self._update_manual_token_usage(output_message=assistant_content)
                
                # Update the tracked message count
                self._last_tracked_message_count = current_message_count

        return self._run_cloud_operation_background(
            "Save conversation history",
            self.cloud_storage.save_conversation_history,
            self.project_id,
            self.conversation_history.copy()  # Make a copy to avoid race conditions
        )

    def _save_metadata_background(self, metadata_dict):
        """Save project metadata in background"""
        if not self.cloud_storage:
            return

        return self._run_cloud_operation_background(
            "Save project metadata",
            self.cloud_storage.save_project_metadata,
            self.project_id,
            metadata_dict.copy()  # Make a copy to avoid race conditions
        )

    def cleanup(self):
        """Clean up background tasks and thread pools"""
        if hasattr(self, 'cloud_executor'):
            print(f"🧹 Waiting for {self.cloud_tasks_active} background cloud operations to complete...")
            self.cloud_executor.shutdown(wait=True, timeout=10.0)
            print("✅ Background cloud operations cleaned up")
            
        if hasattr(self, 'model_executor'):
            print("🧹 Shutting down model operations thread pool...")
            self.model_executor.shutdown(wait=True, timeout=30.0)
            print("✅ Model operations thread pool cleaned up")

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

    print('====')
    print('Using raw user message directly')
    print('====')
    print(args.message)
    print('=========')

    # Determine mode and prepare message
    if args.project_id and args.message:
        # UPDATE MODE
        print("🐛 DEBUG: Entering update mode")
        print("🔄 Starting Project Update Mode")
        print("=" * 60)
        print(f"📋 Project ID: {args.project_id}")
        print(f"💬 Update Request: {args.message}")

        # Initialize system for existing project
        system = BoilerplatePersistentGroq(
            api_key='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',
            project_id=args.project_id
        )

        # user_request = args.message
        user_request = planned_user_message
        mode = "update"

    else:
        # CREATION MODE (default behavior)
        print("🚀 Starting Enhanced Groq Persistent Conversation System")
        print("=" * 60)

        # Use provided message or demo request
        if args.message:
            # user_request = args.message
            user_request = planned_user_message
        else:
            # Demo request for testing
            user_request = "build me a todo app"

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

        # Phase 2.5: Setup project environment (venv, packages) but DON'T start services
        print("🔧 Phase 2.5: Setting up project environment (venv, packages)...")
        setup_success = system.setup_project_environment()
        if setup_success:
            print("✅ Project environment setup completed")
            print("ℹ️  Services will start only when model uses action tags like <action type='start_backend'/>")
        else:
            print("⚠️ Warning: Environment setup had issues, but continuing with generation")



        mode = "creation"

    # Process the request using the same method for both modes
    print(f"\n{'='*60}")
    print(f"🔄 PROCESSING {mode.upper()} REQUEST")
    print("="*60)
    print(f"📝 {user_request}")
    print(f"\n{'='*50}")

    # Send the message with interrupt support (works for both creation and update)
    system._process_update_request_with_interrupts(user_request)

    # Save updated conversation history
    system._save_conversation_history()

    print(f"\n✅ {mode.upper()} COMPLETED!")
    print(f"🔄 Project processed successfully")

    print('Project done ✅')

if __name__ == "__main__":
    main()
