#!/usr/bin/env python3
"""
Stream Session Token Tracker

Tracks token usage for complete /chat/stream API calls from start to finish.
Records data for analysis of tokens-per-session vs satisfaction metrics.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class StreamSessionLog:
    """Log entry for a complete stream session"""
    session_id: str
    project_id: str
    conversation_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    
    # Token usage for the complete session
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    
    # Cost calculations (based on tokens folder methodology)
    estimated_cost_usd: float
    cost_per_token: float = 0.00000089  # From tokens/README.md
    
    # User satisfaction rating (1-10, default 5)
    satisfaction_rating: float = 5.0
    
    # Additional metadata
    message_preview: str = ""  # First 100 chars of user message
    mode: str = "create"  # "create", "update", "create_from_pool", etc.
    iterations_count: int = 0  # Number of coder iterations
    actions_executed: int = 0  # Number of actions executed
    
    # Session tracking
    token_updates_received: int = 0  # Number of token updates during session


class StreamSessionTracker:
    """Tracks complete stream sessions for token usage analysis"""
    
    def __init__(self, log_file_path: str = None):
        """Initialize tracker with log file path"""
        if log_file_path is None:
            log_file_path = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                "logs", 
                "stream_session_logs.json"
            )
        
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Active sessions being tracked
        self.active_sessions: Dict[str, Dict] = {}
        
        # Ensure log file exists
        if not self.log_file_path.exists():
            self._save_logs([])
    
    def start_session(self, session_id: str, project_id: str, conversation_id: str, 
                     message: str = "", mode: str = "create") -> str:
        """Start tracking a new stream session"""
        
        start_time = datetime.now()
        
        session_data = {
            "session_id": session_id,
            "project_id": project_id,
            "conversation_id": conversation_id,
            "start_time": start_time.isoformat(),
            "mode": mode,
            "message_preview": message[:100],
            
            # Token tracking - will be updated throughout session
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            
            # Session metrics - will be updated
            "iterations_count": 0,
            "actions_executed": 0,
            "token_updates_received": 0,
            
            # Internal tracking
            "_start_time_obj": start_time,
            "_initial_token_state": None,
        }
        
        self.active_sessions[session_id] = session_data
        print(f"🎯 StreamSessionTracker: Started session {session_id} for project {project_id}")
        
        return session_id
    
    def update_session_tokens(self, session_id: str, input_tokens: int, 
                            output_tokens: int, total_tokens: int = None):
        """Update token counts for an active session"""
        
        if session_id not in self.active_sessions:
            print(f"⚠️ StreamSessionTracker: Session {session_id} not found for token update")
            return
        
        if total_tokens is None:
            total_tokens = input_tokens + output_tokens
        
        session = self.active_sessions[session_id]
        
        # Store initial state for delta calculation
        if session["_initial_token_state"] is None:
            session["_initial_token_state"] = {
                "input": input_tokens,
                "output": output_tokens, 
                "total": total_tokens
            }
        
        # Update current totals (these are cumulative from token tracker)
        session["total_input_tokens"] = input_tokens
        session["total_output_tokens"] = output_tokens
        session["total_tokens"] = total_tokens
        session["token_updates_received"] += 1
        
        print(f"💰 StreamSessionTracker: Updated session {session_id} tokens: {total_tokens:,} total")
    
    def update_session_metrics(self, session_id: str, iterations: int = None, 
                             actions: int = None):
        """Update session performance metrics"""
        
        if session_id not in self.active_sessions:
            print(f"⚠️ StreamSessionTracker: Session {session_id} not found for metrics update")
            return
        
        session = self.active_sessions[session_id]
        
        if iterations is not None:
            session["iterations_count"] = iterations
        
        if actions is not None:
            session["actions_executed"] = actions
        
        print(f"📊 StreamSessionTracker: Updated session {session_id} metrics - "
              f"iterations: {session['iterations_count']}, actions: {session['actions_executed']}")
    
    def end_session(self, session_id: str, satisfaction_rating: float = 5.0) -> Optional[StreamSessionLog]:
        """End tracking for a session and save the log"""
        
        if session_id not in self.active_sessions:
            print(f"⚠️ StreamSessionTracker: Session {session_id} not found for ending")
            return None
        
        session = self.active_sessions[session_id]
        end_time = datetime.now()
        duration = (end_time - session["_start_time_obj"]).total_seconds()
        
        # Calculate session-specific token usage (delta from start)
        initial_state = session["_initial_token_state"] or {"input": 0, "output": 0, "total": 0}
        
        session_input_tokens = session["total_input_tokens"] - initial_state["input"]
        session_output_tokens = session["total_output_tokens"] - initial_state["output"]  
        session_total_tokens = session["total_tokens"] - initial_state["total"]
        
        # Ensure non-negative values
        session_input_tokens = max(0, session_input_tokens)
        session_output_tokens = max(0, session_output_tokens)
        session_total_tokens = max(0, session_total_tokens)
        
        # Calculate cost based on tokens folder methodology
        cost_per_token = 0.00000089  # From tokens/README.md line 3
        estimated_cost = session_total_tokens * cost_per_token
        
        # Create session log
        session_log = StreamSessionLog(
            session_id=session_id,
            project_id=session["project_id"],
            conversation_id=session["conversation_id"],
            start_time=session["start_time"],
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            
            total_input_tokens=session_input_tokens,
            total_output_tokens=session_output_tokens,
            total_tokens=session_total_tokens,
            
            estimated_cost_usd=estimated_cost,
            satisfaction_rating=satisfaction_rating,
            
            message_preview=session["message_preview"],
            mode=session["mode"],
            iterations_count=session["iterations_count"],
            actions_executed=session["actions_executed"],
            token_updates_received=session["token_updates_received"]
        )
        
        # Save to log file
        self._append_log(session_log)
        
        # Clean up active session
        del self.active_sessions[session_id]
        
        print(f"🏁 StreamSessionTracker: Ended session {session_id}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Session tokens: {session_total_tokens:,} (Input: {session_input_tokens:,}, Output: {session_output_tokens:,})")
        print(f"   Estimated cost: ${estimated_cost:.6f}")
        print(f"   Satisfaction: {satisfaction_rating}/10")
        
        return session_log
    
    def get_session_logs(self) -> List[StreamSessionLog]:
        """Load all session logs from file"""
        try:
            with open(self.log_file_path, 'r') as f:
                logs_data = json.load(f)
            
            return [StreamSessionLog(**log) for log in logs_data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _append_log(self, session_log: StreamSessionLog):
        """Append a new log entry to the file"""
        logs = self.get_session_logs()
        logs.append(session_log)
        
        # Convert to dicts for JSON serialization
        logs_data = [asdict(log) for log in logs]
        
        self._save_logs(logs_data)
    
    def _save_logs(self, logs_data: List[Dict]):
        """Save logs to JSON file"""
        try:
            with open(self.log_file_path, 'w') as f:
                json.dump(logs_data, f, indent=2)
        except Exception as e:
            print(f"❌ StreamSessionTracker: Failed to save logs: {e}")


# Global instance for easy access
_global_tracker: Optional[StreamSessionTracker] = None

def get_stream_session_tracker() -> StreamSessionTracker:
    """Get or create global stream session tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = StreamSessionTracker()
    return _global_tracker


# Convenience functions for integration
def start_stream_session(conversation_id: str, project_id: str, message: str = "", mode: str = "create") -> str:
    """Start tracking a stream session - returns session_id"""
    session_id = f"session_{conversation_id}_{uuid.uuid4().hex[:8]}"
    tracker = get_stream_session_tracker()
    return tracker.start_session(session_id, project_id, conversation_id, message, mode)

def update_stream_session_tokens(session_id: str, input_tokens: int, output_tokens: int, total_tokens: int = None):
    """Update token counts for active session"""
    tracker = get_stream_session_tracker()
    tracker.update_session_tokens(session_id, input_tokens, output_tokens, total_tokens)

def update_stream_session_metrics(session_id: str, iterations: int = None, actions: int = None):
    """Update session metrics"""
    tracker = get_stream_session_tracker()
    tracker.update_session_metrics(session_id, iterations, actions)

def end_stream_session(session_id: str, satisfaction_rating: float = 5.0) -> Optional[StreamSessionLog]:
    """End stream session tracking"""
    tracker = get_stream_session_tracker()
    return tracker.end_session(session_id, satisfaction_rating)


if __name__ == "__main__":
    # Test the tracker
    print("🧪 Testing StreamSessionTracker...")
    
    tracker = StreamSessionTracker("/tmp/test_stream_logs.json")
    
    # Simulate session
    session_id = tracker.start_session("test-session", "proj-123", "conv-456", "Test message", "create")
    tracker.update_session_tokens(session_id, 100, 200, 300)
    tracker.update_session_metrics(session_id, iterations=3, actions=5)
    tracker.update_session_tokens(session_id, 150, 350, 500)  # Simulate more token usage
    
    log_entry = tracker.end_session(session_id, satisfaction_rating=8.5)
    
    print(f"✅ Test completed. Session log: {log_entry}")
    
    # Test log retrieval
    logs = tracker.get_session_logs()
    print(f"✅ Retrieved {len(logs)} logs from file")