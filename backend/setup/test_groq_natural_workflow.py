#!/usr/local/bin/python3.13
"""
Natural Workflow Groq System - Todo-Driven Development
- Direct model calls without manual planning steps
- Model naturally creates and manages todos
- Focus on MUP (Minimum Usable Product) delivery
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
from shared_models import GroqAgentState, StreamingXMLParser
from openai import OpenAI

# Import existing interrupt handlers from test_groq_local
from test_groq_local import GroqAgent

from coder.prompts import generate_error_check_prompt, _build_summary_prompt
from coder.index import coder

from workflow_prompt import NATURAL_WORKFLOW_PROMPT



# Updated Senior Engineer Prompt with Natural Todo Workflow

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
    timestamp = datetime.now().strftime("%m%d-%H%M")
    
    # Join with dashes
    if key_words:
        project_name = '-'.join(key_words) + f'-{timestamp}'
    else:
        project_name = f'project-{timestamp}'
    
    return project_name

class NaturalWorkflowGroq(GroqAgent):
    """
    Natural workflow system - model creates and manages todos automatically
    """
    
    def __init__(self, api_key: str = None, project_name: str = None, api_base_url: str = "http://localhost:8000", project_id: str = None):
        # Initialize parent GroqAgent (pass api_base_url without /api suffix)
        super().__init__(api_key or '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', api_base_url)
        
        # Override with natural workflow specific settings
        self.project_id = project_id or generate_project_name(project_name or "natural-workflow")
        self.project_name = project_name or "Natural Workflow Project"
        
        # Update state
        self.state.project_id = self.project_id
        self.state.project_name = self.project_name
        
        # Todo management  
        self.todos = []
        
        # Create project
        self._create_project()
        
        print(f"🧠 Natural Workflow System Initialized")
        print(f"📋 Project: {self.project_name} ({self.project_id})")
        print(f"🎯 Ready for todo-driven development")

    def _create_project(self):
        """Create project using API"""
        try:
            url = f"{self.api_base_url}/projects"
            response = requests.post(url, json={
                "project_id": self.project_id,
                "files": {}
            }, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Project created: {self.project_id}")
            else:
                print(f"❌ Failed to create project: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error creating project: {e}")

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
                    break
                    
        elif action_type == 'todo_complete':
            attrs = action.get('raw_attrs', {})
            todo_id = attrs.get('id') or action.get('id')
            integration_tested = attrs.get('integration_tested', 'false') == 'true'
            
            for todo in self.todos:
                if todo['id'] == todo_id:
                    todo['status'] = 'completed'
                    todo['integration_tested'] = integration_tested
                    print(f"✅ Completed todo: {todo_id}")
                    if integration_tested:
                        print(f"   🔗 Integration tested: Yes")
                    break
                    
        elif action_type == 'todo_list':
            return self._display_todos()

    def _display_todos(self):
        """Display current todo status"""
        print(f"\n📋 CURRENT TODO STATUS:")
        print(f"=" * 50)
        
        if not self.todos:
            print("No todos created yet")
            return "No todos created yet"
            
        pending = [t for t in self.todos if t['status'] == 'pending']
        in_progress = [t for t in self.todos if t['status'] == 'in_progress']
        completed = [t for t in self.todos if t['status'] == 'completed']
        blocked = [t for t in self.todos if t['status'] == 'blocked']
        
        todo_list = []
        
        if in_progress:
            print(f"🔄 IN PROGRESS:")
            todo_list.append("🔄 IN PROGRESS:")
            for todo in in_progress:
                line = f"   • {todo['id']}: {todo['description']}"
                print(line)
                todo_list.append(f"   • {todo['id']}: {todo['description']} (Priority: {todo['priority']}, Integration: {'Yes' if todo['integration'] else 'No'})")
                
        if pending:
            print(f"⏳ PENDING ({len(pending)}):")
            todo_list.append(f"⏳ PENDING ({len(pending)}):")
            for todo in pending:
                priority_icon = "🔥" if todo['priority'] == 'high' else "📋"
                integration_icon = "🔗" if todo['integration'] else "⚙️"
                line = f"   {priority_icon} {integration_icon} {todo['id']}: {todo['description']}"
                print(line)
                todo_list.append(f"   {priority_icon} {integration_icon} {todo['id']}: {todo['description']} (Priority: {todo['priority']}, Integration: {'Yes' if todo['integration'] else 'No'})")
                
        if completed:
            print(f"✅ COMPLETED ({len(completed)}):")
            todo_list.append(f"✅ COMPLETED ({len(completed)}):")
            for todo in completed:
                integration_status = "🔗✅" if todo.get('integration_tested', False) else "⚙️✅"
                line = f"   {integration_status} {todo['id']}"
                print(line)
                todo_list.append(f"   {integration_status} {todo['id']}: {todo['description']} (Priority: {todo['priority']}, Integration Tested: {'Yes' if todo.get('integration_tested', False) else 'No'})")
                
        if blocked:
            print(f"⚠️ BLOCKED ({len(blocked)}):")
            todo_list.append(f"⚠️ BLOCKED ({len(blocked)}):")
            for todo in blocked:
                line = f"   • {todo['id']}: {todo['description']}"
                print(line)
                todo_list.append(f"   • {todo['id']}: {todo['description']} (Priority: {todo['priority']}, Integration: {'Yes' if todo['integration'] else 'No'})")
        
        print(f"=" * 50)
        
        return "\n".join(todo_list)

    def process_request(self, user_request: str):
        """Process user request with natural todo workflow"""
        print(f"\n🎯 PROCESSING REQUEST: {user_request}")
        print("=" * 60)
        
        # Add to conversation history
        self.state.conversation_history.append({
            'role': 'user',
            'content': user_request
        })
        
        # Build context with project files and todo status
        context = self._build_context()
        
        # Create prompt with natural workflow
        prompt = f"""
{NATURAL_WORKFLOW_PROMPT}

## CURRENT PROJECT CONTEXT

{context}

## USER REQUEST
{user_request}

## YOUR NATURAL RESPONSE

You naturally analyze this request and create todos for what needs to be built. Start by creating todos for the core workflows the user needs to accomplish, then begin implementing the highest priority todo.

Remember: This is how your mind naturally works - break down the problem, create todos, work systematically, track progress.
"""

        # Stream response with real interrupt handling
        print(f"🧠 Model thinking and creating natural workflow...")
        
        # Convert to messages format for coder-style processing
        messages = [{"role": "user", "content": prompt}]
        
        response = self._stream_with_real_interrupts(messages)
        
        print(f"\n")
        
        # Add to conversation history
        self.state.conversation_history.append({
            'role': 'assistant', 
            'content': response
        })
        
        # Update state (skip last_response as it's not in the model)

    def _build_context(self) -> str:
        """Build context string with project files and todo status"""
        context = f"Project: {self.project_name} ({self.project_id})\n\n"
        
        # Add todo status
        if self.todos:
            context += "📋 CURRENT TODOS:\n"
            for todo in self.todos:
                status_icon = {
                    'pending': '⏳',
                    'in_progress': '🔄', 
                    'completed': '✅',
                    'blocked': '⚠️'
                }.get(todo['status'], '📋')
                
                priority_icon = "🔥" if todo['priority'] == 'high' else "📋"
                integration_icon = "🔗" if todo['integration'] else "⚙️"
                
                context += f"{status_icon} {priority_icon} {integration_icon} {todo['id']}: {todo['description']}\n"
            context += "\n"
        
        # Add current project files
        if self.state.project_files:
            context += "📂 CURRENT FILES:\n"
            for file_path in sorted(self.state.project_files.keys()):
                context += f"   {file_path}\n"
            context += "\n"
        
        return context

    def _simple_stream_completion(self, prompt: str) -> str:
        """Simple streaming without complex interrupts"""
        try:
            # Convert prompt to messages format
            messages = [{"role": "user", "content": prompt}]
            
            # Create streaming response  
            stream = self.client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",
                messages=messages,
                stream=True,
                temperature=0.1,
                max_tokens=4000
            )
            
            response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    response += content
            
            return response
            
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return ""

    def _process_completed_response_actions(self, response: str):
        """Process all actions from completed response"""
        import re
        
        # Find all action tags
        action_pattern = r'<action\s+([^>]*?)(?:/>|>([^<]*)</action>)'
        matches = re.finditer(action_pattern, response, re.DOTALL)
        
        for match in matches:
            attrs_str = match.group(1)
            content = match.group(2) or ""
            
            # Parse attributes
            attrs = {}
            for attr_match in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
                attrs[attr_match.group(1)] = attr_match.group(2)
            
            action = {
                'type': attrs.get('type', ''),
                'raw_attrs': attrs,
                'content': content.strip()
            }
            
            action_type = action.get('type', '')
            if action_type.startswith('todo_'):
                self._handle_todo_actions(action)
            elif action_type == 'file':
                self._handle_file_interrupt(action)
            elif action_type == 'start_backend':
                self._handle_start_backend_interrupt(action)
            elif action_type == 'start_frontend':
                self._handle_start_frontend_interrupt(action)

    def _stream_with_real_interrupts(self, messages: list) -> str:
        """Stream with real-time interrupt handling like coder system"""
        print(f"🔄 Starting real-time interrupt streaming...")
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        full_response = ""
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*50}")
            print(f"📝 Generation iteration {iteration}/{max_iterations}")
            
            try:
                # Create streaming response
                completion = self.client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000,
                    stream=True
                )
                
                # Process stream with interrupt detection
                parser = StreamingXMLParser()
                accumulated_content = ""
                should_interrupt = False
                interrupt_action = None
                
                print("🌊 Processing streaming chunks...")
                
                for chunk in completion:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end='', flush=True)
                        accumulated_content += content
                        
                        # Parse for actions in real-time
                        actions = list(parser.process_chunk(content))
                        
                        for action in actions:
                            action_type = action.get('type')
                            if action_type:
                                print(f"\n🚨 INTERRUPT: Detected {action_type} action")
                                should_interrupt = True
                                interrupt_action = action
                                print("⚡ Breaking from chunk loop for interrupt")
                                break
                        
                        if should_interrupt:
                            print("🛑 Interrupt flag set, breaking from chunk processing")
                            break
                
                print(f"\n📊 Accumulated content length: {len(accumulated_content)} chars")
                full_response += accumulated_content
                
                # Handle interrupt if detected
                if should_interrupt and interrupt_action:
                    action_type = interrupt_action.get('type')
                    print(f"\n🚨 PROCESSING INTERRUPT: {action_type}")
                    
                    if action_type.startswith('todo_'):
                        # Handle todo actions
                        self._handle_todo_actions(interrupt_action)
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"Todo action {action_type} completed. Please continue with your response."}
                        messages.extend([assistant_msg, user_msg])
                        continue
                        
                    elif action_type == 'file':
                        # Handle file creation using parent class method
                        result = super()._handle_create_file_realtime({'content': accumulated_content})
                        if result:
                            assistant_msg = {"role": "assistant", "content": accumulated_content}
                            user_msg = {"role": "user", "content": f"File created successfully. Please continue with your response."}
                            messages.extend([assistant_msg, user_msg])
                            continue
                        else:
                            print("❌ Failed to create file, stopping")
                            break
                            
                    elif action_type == 'start_backend':
                        # Handle backend start using parent class method
                        result = super()._handle_start_backend_interrupt(interrupt_action)
                        if result:
                            backend_url = result.get('backend_url', 'http://localhost:8000')
                            assistant_msg = {"role": "assistant", "content": accumulated_content}
                            user_msg = {"role": "user", "content": f"Backend started successfully at {backend_url}. BACKEND_URL environment variable is set. Please continue with your response."}
                            messages.extend([assistant_msg, user_msg])
                            continue
                        else:
                            print("❌ Failed to start backend, stopping")
                            break
                            
                    elif action_type == 'start_frontend':
                        # Handle frontend start using parent class method
                        result = super()._handle_start_frontend_interrupt(interrupt_action)
                        if result:
                            frontend_url = result.get('frontend_url', 'http://localhost:3000')
                            assistant_msg = {"role": "assistant", "content": accumulated_content}
                            user_msg = {"role": "user", "content": f"Frontend started successfully at {frontend_url}. Please continue with your response."}
                            messages.extend([assistant_msg, user_msg])
                            continue
                        else:
                            print("❌ Failed to start frontend, stopping")
                            break
                else:
                    # No interrupts, we're done
                    print("✅ No interrupts detected, generation complete")
                    break
                    
            except Exception as e:
                print(f"❌ Error during streaming: {e}")
                break
        
        return full_response

    def _generate_with_interrupts(self, messages: list) -> str:
        """Generate response with interrupt-and-continue pattern from coder system"""
        print(f"🔄 Starting generation with interrupt support...")
        
        # Use the coder system which handles interrupts properly
        full_response = coder(messages=messages, self=self.state)
        return full_response

    def _stream_completion_with_interrupts(self, prompt: str) -> str:
        """Stream completion with interrupt handling"""
        max_iterations = 10
        iteration = 0 
        full_response = ""
        
        # Convert prompt to messages format
        messages = [{"role": "user", "content": prompt}]
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Generation iteration {iteration}/{max_iterations}")
            
            try:
                # Create streaming response  
                stream = self.client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=messages,
                    stream=True,
                    temperature=0.1,
                    max_tokens=4000
                )
                
                chunk_response = ""
                parser = StreamingXMLParser()
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end='', flush=True)
                        chunk_response += content
                        full_response += content
                        
                        # Process chunks for actions
                        for action in parser.process_chunk(content):
                            action_type = action.get('type', '')
                            if action_type:  # Only interrupt if we have a valid action type
                                print(f"\n🚨 INTERRUPT: Detected {action_type} action")
                                
                                # Handle the action immediately
                                result = self._handle_action_interrupt(action)
                                
                                if result:
                                    # Add result to conversation and continue
                                    action_result_msg = f"\nAction {action_type} completed: {result}"
                                    messages.append({"role": "assistant", "content": chunk_response})
                                    messages.append({"role": "user", "content": action_result_msg})
                                    print(f"✅ Action completed, continuing generation...")
                                    
                                    # Start new iteration for continuation
                                    chunk_response = ""
                                    break
                
                # If no interrupts, we're done
                break
                
            except Exception as e:
                print(f"❌ Streaming error: {e}")
                break
        
        return full_response

    # All interrupt handlers are inherited from GroqAgent parent class
    # Only need to override specific behavior for todo actions

def main():
    """Main function for natural workflow system"""
    print("🧠 Natural Workflow Groq System")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("GROQ_API_KEY", "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")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable is required")
        return
    
    # Get user request
    user_request = input("\n🎯 What would you like to build? ")
    if not user_request.strip():
        print("❌ Error: Please provide a request")
        return
    
    # Initialize system
    project_name = generate_project_name(user_request)
    system = NaturalWorkflowGroq(
        api_key=api_key,
        project_name=project_name
    )
    
    # Process initial request
    system.process_request(user_request)
    
    # Interactive loop for follow-up requests
    while True:
        print(f"\n" + "="*60)
        follow_up = input("\n🔄 Any updates or additional requests? (press Enter to finish): ")
        
        if not follow_up.strip():
            break
            
        system.process_request(follow_up)
    
    print(f"\n✅ Natural workflow session completed!")
    print(f"📋 Final todo status:")
    system._display_todos()

if __name__ == "__main__":
    main()