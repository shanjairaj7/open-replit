Complete Flow: Prompt Input → AI Response → File Generation → Preview

STEP 1: Prompt Input & UI State

What happens when you type:

1. Chat Input Component (/app/components/chat/ChatBox.tsx):
   - TextArea captures your input
   - File uploads (images/PDFs) are processed
   - Model selection (GPT-4, Claude, etc.) is stored
   - Send button triggers the flow

2. UI State Changes:
   - Chat input gets disabled
   - Streaming indicator appears
   - "Stop" button becomes available
   - Loading animations start

STEP 2: Request Processing & AI Pipeline

API Route Handler (/app/routes/api.chat.ts):

1. Request Parsing:
   - Extracts messages, files, model settings from request
   - Gets API keys from cookies
   - Initializes streaming response

2. Context Optimization:
   - If many files exist, AI selects only relevant files
   - Creates conversation summary for token efficiency
   - File selection happens via selectContext() function

3. AI Provider Selection:
   - Based on your model choice (GPT-4, Claude, etc.)
   - API keys are validated
   - Provider-specific configurations applied

STEP 3: AI Response Streaming

Stream Processing:

1. AI API Call:
   - Prompt sent to chosen AI provider (OpenAI, Anthropic, etc.)
   - Response streams back in real-time chunks
   - Each chunk immediately sent to UI

2. Response Parsing:
   - AI response parsed for different action types:
     - Text responses (explanations)
     - File operations (create, edit, delete)
     - Terminal commands
     - Tool invocations

3. Real-time UI Updates:
   - Message Display: Streaming text appears character by character
   - Action Indicators: Shows when AI is "Creating file...", "Running command..."
   - Progress Bars: For longer operations

STEP 4: File System Operations

File Management (/app/lib/stores/files.ts):

1. File Creation/Updates:
   - AI generates file content
   - FilesStore.saveFile() writes to WebContainer virtual file system
   - Files immediately appear in file tree UI

2. File Watching:
   - WebContainer watches for file changes
   - UI automatically updates when files change
   - Syntax highlighting applied in editor

3. Lock Management:
   - Files get "locked" during AI operations
   - Prevents user edits during AI modifications
   - Visual indicators show locked state

STEP 5: Terminal Operations

Command Execution:

1. Terminal Interface (/app/components/workbench/terminal/):
   - AI-generated commands (npm install, npm run dev)
   - Commands execute in WebContainer's virtual shell
   - Real-time output streams to terminal UI

2. Package Installation:
   - npm install actually downloads packages
   - node_modules appears in file tree
   - Dependencies become available to the app

STEP 6: Preview Generation

Live Preview System:

1. Development Server Startup:
   - AI runs npm run dev or similar
   - WebContainer starts actual dev server (Vite, Next.js, etc.)
   - Server runs on virtual localhost port

2. Preview Display:
   - Preview Pane: Shows live application
   - Hot Reload: Changes automatically refresh preview
   - Error Handling: Runtime errors displayed in UI

3. URL Generation:
   - WebContainer provides preview URLs
   - Multiple ports supported for different services
   - Real-time updates as code changes

STEP 7: UI State Management

Throughout the process:

Store Updates (Nanostores):

- chatStore: Message history, streaming state
- filesStore: File tree, content, locks
- workbenchStore: Preview state, terminal output
- themeStore: UI theme and layout

Visual Feedback:

- Progress Indicators: File creation progress
- Streaming Dots: AI thinking animation
- Code Highlighting: Syntax highlighting as files are created
- Error States: API errors, build failures
- Success States: Green checkmarks, "Ready" indicators

Complete Data Flow Diagram:

You Type Prompt
↓
ChatBox Component → API Route (/api/chat)
↓
AI Provider (OpenAI/Claude/etc)
↓
Streaming Response Parser
↓
┌─ Text Display (Messages)
├─ File Operations (FilesStore)
├─ Terminal Commands (WebContainer)
└─ Tool Invocations (MCP)
↓
WebContainer File System
↓
File Watcher → UI Updates
↓
Development Server Startup
↓
Live Preview Display

Key Files Involved:

- Chat UI: BaseChat.tsx, ChatBox.tsx, Messages.client.tsx
- API: api.chat.ts, stream-text.ts
- File System: files.ts, webcontainer/index.ts
- Preview: Workbench.client.tsx, Preview.tsx
- Stores: Various Nanostores for state management

The entire flow happens in real-time with streaming updates, so you see files being
created, commands running, and the preview updating live as the AI works!
