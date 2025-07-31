# Bolt.diy Streaming Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Streaming Protocol](#streaming-protocol)
3. [Backend Streaming Process](#backend-streaming-process)
4. [Frontend Parsing Architecture](#frontend-parsing-architecture)
5. [Action Types and Handlers](#action-types-and-handlers)
6. [Component Integration](#component-integration)
7. [Real-world Example](#real-world-example)

## Overview

Bolt.diy uses a sophisticated streaming architecture to provide real-time code generation, file creation, and command execution. The system streams AI responses character-by-character, parses them into structured actions, and updates the UI in real-time.

### Key Components:
- **Backend**: Streams raw AI responses using Server-Sent Events (SSE) format
- **Parser**: State machine that reconstructs structured data from streamed chunks
- **Workbench Store**: Manages application state and executes actions
- **WebContainer**: Browser-based Node.js runtime for file system and terminal operations

## Streaming Protocol

### Stream Format
The backend uses the AI SDK streaming protocol with numbered event types:

```
0:"text content"          # Regular text/content chunks
2:[{data}]               # Data messages (progress, etc.)
8:[{annotations}]        # Metadata/usage info
f:{"messageId":"..."}    # Message metadata
```

### Bolt Action Format
AI responses contain special XML-like tags for actions:

```xml
<boltArtifact id="unique-id" title="Project Title">
  <boltAction type="file" filePath="src/App.tsx">
    // File content here
  </boltAction>
  
  <boltAction type="shell">
    npm install react
  </boltAction>
  
  <boltAction type="start">
    npm run dev
  </boltAction>
</boltArtifact>
```

## Backend Streaming Process

### 1. Chat Service (chat_service.py)
```python
async def _process_groq_stream(self, model: str, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
    stream = await self.groq_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        max_tokens=8000
    )
    
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            # Escape and format for streaming
            escaped_content = json.dumps(content)[1:-1]
            yield f'0:"{escaped_content}"\n'
```

### 2. Streaming Response Flow
```
AI Model → Groq API → Backend → SSE Stream → Frontend
   ↓          ↓           ↓           ↓            ↓
"Hello"   chunk.delta  escape     0:"Hello"    Parser
```

## Frontend Parsing Architecture

### 1. StreamingMessageParser State Machine

The parser maintains state for each message:

```typescript
interface MessageState {
  position: number;          // Current parse position
  insideArtifact: boolean;   // Parsing artifact tag
  insideAction: boolean;     // Parsing action tag  
  currentArtifact?: BoltArtifactData;
  currentAction: BoltActionData;
  actionId: number;
}
```

### 2. Parser Callbacks

```typescript
interface ParserCallbacks {
  onArtifactOpen?: (data: ArtifactCallbackData) => void;
  onArtifactClose?: (data: ArtifactCallbackData) => void;
  onActionOpen?: (data: ActionCallbackData) => void;
  onActionStream?: (data: ActionCallbackData) => void;
  onActionClose?: (data: ActionCallbackData) => void;
}
```

### 3. Parsing Flow

```
Input: "0:<boltAction type=\"file\" filePath=\"App.tsx\">"
       "0:import React from 'react';"
       "0:</boltAction>"

Parser State Machine:
1. Detects <boltAction> → Sets insideAction = true
2. Extracts attributes → type="file", filePath="App.tsx"
3. Calls onActionOpen → UI shows new file
4. Accumulates content → "import React from 'react';"
5. Detects </boltAction> → Calls onActionClose
6. File is saved to WebContainer
```

## Action Types and Handlers

### 1. File Actions
```typescript
// Parser detects file action
onActionOpen: (data) => {
  if (data.action.type === 'file') {
    workbenchStore.addAction(data);  // Add to UI
  }
}

// Stream file content in real-time
onActionStream: (data) => {
  workbenchStore.runAction(data, true);  // Update editor
}

// Finalize file
onActionClose: (data) => {
  workbenchStore.runAction(data);  // Save to WebContainer
}
```

### 2. Shell Actions
```typescript
// Shell commands are added on close (when we have full command)
onActionClose: (data) => {
  if (data.action.type === 'shell') {
    workbenchStore.addAction(data);    // Add to action list
    workbenchStore.runAction(data);    // Execute in terminal
  }
}
```

### 3. Start Actions
```typescript
// Start development server
onActionClose: (data) => {
  if (data.action.type === 'start') {
    // Runs in WebContainer terminal with preview
    workbenchStore.runAction(data);
  }
}
```

## Component Integration

### 1. Workbench Store (`workbench.ts`)
```typescript
async _runAction(data: ActionCallbackData, isStreaming = false) {
  const action = artifact.runner.actions.get()[data.actionId];
  
  if (data.action.type === 'file') {
    const fullPath = path.join(webcontainer.workdir, data.action.filePath);
    
    // Update editor with content
    this.#editorStore.updateFile(fullPath, data.action.content);
    
    // Save to WebContainer filesystem
    if (!isStreaming) {
      await this.saveFile(fullPath);
    }
  } else {
    // Run shell or start commands
    await artifact.runner.runAction(data);
  }
}
```

### 2. Editor Store Integration
- Manages open files and tabs
- Updates file content in real-time
- Handles unsaved changes

### 3. Terminal Integration
- Executes shell commands in WebContainer
- Shows command output
- Handles start commands with preview

## Real-world Example

### AI Generates React Component:

1. **AI Response Stream**:
```
0:"<boltArtifact id=\"react-app\" title=\"React App\">\n"
0:"<boltAction type=\"file\" filePath=\"src/App.tsx\">\n"
0:"import React from 'react';\n"
0:"export default function App() {\n"
0:"  return <h1>Hello World</h1>;\n"
0:"}\n"
0:"</boltAction>\n"
0:"<boltAction type=\"shell\">npm install</boltAction>\n"
0:"<boltAction type=\"start\">npm run dev</boltAction>\n"
0:"</boltArtifact>"
```

2. **Parser Events**:
```
→ onArtifactOpen({ id: "react-app", title: "React App" })
  → Shows workbench UI
  
→ onActionOpen({ type: "file", filePath: "src/App.tsx" })
  → Creates file in file tree
  
→ onActionStream({ content: "import React..." })
  → Updates editor in real-time
  
→ onActionClose({ type: "file", content: "..." })
  → Saves file to WebContainer
  
→ onActionClose({ type: "shell", content: "npm install" })
  → Runs npm install in terminal
  
→ onActionClose({ type: "start", content: "npm run dev" })
  → Starts dev server with preview
```

3. **UI Updates**:
- File tree shows new file
- Editor opens with content
- Terminal shows npm output
- Preview pane shows running app

## State Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Backend   │────▶│   Parser    │────▶│ Workbench   │
│  Streaming  │     │State Machine│     │   Store     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   SSE Format          Callbacks            Actions
   0:"<bolt..."        onAction*          runAction()
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │WebContainer │
                                        │ FileSystem  │
                                        │  Terminal   │
                                        └─────────────┘
```