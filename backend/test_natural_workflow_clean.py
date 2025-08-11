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
from datetime import datetime
from groq import Groq
from shared_models import GroqAgentState, StreamingXMLParser

# Import existing interrupt handlers from test_groq_local
from test_groq_local import BoilerplatePersistentGroq

def generate_project_name(request: str) -> str:
    """Generate project name from user request"""
    if not request:
        timestamp = datetime.now().strftime("%m%d-%H%M")
        return f'project-{timestamp}'
    
    # Extract key terms
    words = re.findall(r'\b[a-zA-Z]{3,}\b', request.lower())
    
    # Filter out common words
    common_words = {'the', 'and', 'for', 'with', 'can', 'you', 'app', 'application', 'system', 'want', 'need', 'build', 'create', 'make'}
    key_words = [w for w in words[:3] if w not in common_words]
    
    if key_words:
        timestamp = datetime.now().strftime("%m%d-%H%M")
        project_name = '-'.join(key_words) + f'-{timestamp}'
    else:
        timestamp = datetime.now().strftime("%m%d-%H%M")
        project_name = f'project-{timestamp}'
    
    return project_name

class NaturalWorkflowGroq(BoilerplatePersistentGroq):
    """
    Natural workflow system - inherits all interrupt handlers from GroqAgent
    """
    
    def __init__(self, api_key: str = None, project_name: str = None, api_base_url: str = "http://localhost:8000", project_id: str = None):
        # Generate project details first
        generated_project_name = project_name or generate_project_name("natural-workflow")
        
        # Initialize parent class WITHOUT project_id to trigger new project creation
        super().__init__(
            api_key=api_key or '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', 
            project_name=generated_project_name,
            api_base_url=f"{api_base_url}/api"
            # Don't pass project_id - this will trigger new project creation flow
        )
        
        # Todo management  
        self.todos = []
        
        print(f"🧠 Natural Workflow System Initialized")
        print(f"📋 Project: {self.project_name} ({self.project_id})")
        print(f"🎯 Ready for todo-driven development")

    def process_request(self, user_request: str):
        """Process user request with natural workflow using parent class methods"""
        print(f"\n🎯 PROCESSING REQUEST: {user_request}")
        print("=" * 60)
        
        # Modify the user request to include natural workflow instructions
        enhanced_request = f"""{user_request}

IMPORTANT: As a senior engineer, work naturally by:
1. Breaking down requirements into actionable todos using `<action type="todo_create" id="unique_id" priority="high/medium/low" integration="true/false">Description</action>`
2. Updating todo status when you start working: `<action type="todo_update" id="todo_id" status="in_progress"/>`
3. Completing todos when done: `<action type="todo_complete" id="todo_id" integration_tested="true/false"/>`
4. Creating files: `<action type="file" filePath="path/to/file">FILE_CONTENT</action>`
5. Starting services: `<action type="start_backend"/>` and `<action type="start_frontend"/>`

Work systematically through each todo to build a complete, working solution."""
        
        # Use the coder system directly without planning - let model create todos naturally
        print(f"🧠 Using direct coder system with natural todo workflow...")
        
        # Add the user request to conversation history
        self.conversation_history.append({"role": "user", "content": enhanced_request})
        
        # Use the coder system directly with current conversation history
        from coder.index import coder
        response = coder(messages=self.conversation_history, self=self)
        
        # Add model response to conversation history
        if response:
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Add current todo status as user message for next iteration awareness
            todo_status = self._get_todo_status_summary()
            if todo_status:
                self.conversation_history.append({"role": "user", "content": todo_status})
            
        print(f"\n✅ Request processing completed")
        return response

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

    # Custom streaming method removed - using parent class send_message_with_chunks

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
    
    # Show final status
    system._display_todos()
    
    print(f"\n✅ Natural workflow session completed!")

if __name__ == "__main__":
    main()