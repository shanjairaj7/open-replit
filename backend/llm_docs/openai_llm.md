# LLM Integration Guide - OpenAI Package with OpenRouter

## Quick Setup

**Requirements:** Add to `requirements.txt`:
```
openai
python-dotenv
```

**Environment:** The `OPENROUTER_API_KEY` is automatically provided in all deployed backends.

**Basic Client Setup:**
```python
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
```

**Important:** Always use **non-streaming** for better UX. Show skeleton loaders in frontend while waiting for response.

## How Messages Work

Messages are conversation arrays that the LLM processes:
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant that can use tools."},  # Instructions
    {"role": "user", "content": "What is Python?"},                                    # User input
    {"role": "assistant", "content": "Python is a programming language..."},           # LLM response
    {"role": "assistant", "tool_calls": [...]},                                        # LLM wants to use tools
    {"role": "tool", "tool_call_id": "call_123", "name": "get_data", "content": "..."}  # Tool results
]
```

**Key Concept:** The LLM sees the entire conversation history and decides what to do next - respond directly or use tools.

## Tool Integration

Tools let the LLM execute functions to get real data. Here's the complete pattern:

```python
# 1. Define tool functions
def get_weather(location: str) -> str:
    return f"Weather in {location}: 22°C, sunny"

def get_user_tasks(user_id: str) -> str:
    # Real database integration using backend-boilerplate's json_db.py
    from json_db import db
    tasks = db.find_all("tasks", user_id=int(user_id))
    if not tasks:
        return f"No tasks found for user {user_id}"
    return f"Found {len(tasks)} tasks: " + ", ".join([t['title'] for t in tasks])

# 2. Create tool definitions (OpenAI format)
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_tasks",
            "description": "Get all tasks for a user from database",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"]
            }
        }
    }
]

# 3. Tool handler mapping
tool_handlers = {"get_weather": get_weather, "get_user_tasks": get_user_tasks}

def execute_tool_call(tool_call):
    """Execute any tool call and return result"""
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    if function_name in tool_handlers:
        result = tool_handlers[function_name](**arguments)
        return {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": result
        }
```

## Universal Agent Function (Use This Always)

**IMPORTANT:** Always use this agentic pattern for ANY LLM request. It handles both simple responses and tool calls automatically.

```python
def agent_chat(user_message: str, conversation_history: list = None):
    """Universal agent - handles all LLM requests with automatic tool calling"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed for real data."}
    ]

    # Add conversation history for chat apps
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    while True:
        # Call LLM (non-streaming preferred)
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",  # Best for tools
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # Add assistant response to conversation
        if message.content:
            messages.append({"role": "assistant", "content": message.content})

        # Handle tool calls automatically
        if message.tool_calls:
            # Add tool calls to conversation
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                } for tc in message.tool_calls]
            })

            # Execute tools and add results
            for tool_call in message.tool_calls:
                tool_result = execute_tool_call(tool_call)
                if tool_result:
                    messages.append(tool_result)
            continue  # Loop again for final response
        else:
            # No tools needed, return final response and conversation
            return {
                "response": message.content,
                "conversation": messages  # For persistence in chat apps
            }

# Usage Examples:
# Simple: agent_chat("What is Python?")["response"]
# With tools: agent_chat("Get tasks for user 123")["response"]
# With history: agent_chat("And for user 456?", previous_conversation)["response"]
```

## Available Models

**Recommended Models (Cost vs Performance):**
- `meta-llama/llama-3.1-8b-instruct` - Best for tools ($0.000015/1k)
- `mistralai/mistral-nemo` - Good balance ($0.0000075/1k)
- `meta-llama/llama-3.2-3b-instruct` - Cheapest ($0.000003/1k)

**Tool Support:** Use `meta-llama/llama-3.1-8b-instruct` for reliable tool calling.

## Technical Breakdown: What Happens Step-by-Step

When you call `agent_chat("Get me all tasks for user 123 and tell me which ones are urgent")`, here's exactly what happens:

1. **LLM receives the message** and analyzes it
2. **LLM decides it needs the `get_user_tasks` tool** to access the database
3. **Tool function executes** - connects to JSON database and runs `db.find_all("tasks", user_id=123)`
4. **Database returns results** like `[{"id": 1, "user_id": 123, "title": "Fix bug", "priority": "high"}, ...]`
5. **Tool result gets added** to the conversation as a tool response
6. **LLM processes the database results** and generates a natural language response
7. **Final response returned**: "I found 5 tasks for user 123. The urgent ones are: Fix bug (high priority) and Deploy app (urgent priority)."

## The AI-Powered App Superpower

**LLM + Tools is not just integration - it's transformation.** You're not adding a chatbot to your app, you're creating an intelligent, conversational interface that can both understand and modify your data.

### What This Really Means

**Traditional App**: User clicks buttons → App shows data
**AI-Powered App**: User talks naturally → AI understands, analyzes, and takes action

### Core Superpowers

1. **Intelligent Data Reading**: AI doesn't just show data - it understands, summarizes, and finds patterns
2. **Conversational Actions**: Users describe what they want - AI figures out how to do it
3. **Smart Automation**: AI can analyze situations and suggest/take appropriate actions
4. **Context Awareness**: AI remembers conversation and app state to provide relevant responses

### Real Application Examples

#### 🎯 **Task Manager App**
- **Basic**: "Show my tasks" → List of tasks
- **AI-Powered**: "I'm overwhelmed with my project" → AI analyzes tasks, suggests priorities, breaks complex tasks into subtasks, updates database automatically

#### 🛒 **E-commerce App**
- **Basic**: "Show my orders" → Order history
- **AI-Powered**: "I need something for my dinner party" → AI analyzes past preferences, suggests products, calculates quantities, creates shopping list

#### 📊 **Business CRM**
- **Basic**: "Show client info" → Client data
- **AI-Powered**: "How should I approach this client?" → AI analyzes client history, suggests strategy, schedules follow-ups, creates action items

### The Game-Changing Pattern

```
User Request → AI Analysis → Smart Action → Database Update → Intelligent Response
```

Instead of just retrieving data, the AI:
1. **Understands intent** behind user's request
2. **Analyzes available data** for insights
3. **Takes intelligent actions** (create, update, organize)
4. **Provides contextualized responses** with explanations

### Complete Smart Task Example

```python
def update_task(task_id: str, detailed_plan: str) -> str:
    """Simple tool to update a task with new information"""
    from json_db import db

    success = db.update_one(
        "tasks",
        {"id": int(task_id)},
        {
            "description": updated_description,
            "status": "planned",
        }
    )

    return "Task updated with detailed plan!" if success else "Failed to update task"

def smart_task_assistant(user_message: str) -> str:
    """AI-powered task assistant - LLM does the analysis, tools do simple operations"""

    # Simple, focused tools - no AI logic inside them
    smart_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_user_tasks",
                "description": "Get all tasks for a specific user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"}
                    },
                    "required": ["user_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_task",
                "description": "Update a task with new detailed plan or information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task to update"},
                        "updated_description": {"type": "string", "description": "Detailed action plan for completing the task"}
                    },
                    "required": ["task_id", "updated_description"]
                }
            }
        }
    ]

    # Tool handlers - simple database operations only
    smart_tool_handlers = {
        "get_user_tasks": get_user_tasks,  # From previous examples
        "update_task": update_task
    }

    def execute_smart_tool_call(tool_call):
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        if function_name in smart_tool_handlers:
            result = smart_tool_handlers[function_name](**arguments)
            return {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result
            }

    # AI agent - intelligence lives here, not in tools
    messages = [
        {"role": "system", "content": """You are a smart productivity assistant. You can:
        1. Get user tasks to understand their workload
        2. When users feel overwhelmed about a task, break it into detailed action steps
        3. Update tasks with your detailed plans using the update_task tool

        Always analyze tasks yourself and create detailed, actionable plans. Use tools for data operations only."""},
        {"role": "user", "content": user_message}
    ]

    while True:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=messages,
            tools=smart_tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.content:
            messages.append({"role": "assistant", "content": message.content})

        if message.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                } for tc in message.tool_calls]
            })

            for tool_call in message.tool_calls:
                tool_result = execute_smart_tool_call(tool_call)
                if tool_result:
                    messages.append(tool_result)
            continue
        else:
            return message.content

# How This Actually Works:
# User: "I'm really struggling with task 123, it feels too big"
#
# LLM thinks: "User needs help with task 123. Let me get their tasks first, then create a plan"
# 1. LLM calls get_user_tasks(user_id="456")
# 2. LLM sees task 123: "Launch Marketing Campaign"
# 3. LLM analyzes and creates detailed plan internally
# 4. LLM calls update_task(task_id="123", description="1. Define target audience (2 hrs)...")
# 5. LLM responds: "I understand you're overwhelmed! I've broken down your marketing campaign into 8 manageable steps in your description, you can take a look at it in the plan section in your task..."
```

### Why This Changes Everything

**Before AI**: Apps were static interfaces to data
**After AI**: Apps become intelligent assistants that understand, analyze, and act

Your task manager isn't just storing tasks - it's a productivity coach.
Your e-commerce site isn't just showing products - it's a personal shopping assistant.
Your CRM isn't just storing contacts - it's a relationship strategist.

**The real superpower**: Every app becomes a domain expert that can have intelligent conversations about its data and take smart actions to help users succeed.

## Message Persistence for Chat Apps

```python
def save_conversation(user_id: str, messages: list):
    """Save conversation to database"""
    from json_db import db
    conversation_data = {
        "user_id": user_id,
        "messages": messages,
        "updated_at": datetime.now().isoformat()
    }
    return db.insert("conversations", conversation_data)

def load_conversation(user_id: str) -> list:
    """Load conversation from database"""
    from json_db import db
    conversation = db.find_one("conversations", user_id=user_id)
    return conversation.get("messages", []) if conversation else []

def chat_with_persistence(user_message: str, user_id: str):
    """Chat function with message persistence"""
    history = load_conversation(user_id)
    result = agent_chat(user_message, conversation_history=history)
    save_conversation(user_id, result["conversation"])
    return result["response"]
```


## Implementation Rules

### 1. UI/UX Guidelines
- **Always use non-streaming** for cleaner user experience
- **Show skeleton loaders** while waiting for LLM response
- **Different UI patterns** for different app types:
  - Chat apps: Message bubbles with typing indicators
  - Form apps: Loading states on submit buttons
  - Dashboard apps: Skeleton cards/tables
- **Store all messages** in database for persistence

### 2. Agent Implementation Rules
- **Always use the universal agent pattern** (while loop with tools)
- **Pass conversation history** for context in chat apps
- **Return both response and conversation** for persistence
- **Handle tool calls automatically** - no manual intervention needed
- **Use cheapest model** unless tools are required

### 3. Database Integration Rules
- **Store complete conversation arrays** in JSON format
- **Include metadata** (user_id, timestamps, app_context)
- **Load conversation history** before each agent call in chat apps
- **Save immediately** after each response

### 4. Frontend Integration Rules
- **Show skeleton loader** immediately on user action
- **Call non-streaming endpoint** from frontend
- **Update UI** when response arrives
- **Store conversation state** in frontend for immediate UX
- **Sync with backend** for persistence

### 5. Error Handling Rules
- **Always include try-catch** around LLM calls
- **Provide fallback responses** if tools fail
- **Log errors** but continue conversation
- **Return partial results** if some tools succeed

## Advanced: Streaming (If Needed)

**Prefer non-streaming**, but if streaming is required:

```python
def streaming_agent_chat(user_message: str):
    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}]

    stream = client.chat.completions.create(
        model="meta-llama/llama-3.1-8b-instruct",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True
    )

    full_content = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_content += content

    # Note: Tool calling with streaming requires additional complexity
    # Prefer non-streaming for tool-based agents
```

**Streaming Properties:**
- `chunk.choices[0].delta.content` - Text content (None if no content)
- `chunk.choices[0].finish_reason` - "stop", "length", "tool_calls", or None
- `chunk.choices[0].delta.tool_calls` - Tool calls (if any)
