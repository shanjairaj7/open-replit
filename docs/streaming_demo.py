#!/usr/bin/env python3
"""
Bolt.diy Streaming Architecture Demo
This Python script mimics the streaming, parsing, and UI update behavior
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import os
import tempfile
import shutil
import subprocess
from datetime import datetime

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ActionType(Enum):
    FILE = "file"
    SHELL = "shell"
    START = "start"

@dataclass
class BoltAction:
    type: ActionType
    content: str = ""
    file_path: Optional[str] = None
    
@dataclass
class BoltArtifact:
    id: str
    title: str
    actions: List[BoltAction] = field(default_factory=list)

@dataclass
class ParserState:
    position: int = 0
    inside_artifact: bool = False
    inside_action: bool = False
    current_artifact: Optional[BoltArtifact] = None
    current_action: Optional[BoltAction] = None
    buffer: str = ""

class StreamingMessageParser:
    """Mimics the frontend StreamingMessageParser"""
    
    def __init__(self, callbacks: Dict[str, Callable]):
        self.callbacks = callbacks
        self.state = ParserState()
        
    def parse(self, chunk: str) -> str:
        """Parse incoming chunk and trigger callbacks"""
        self.state.buffer += chunk
        output = ""
        
        # Check for artifact open
        artifact_match = re.search(r'<boltArtifact\s+id="([^"]+)"\s+title="([^"]+)">', self.state.buffer)
        if artifact_match and not self.state.inside_artifact:
            self.state.inside_artifact = True
            self.state.current_artifact = BoltArtifact(
                id=artifact_match.group(1),
                title=artifact_match.group(2)
            )
            if 'on_artifact_open' in self.callbacks:
                self.callbacks['on_artifact_open'](self.state.current_artifact)
            # Remove processed part
            self.state.buffer = self.state.buffer[artifact_match.end():]
            
        # Check for action open
        if self.state.inside_artifact and not self.state.inside_action:
            action_match = re.search(r'<boltAction\s+type="([^"]+)"(?:\s+filePath="([^"]+)")?>', self.state.buffer)
            if action_match:
                self.state.inside_action = True
                action_type = ActionType(action_match.group(1))
                file_path = action_match.group(2) if action_match.group(2) else None
                
                self.state.current_action = BoltAction(
                    type=action_type,
                    file_path=file_path
                )
                
                if 'on_action_open' in self.callbacks:
                    self.callbacks['on_action_open'](self.state.current_action)
                    
                self.state.buffer = self.state.buffer[action_match.end():]
        
        # Check for action close
        if self.state.inside_action:
            close_match = re.search(r'(.*?)</boltAction>', self.state.buffer, re.DOTALL)
            if close_match:
                # Add remaining content
                self.state.current_action.content = close_match.group(1)
                
                if 'on_action_close' in self.callbacks:
                    self.callbacks['on_action_close'](self.state.current_action)
                
                self.state.inside_action = False
                self.state.current_action = None
                self.state.buffer = self.state.buffer[close_match.end():]
            else:
                # Stream content for file actions
                if self.state.current_action.type == ActionType.FILE and len(self.state.buffer) > 0:
                    self.state.current_action.content = self.state.buffer
                    if 'on_action_stream' in self.callbacks:
                        self.callbacks['on_action_stream'](self.state.current_action)
                    self.state.buffer = ""
        
        # Check for artifact close
        if self.state.inside_artifact:
            if '</boltArtifact>' in self.state.buffer:
                if 'on_artifact_close' in self.callbacks:
                    self.callbacks['on_artifact_close'](self.state.current_artifact)
                self.state.inside_artifact = False
                self.state.current_artifact = None
                self.state.buffer = ""
                
        return output

class WorkbenchSimulator:
    """Simulates the workbench store and UI updates"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="bolt_demo_")
        self.files = {}
        self.terminal_output = []
        print(f"{Colors.GREEN}Created temp workspace: {self.temp_dir}{Colors.ENDC}")
        
    def __del__(self):
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def add_artifact(self, artifact: BoltArtifact):
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}📦 Artifact: {artifact.title}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
    def add_file_action(self, action: BoltAction):
        print(f"\n{Colors.BLUE}📄 Creating file: {action.file_path}{Colors.ENDC}")
        self.files[action.file_path] = ""
        
    def stream_file_content(self, action: BoltAction):
        # Simulate real-time file editing
        self.files[action.file_path] = action.content
        # Show last line being written
        lines = action.content.split('\n')
        if lines:
            last_line = lines[-1] if lines[-1] else lines[-2] if len(lines) > 1 else ""
            if last_line:
                print(f"{Colors.CYAN}  Writing: {last_line[:50]}{'...' if len(last_line) > 50 else ''}{Colors.ENDC}", end='\r')
        
    def save_file(self, action: BoltAction):
        full_path = os.path.join(self.temp_dir, action.file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(action.content)
            
        print(f"\n{Colors.GREEN}✅ Saved: {action.file_path} ({len(action.content)} bytes){Colors.ENDC}")
        
        # Show file preview
        lines = action.content.split('\n')
        print(f"{Colors.YELLOW}  Preview:{Colors.ENDC}")
        for i, line in enumerate(lines[:5]):
            print(f"  {i+1:3d} | {line}")
        if len(lines) > 5:
            print(f"  ... | ({len(lines) - 5} more lines)")
            
    def run_shell_command(self, action: BoltAction):
        print(f"\n{Colors.BLUE}🚀 Running: {action.content}{Colors.ENDC}")
        
        # Simulate command execution
        if action.content.startswith('npm install'):
            print(f"{Colors.CYAN}  Installing dependencies...{Colors.ENDC}")
            time.sleep(1)  # Simulate install time
            print(f"{Colors.GREEN}  ✓ Dependencies installed{Colors.ENDC}")
        else:
            try:
                # Actually run the command in temp dir
                result = subprocess.run(
                    action.content, 
                    shell=True, 
                    cwd=self.temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    print(f"{Colors.GREEN}  Output: {result.stdout.strip()}{Colors.ENDC}")
                if result.stderr:
                    print(f"{Colors.RED}  Error: {result.stderr.strip()}{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.YELLOW}  Simulated execution (actual command skipped){Colors.ENDC}")
                
    def start_dev_server(self, action: BoltAction):
        print(f"\n{Colors.GREEN}🌐 Starting dev server: {action.content}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Preview available at: http://localhost:3000{Colors.ENDC}")
        print(f"{Colors.YELLOW}  (This is a simulation - no actual server started){Colors.ENDC}")

class AIStreamSimulator:
    """Simulates the AI streaming response"""
    
    def __init__(self):
        self.sample_response = '''<boltArtifact id="react-counter" title="React Counter App">
<boltAction type="file" filePath="package.json">
{
  "name": "react-counter-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
</boltAction>
<boltAction type="file" filePath="src/App.tsx">
import React, { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);
  
  return (
    <div style={{ textAlign: 'center', padding: '2rem' }}>
      <h1>React Counter</h1>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
      <button onClick={() => setCount(count - 1)}>
        Decrement
      </button>
    </div>
  );
}
</boltAction>
<boltAction type="file" filePath="src/main.tsx">
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
</boltAction>
<boltAction type="shell">npm install</boltAction>
<boltAction type="start">npm run dev</boltAction>
</boltArtifact>'''
        
    async def stream_response(self, chunk_size: int = 10):
        """Simulate streaming response chunk by chunk"""
        for i in range(0, len(self.sample_response), chunk_size):
            chunk = self.sample_response[i:i + chunk_size]
            # Simulate the SSE format
            escaped = json.dumps(chunk)[1:-1]  # Remove quotes
            yield f'0:"{escaped}"'
            await asyncio.sleep(0.05)  # Simulate network delay

async def main():
    print(f"{Colors.BOLD}{Colors.HEADER}Bolt.diy Streaming Architecture Demo{Colors.ENDC}")
    print(f"{Colors.CYAN}This demonstrates how streaming, parsing, and UI updates work{Colors.ENDC}\n")
    
    # Initialize components
    workbench = WorkbenchSimulator()
    ai_simulator = AIStreamSimulator()
    
    # Setup parser with callbacks
    parser = StreamingMessageParser({
        'on_artifact_open': lambda artifact: workbench.add_artifact(artifact),
        'on_artifact_close': lambda artifact: print(f"\n{Colors.GREEN}✨ Artifact complete!{Colors.ENDC}"),
        'on_action_open': lambda action: (
            workbench.add_file_action(action) if action.type == ActionType.FILE else None
        ),
        'on_action_stream': lambda action: workbench.stream_file_content(action),
        'on_action_close': lambda action: (
            workbench.save_file(action) if action.type == ActionType.FILE else
            workbench.run_shell_command(action) if action.type == ActionType.SHELL else
            workbench.start_dev_server(action) if action.type == ActionType.START else None
        )
    })
    
    # Simulate streaming
    print(f"{Colors.YELLOW}Starting AI stream simulation...{Colors.ENDC}\n")
    
    async for sse_chunk in ai_simulator.stream_response():
        # Extract content from SSE format
        match = re.match(r'^0:"(.*)"$', sse_chunk)
        if match:
            content = match.group(1)
            # Unescape
            content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            # Parse the chunk
            parser.parse(content)
            
    print(f"\n\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}✅ Streaming complete!{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Files created in: {workbench.temp_dir}{Colors.ENDC}")
    
    # List created files
    print(f"\n{Colors.CYAN}📁 File Structure:{Colors.ENDC}")
    for root, dirs, files in os.walk(workbench.temp_dir):
        level = root.replace(workbench.temp_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{sub_indent}{file}')

if __name__ == "__main__":
    asyncio.run(main())