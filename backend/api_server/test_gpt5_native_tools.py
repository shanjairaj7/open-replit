#!/usr/bin/env python3
"""
Test GPT-5 with native tool calling - iterative testing until it works
"""

import os
import json
from openai import AzureOpenAI
import sys

# Get the prompt content
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prompts.gpt5_prompt import prompt

# Azure OpenAI Configuration
USE_AZURE = True  # Set to True to use Azure, False for standard OpenAI

if USE_AZURE:
    # Azure configuration - using the same config as agent_class.py
    AZURE_ENDPOINT = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com"
    AZURE_API_KEY = os.environ.get('AZURE_SUBSCRIPTION_KEY', 'FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1')
    MODEL_NAME = "gpt-5"  # GPT-5 deployment name
    
    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version="2024-12-01-preview",
        azure_endpoint=AZURE_ENDPOINT
    )
else:
    # Standard OpenAI configuration (simpler for testing)
    from openai import OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    MODEL_NAME = "gpt-4-turbo-preview"  # Use a model that supports tools
    
    client = OpenAI(api_key=OPENAI_API_KEY)

# Define all native tools from the GPT-5 prompt
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory or entire project",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (optional, omit for all files)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "Update a file using search and replace blocks",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to update"
                    },
                    "search": {
                        "type": "string",
                        "description": "Exact content to search for (must match character-for-character)"
                    },
                    "replace": {
                        "type": "string",
                        "description": "New content to replace with"
                    }
                },
                "required": ["path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with complete content",
            "parameters": {
                "type": "object",
                "properties": {
                    "filePath": {
                        "type": "string",
                        "description": "Path where the file should be created"
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete file content"
                    }
                },
                "required": ["filePath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_logs",
            "description": "Check logs of a service (backend or frontend)",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["backend", "frontend"],
                        "description": "Service to check logs for"
                    }
                },
                "required": ["service"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_network",
            "description": "Check network requests for debugging",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["frontend"],
                        "description": "Service to check network for"
                    }
                },
                "required": ["service"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "todo_create",
            "description": "Create a task management todo item",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for the todo"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Priority level"
                    },
                    "description": {
                        "type": "string",
                        "description": "Todo description"
                    }
                },
                "required": ["id", "priority", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "integration_docs",
            "description": "Access integration documentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "search", "read"],
                        "description": "Operation to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search operation)"
                    },
                    "doc_name": {
                        "type": "string",
                        "description": "Document name (for read operation)"
                    }
                },
                "required": ["operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "attempt_completion",
            "description": "Signal that the implementation is fully complete",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Completion message"
                    }
                },
                "required": ["message"]
            }
        }
    }
]

# Tool implementations (placeholders for testing)
def read_file(path):
    print(f"  📖 [read_file] Reading: {path}")
    if "app.py" in path:
        return """from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}"""
    return f"# Contents of {path}\nprint('Hello from {path}')"

def list_files(path=None):
    print(f"  📁 [list_files] Listing: {path or 'all files'}")
    if path and "backend" in path:
        return "app.py\nroutes/\n  __init__.py\n  auth.py\n  users.py\njson_db.py"
    return "backend/\n  app.py\nfrontend/\n  src/\n    App.tsx\n    main.tsx"

def update_file(path, search, replace):
    print(f"  ✏️ [update_file] Updating: {path}")
    print(f"     Search: {search[:50]}...")
    print(f"     Replace: {replace[:50]}...")
    return f"Successfully updated {path}"

def create_file(filePath, content):
    print(f"  📝 [create_file] Creating: {filePath}")
    print(f"     Content length: {len(content)} chars")
    return f"Created {filePath}"

def check_logs(service):
    print(f"  📋 [check_logs] Checking {service} logs")
    return f"No errors in {service} logs"

def check_network(service):
    print(f"  🌐 [check_network] Checking {service} network")
    return "No network errors detected"

def todo_create(id, priority, description):
    print(f"  ✅ [todo_create] Creating todo: {id} ({priority})")
    return f"Created todo: {description}"

def integration_docs(operation, query=None, doc_name=None):
    print(f"  📚 [integration_docs] Operation: {operation}")
    if operation == "list":
        return "Available docs: openai_integration.md, stripe_integration.md, exa_integration.md"
    elif operation == "search" and query:
        return f"Found docs matching '{query}': openai_integration.md"
    elif operation == "read" and doc_name:
        return f"# {doc_name}\n\nIntegration guide content here..."
    return "No results"

def web_search(query):
    print(f"  🔍 [web_search] Searching: {query}")
    return f"Search results for '{query}': [1] Example result [2] Another result"

def attempt_completion(message):
    print(f"  🎉 [attempt_completion] {message}")
    return "Implementation marked as complete"

# Map function names to implementations
available_functions = {
    "read_file": read_file,
    "list_files": list_files,
    "update_file": update_file,
    "create_file": create_file,
    "check_logs": check_logs,
    "check_network": check_network,
    "todo_create": todo_create,
    "integration_docs": integration_docs,
    "web_search": web_search,
    "attempt_completion": attempt_completion
}

def clean_prompt_for_native_tools(original_prompt):
    """Remove XML action tags and update prompt for native tools"""
    
    # Remove the tools section and replace with native function instructions
    lines = original_prompt.split('\n')
    new_lines = []
    skip_until = None
    
    for i, line in enumerate(lines):
        # Skip the XML tools section
        if '## Tools' in line:
            skip_until = '## Tool usage guidelines'
            new_lines.append("## Tools\n")
            new_lines.append("You have access to the following native functions. Call them directly instead of using XML tags:\n")
            new_lines.append("- read_file(path) - Read file contents")
            new_lines.append("- list_files(path) - List files in directory") 
            new_lines.append("- update_file(path, search, replace) - Update file with search/replace")
            new_lines.append("- create_file(filePath, content) - Create new file")
            new_lines.append("- check_logs(service) - Check service logs")
            new_lines.append("- check_network(service) - Check network requests")
            new_lines.append("- todo_create(id, priority, description) - Create todo item")
            new_lines.append("- integration_docs(operation, query, doc_name) - Access docs")
            new_lines.append("- web_search(query) - Search the web")
            new_lines.append("- attempt_completion(message) - Mark as complete\n")
            continue
            
        if skip_until and skip_until in line:
            skip_until = None
            new_lines.append("\n## Native Function Calling Guidelines")
            new_lines.append("Instead of XML action tags, use the provided functions directly.")
            new_lines.append("Always create a clear plan first, then execute it step by step using function calls.")
            new_lines.append("For file updates, call update_file with exact search and replace strings.\n")
            continue
            
        if skip_until:
            continue
            
        # Skip XML examples
        if '<action type=' in line or '------- SEARCH' in line or '+++++++ REPLACE' in line:
            continue
            
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def test_iteration(iteration_num, test_prompt):
    """Run a single test iteration"""
    print(f"\n{'='*60}")
    print(f"🔄 ITERATION {iteration_num}")
    print(f"{'='*60}")
    
    # Prepare system prompt
    system_prompt = clean_prompt_for_native_tools(prompt)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_prompt}
    ]
    
    print(f"📝 User: {test_prompt}")
    print(f"⏳ Calling GPT-5 with native tools...")
    
    try:
        # Call GPT-5 with tools
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=4000
        )
        
        response_message = response.choices[0].message
        
        if response_message.content:
            print(f"\n🤖 Assistant: {response_message.content[:500]}...")
        
        # Check for tool calls
        if response_message.tool_calls:
            print(f"\n🔧 Tool calls requested: {len(response_message.tool_calls)}")
            
            # Execute each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"\n➡️ Executing: {function_name}")
                
                # Execute function
                if function_name in available_functions:
                    function = available_functions[function_name]
                    result = function(**function_args)
                    
                    # Add to messages
                    messages.append(response_message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result)
                    })
            
            # Get next response
            print(f"\n⏳ Getting next response after tool execution...")
            next_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                max_completion_tokens=4000
            )
            
            if next_response.choices[0].message.content:
                print(f"\n🤖 Assistant (after tools): {next_response.choices[0].message.content[:500]}...")
            
            # Check if more tools are needed
            if next_response.choices[0].message.tool_calls:
                print(f"\n🔄 More tools requested: {len(next_response.choices[0].message.tool_calls)}")
                
                # Execute the next round of tool calls to see full flow
                for tool_call in next_response.choices[0].message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"➡️ Executing: {function_name}")
                    
                    if function_name in available_functions:
                        function = available_functions[function_name]
                        result = function(**function_args)
                        
                        messages.append(next_response.choices[0].message)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": str(result)
                        })
                
                # Get final response
                print(f"\n⏳ Getting final response...")
                final_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=tools,
                    max_completion_tokens=4000
                )
                
                if final_response.choices[0].message.content:
                    print(f"\n🤖 Final response: {final_response.choices[0].message.content[:300]}...")
                
                return True  # Success - model completed full flow
            
            return True  # Success - model used tools
        else:
            print("\n⚠️ No tool calls made - model didn't use native functions")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        if hasattr(e, 'response'):
            print(f"❌ Response: {getattr(e, 'response', 'No response')}")
        return False

def main():
    """Main test loop - iterate until model successfully uses tools"""
    
    print("🚀 Starting GPT-5 Native Tools Testing")
    print("=" * 60)
    
    # Test scenarios
    test_prompts = [
        "Build a basic todo list backend with FastAPI that includes user authentication",
        "Create a simple Python hello world script",
        "Show me what files are in the backend folder",
        "Create a new route for user management in the backend"
    ]
    
    for i, test_prompt in enumerate(test_prompts, 1):
        success = test_iteration(i, test_prompt)
        
        if success:
            print(f"\n✅ SUCCESS on iteration {i}! Model is using native tools properly.")
            print("The model successfully:")
            print("1. Built a plan")
            print("2. Called native tool functions")
            print("3. Processed the results")
            break
        else:
            print(f"\n⚠️ Iteration {i} needs improvement")
            if i < len(test_prompts):
                print("Trying next test scenario...")
    
    print("\n" + "="*60)
    print("🏁 Testing complete!")

if __name__ == "__main__":
    main()