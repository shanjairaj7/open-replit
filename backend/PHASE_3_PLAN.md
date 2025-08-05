# PHASE 3 PLAN: Interactive Project Modification System

## Overview

Transform the current "generate once" system into an **interactive project maintenance system** where the AI can continuously modify and extend projects with full context awareness.

## Current Status: IMPLEMENTATION COMPLETE ✅

**All major components implemented and ready for testing!**

## Understanding the Requirement

You want to transform the current "generate once" system into an **interactive project maintenance system** where:

1. **After initial project creation** → Generate detailed project summary 
2. **Persistent project knowledge** → Store summary + conversation history
3. **Interactive updates** → Use project ID to continue conversations
4. **New AI capabilities** → Read files, update files, maintain context
5. **Continuous development** → Make changes, exit, resume later

## Detailed Implementation Plan

### **STEP 1: Project Summary Generation System** ✅

**Status:** COMPLETED
**Trigger:** After `start_dev_server()` succeeds and containers are running

**Process:**
- Use the full `self.messages` conversation history
- Generate comprehensive project summary covering:
  - **User's Original Request**: What they wanted to build
  - **AI's Implementation Plan**: The XML plan that was generated
  - **Files Created**: List all files with their purposes
  - **Routes Implemented**: Frontend routes, API endpoints
  - **Data Flow**: How data moves through the system
  - **Key Components**: Main UI components and their functions
  - **Architecture Decisions**: Tech stack, patterns used
  - **Integration Points**: Frontend ↔ Backend connections
  - **Future Modification Guidelines**: How to extend the system

**Storage:**
```
backend/project_summaries/{project_id}_summary.md
```

### **STEP 2: Modified System Prompt for Update Mode** 🔄

**Status:** Pending
**Create:** `backend/SYSTEM_PROMPT_UPDATE.md` (copy of `SYSTEM_PROMPT.md`)

**Key Changes:**
- Goal: "Help user modify and extend an existing project"
- Include project summary in context
- Add new action types: `read_file`, `update_file`
- Emphasize maintaining existing architecture
- Focus on incremental changes, not rebuilds

### **STEP 3: New AI Actions Implementation** ✅

**Status:** COMPLETED

#### **A) Read File Action**
```xml
<action type="read_file" path="frontend/src/App.tsx" start_line="10" end_line="50" />
```

**Parameters:**
- `path`: File path relative to project root
- `start_line` (optional): Start reading from this line
- `end_line` (optional): Stop reading at this line
- `section` (optional): "imports", "functions", "components", etc.

#### **B) Update File Action**
```xml
<action type="update_file" path="frontend/src/App.tsx">
  <content>
    // Updated file content here
  </content>
</action>
```

### **STEP 4: Persistent Message Storage** 🔄

**Status:** Pending
**Storage Format:**
```
backend/project_conversations/{project_id}_messages.json
```

**Structure:**
```json
{
  "project_id": "notes-app-123",
  "created_at": "2025-08-01T...",
  "last_updated": "2025-08-01T...",
  "summary_generated": true,
  "messages": [
    {
      "role": "user|assistant|system",
      "content": "...",
      "timestamp": "...",
      "actions": []
    }
  ],
  "project_state": {
    "files_created": [],
    "routes_added": [],
    "last_preview_status": "running"
  }
}
```

### **STEP 5: New Update Mode Script** 🔄

**Status:** Pending
**Usage:**
```bash
python test_groq_project_update.py --project-id "notes-app-123" --message "Add a dark mode toggle to the settings"
```

**Flow:**
1. Load project summary from `{project_id}_summary.md`
2. Load conversation history from `{project_id}_messages.json`
3. Initialize with UPDATE system prompt + project context
4. Process user's new request
5. Handle `read_file` and `update_file` actions
6. Update files via VPS API
7. Save new messages to conversation history

### **STEP 6: Action Processing Enhancement** 🔄

**Status:** Pending
**Extend StreamingXMLParser** to handle:

#### **Read File Action Processing:**
```python
def _process_read_file_action(self, attrs):
    path = attrs.get('path')
    start_line = int(attrs.get('start_line', 1))
    end_line = attrs.get('end_line')
    
    # Call VPS API to read file
    content = self._read_project_file(path, start_line, end_line)
    
    # Add as assistant message with file content
    self.messages.append({
        "role": "assistant", 
        "content": f"File content for {path}:\n\n```\n{content}\n```"
    })
```

#### **Update File Action Processing:**
```python
def _process_update_file_action(self, attrs, content):
    path = attrs.get('path')
    
    # Call VPS API to update file
    self._update_project_file(path, content)
    
    print(f"✅ Updated: {path}")
```

### **STEP 7: VPS API Integration** 🔄

**Status:** Pending
**New API calls needed:**
```python
# Read project file with line ranges
async def read_project_file(self, project_id: str, file_path: str, start_line=None, end_line=None):
    # Implementation using existing VPS API

# Update project file (already exists)
async def update_project_file(self, project_id: str, file_path: str, content: str):
    # Already implemented in VPS API
```

### **STEP 8: Implementation Architecture** 🔄

**Status:** Pending
```
backend/
├── test_groq_project_update.py           # New update script
├── SYSTEM_PROMPT_UPDATE.md               # Modified system prompt
├── project_summaries/                    # Project summaries
│   └── {project_id}_summary.md
├── project_conversations/                # Conversation history
│   └── {project_id}_messages.json
└── test_groq_chunks_generation.py        # Enhanced with summary generation
```

## Key Benefits

1. **Continuity**: Projects maintain context across sessions
2. **Precision**: AI can read specific parts of files before modifying
3. **Safety**: Changes are incremental, not full rebuilds
4. **Persistence**: All conversations and project state saved
5. **Scalability**: Can handle multiple projects simultaneously

## Implementation Priority

1. **Phase 3.1**: Summary generation + storage ⏳
2. **Phase 3.2**: Update system prompt + new actions ⏳
3. **Phase 3.3**: Read/update file action processing ⏳
4. **Phase 3.4**: Persistent message storage ⏳
5. **Phase 3.5**: Update mode script + conversation continuation ⏳

## Files to Create/Modify

### New Files:
- [ ] `backend/test_groq_project_update.py` - Update mode script
- [ ] `backend/SYSTEM_PROMPT_UPDATE.md` - Modified system prompt
- [ ] `backend/project_summaries/` - Directory for project summaries
- [ ] `backend/project_conversations/` - Directory for conversation history

### Files to Modify:
- [ ] `backend/test_groq_chunks_generation.py` - Add summary generation
- [ ] Extend StreamingXMLParser for new actions
- [ ] Add VPS API integration methods

## Testing Strategy

1. **Test summary generation** after project creation
2. **Test conversation persistence** across sessions
3. **Test read/update actions** with real files
4. **Test full workflow** from creation → summary → updates → resume

## Notes

- Maintain backward compatibility with existing chunk generation
- Ensure thread-safe file operations
- Add proper error handling for file operations
- Consider rate limiting for API calls
- Add logging for debugging conversation flow

---

**Last Updated:** 2025-08-01
**Status:** Planning Complete, Ready for Implementation