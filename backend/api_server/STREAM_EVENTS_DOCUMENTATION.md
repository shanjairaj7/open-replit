# Stream Events Documentation

This document outlines all the streaming events emitted by the agent system, their data structures, and usage patterns.

## Overview

The agent system emits four main types of streaming events:

1. **assistant_message** - Regular assistant text responses
2. **action_start** - When an action begins execution
3. **action_result** - When an action completes with results
4. **attempt_completion** - When the task is completed

## Event Types and Data Structures

### 1. assistant_message

**Purpose**: Streams regular assistant text responses during conversation.

**Structure**:

```json
{
  "event_type": "assistant_message",
  "content": "string - The assistant's response text",
  "metadata": null
}
```

**Usage**: Emitted during normal conversation flow when the assistant is responding without executing actions.

---

### 2. action_start

**Purpose**: Signals the start of an action execution.

**Structure**:

```json
{
  "event_type": "action_start",
  "content": "string - Human-readable description of the action",
  "metadata": {
    "action_type": "string - Type of action being started",
    "file_path": "string (optional) - File path for file operations",
    "command": "string (optional) - Command being executed",
    "cwd": "string (optional) - Working directory for commands",
    "service": "string (optional) - Service name for service operations",
    "todo_id": "string (optional) - Todo ID for todo operations",
    "description": "string (optional) - Todo description",
    "priority": "string (optional) - Todo priority",
    "status": "string (optional) - Todo status",
    "sub_actions_count": "number (optional) - Number of sub-actions for parallel",
    "action_details": "object (optional) - Full action object"
  }
}
```

## Action Type Reference with Exact Data Structures

### File Operations

#### read_file

```json
{
  "event_type": "action_start",
  "content": "Reading file: {file_path}",
  "metadata": {
    "action_type": "read_file",
    "file_path": "{file_path}",
    "action_details": {
      "type": "read_file",
      "path": "{file_path}"
    }
  }
}
```

#### update_file

```json
{
  "event_type": "action_start",
  "content": "Updating file: {file_path}",
  "metadata": {
    "action_type": "update_file",
    "file_path": "{file_path}",
    "action_details": {
      "type": "update_file",
      "path": "{file_path}"
    }
  }
}
```

#### create_file

```json
{
  "event_type": "action_start",
  "content": "Creating file: {file_path}",
  "metadata": {
    "action_type": "create_file",
    "file_path": "{file_path}",
    "action_details": {
      "type": "file",
      "filePath": "{file_path}"
    }
  }
}
```

#### rename_file

```json
{
  "event_type": "action_start",
  "content": "Renaming file: {old_path} → {new_name}",
  "metadata": {
    "action_type": "rename_file",
    "file_path": "{old_path}",
    "new_name": "{new_name}",
    "action_details": {
      "type": "rename_file",
      "path": "{old_path}",
      "new_name": "{new_name}"
    }
  }
}
```

#### delete_file

```json
{
  "event_type": "action_start",
  "content": "Deleting file: {file_path}",
  "metadata": {
    "action_type": "delete_file",
    "file_path": "{file_path}",
    "action_details": {
      "type": "delete_file",
      "path": "{file_path}"
    }
  }
}
```

### Terminal Operations

#### run_command

```json
{
  "event_type": "action_start",
  "content": "Running command: {command}",
  "metadata": {
    "action_type": "run_command",
    "command": "{command}",
    "cwd": "{working_directory}",
    "action_details": {
      "type": "run_command",
      "command": "{command}",
      "cwd": "{working_directory}"
    }
  }
}
```

### Service Operations

#### start_backend

```json
{
  "event_type": "action_start",
  "content": "Starting backend service",
  "metadata": {
    "action_type": "start_backend",
    "service": "backend",
    "action_details": {
      "type": "start_backend"
    }
  }
}
```

#### start_frontend

```json
{
  "event_type": "action_start",
  "content": "Starting frontend service",
  "metadata": {
    "action_type": "start_frontend",
    "service": "frontend",
    "action_details": {
      "type": "start_frontend"
    }
  }
}
```

### Diagnostics

#### check_logs

```json
{
  "event_type": "action_start",
  "content": "Checking logs for {service} service",
  "metadata": {
    "action_type": "check_logs",
    "service": "{service}",
    "action_details": {
      "type": "check_logs",
      "service": "{service}"
    }
  }
}
```

#### check_network

```json
{
  "event_type": "action_start",
  "content": "Checking network requests for frontend service",
  "metadata": {
    "action_type": "check_network",
    "service": "frontend",
    "action_details": {
      "type": "check_network"
    }
  }
}
```

### Task Management

#### todo_create

```json
{
  "event_type": "action_start",
  "content": "Creating todo: {description}",
  "metadata": {
    "action_type": "todo_create",
    "todo_id": "{todo_id}",
    "description": "{description}",
    "priority": "{priority}",
    "action_details": {
      "type": "todo_create",
      "id": "{todo_id}",
      "priority": "{priority}",
      "content": "{description}"
    }
  }
}
```

#### todo_update

```json
{
  "event_type": "action_start",
  "content": "Updating todo {todo_id} → {status}",
  "metadata": {
    "action_type": "todo_update",
    "todo_id": "{todo_id}",
    "status": "{status}",
    "action_details": {
      "type": "todo_update",
      "id": "{todo_id}",
      "status": "{status}"
    }
  }
}
```

#### todo_complete

```json
{
  "event_type": "action_start",
  "content": "Completing todo: {todo_id}",
  "metadata": {
    "action_type": "todo_complete",
    "todo_id": "{todo_id}",
    "action_details": {
      "type": "todo_complete",
      "id": "{todo_id}"
    }
  }
}
```

### Advanced Operations

#### parallel

```json
{
  "event_type": "action_start",
  "content": "Executing parallel actions: {count} sub-actions",
  "metadata": {
    "action_type": "parallel",
    "sub_actions_count": {count},
    "action_details": {
      "type": "parallel",
      "actions": [...]
    }
  }
}
```

---

### 3. action_result

**Purpose**: Reports the completion of an action with results or errors.

**Structure**:

```json
{
  "event_type": "action_result",
  "content": "string - Human-readable result description",
  "metadata": {
    "action_type": "string - Type of action that completed",
    "file_path": "string (optional) - File path for file operations",
    "command": "string (optional) - Command that was executed",
    "working_dir": "string (optional) - Working directory used",
    "success": "boolean (optional) - Whether the action succeeded",
    "error": "string (optional) - Error message if failed",
    "content_length": "number (optional) - Length of content read",
    "output_length": "number (optional) - Length of command output",
    "status": "string (optional) - Result status",
    "result": "any (optional) - Raw result data",
    "actions_count": "number (optional) - Total actions in parallel execution",
    "results_count": "number (optional) - Successful actions in parallel execution",
    "results": "array (optional) - Array of individual action results",
    "todo_id": "string (optional) - Todo ID for todo operations"
  }
}
```

**Result Data Structures by Action Type**:

#### read_file Results

```json
{
  "action_type": "read_file",
  "file_path": "path/to/file.txt",
  "success": true,
  "content": "Full file content as string",
  "content_length": 1234
}
```

#### run_command Results

```json
{
  "action_type": "run_command",
  "command": "ls -la",
  "working_dir": "/path/to/dir",
  "success": true,
  "output": "Command output as string",
  "output_length": 567
}
```

#### parallel Results

```json
{
  "action_type": "parallel",
  "actions_count": 3,
  "results_count": 3,
  "results": [
    {
      "action_type": "read_file",
      "file_path": "file1.txt",
      "success": true,
      "content": "...",
      "content_length": 100
    },
    {
      "action_type": "run_command",
      "command": "ls",
      "success": true,
      "output": "...",
      "output_length": 200
    }
  ]
}
```

#### todo Results

```json
{
  "action_type": "todo_create",
  "todo_id": "unique_id",
  "status": "success",
  "result": "Todo created successfully"
}
```

---

### 4. attempt_completion

**Purpose**: Signals the completion of the entire task.

**Structure**:

```json
{
  "event_type": "attempt_completion",
  "content": "object - Completion data structure",
  "metadata": null
}
```

**Content Structure**:

```json
{
  "success": true,
  "message": "string - Completion message",
  "session_ended": true,
  "timestamp": "ISO timestamp string"
}
```

## Action Type Reference

### File Operations

- **read_file**: Read file contents
- **update_file**: Modify existing files
- **create_file**: Create new files
- **rename_file**: Rename files
- **delete_file**: Delete files

### Terminal Operations

- **run_command**: Execute shell commands

### Service Operations

- **start_backend**: Start backend service
- **start_frontend**: Start frontend service
- **restart_backend**: Restart backend service
- **restart_frontend**: Restart frontend service

### Diagnostics

- **check_errors**: Check for system errors
- **check_logs**: Retrieve service logs
- **check_network**: Check network connectivity

### Task Management

- **todo_create**: Create new todos
- **todo_update**: Update todo status
- **todo_complete**: Mark todo as complete
- **todo_list**: List todos

### Advanced Operations

- **parallel**: Execute multiple actions concurrently
- **integration_docs**: Access integration documentation
- **web_search**: Perform web searches

## Usage Patterns

### Sequential Actions

```javascript
// Action starts
{ event_type: "action_start", content: "Reading file: config.json", metadata: { action_type: "read_file", file_path: "config.json" } }

// Action completes
{ event_type: "action_result", content: "Read 1234 characters from: config.json", metadata: { action_type: "read_file", success: true, content_length: 1234 } }
```

### Parallel Actions

```javascript
// Parallel execution starts
{ event_type: "action_start", content: "Executing parallel actions: 3 sub-actions", metadata: { action_type: "parallel", sub_actions_count: 3 } }

// Individual action starts (may be emitted for each sub-action)
// ...

// Parallel execution completes
{ event_type: "action_result", content: "Parallel execution completed: 3/3 actions", metadata: { action_type: "parallel", actions_count: 3, results_count: 3, results: [...] } }
```

### Error Handling

```javascript
// Action fails
{ event_type: "action_result", content: "Error reading file: nonexistent.txt", metadata: { action_type: "read_file", success: false, error: "File not found" } }
```

## Implementation Notes

- All events include `event_type`, `content`, and optional `metadata`
- `content` is always a human-readable string description
- `metadata` contains structured data for programmatic processing
- File operations include full content in results (no truncation)
- Parallel operations aggregate results from all sub-actions
- Error states are clearly indicated with `success: false` and error messages

## Frontend Integration

When integrating with frontend streaming:

1. Listen for `action_start` to show loading states
2. Process `action_result` to display results or handle errors
3. Use `assistant_message` for regular conversation text
4. Handle `attempt_completion` to end the session

The metadata structure allows for rich UI updates and progress tracking during action execution.
