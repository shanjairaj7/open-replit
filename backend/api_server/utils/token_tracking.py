#!/usr/bin/env python3
"""
Token Tracking Utilities

Centralized module for handling token usage tracking and OpenRouter API integration.
Extracted from agent.py and agent_class.py to provide reusable token tracking functionality.
"""

import requests
import time
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class TokenTracker:
    """Handles token usage tracking and OpenRouter API queries"""
    
    # Default pricing configuration (can be updated based on actual OpenRouter rates)
    DEFAULT_INPUT_PRICE_PER_MILLION = 0.20   # $0.20 per 1M input tokens
    DEFAULT_OUTPUT_PRICE_PER_MILLION = 0.80  # $0.80 per 1M output tokens
    
    def __init__(self, project_id: str = None, input_price: float = None, output_price: float = None):
        """Initialize token tracker with project ID and pricing configuration"""
        self.project_id = project_id
        self.input_price_per_million = input_price or self.DEFAULT_INPUT_PRICE_PER_MILLION
        self.output_price_per_million = output_price or self.DEFAULT_OUTPUT_PRICE_PER_MILLION
        
        # Initialize token usage
        self.token_usage = {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
        
        # Set up JSON audit log file path
        self.audit_log_path = self._get_audit_log_path()
        
        # Session tracking for boundaries
        self.current_session_id = None
        self.session_start_recorded = False
        
    def initialize_token_usage(self) -> Dict[str, int]:
        """Initialize or reset token usage tracking"""
        self.token_usage = {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
        return self.token_usage.copy()
    
    def load_token_usage(self, usage_data: Dict[str, int]) -> None:
        """Load token usage from external source (e.g., cloud metadata)"""
        if usage_data and isinstance(usage_data, dict):
            self.token_usage = {
                'total_tokens': usage_data.get('total_tokens', 0),
                'prompt_tokens': usage_data.get('prompt_tokens', 0),
                'completion_tokens': usage_data.get('completion_tokens', 0)
            }
            print(f"=💰 Loaded token usage: {self.token_usage['total_tokens']:,} total tokens")
        else:
            self.initialize_token_usage()
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage"""
        return self.token_usage.copy()
    
    def update_token_usage(self, prompt_tokens: int, completion_tokens: int, 
                          total_tokens: int = None) -> Dict[str, int]:
        """Update token usage with new values"""
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
            
        old_total = self.token_usage['total_tokens']
        old_prompt = self.token_usage['prompt_tokens'] 
        old_completion = self.token_usage['completion_tokens']
        
        self.token_usage['prompt_tokens'] += prompt_tokens
        self.token_usage['completion_tokens'] += completion_tokens
        self.token_usage['total_tokens'] += total_tokens
        
        # Calculate cost estimates
        total_input_cost = (self.token_usage['prompt_tokens'] / 1_000_000) * self.input_price_per_million
        total_output_cost = (self.token_usage['completion_tokens'] / 1_000_000) * self.output_price_per_million
        total_cost = total_input_cost + total_output_cost
        
        project_info = f" [Project: {self.project_id}]" if self.project_id else ""
        print(f"=📊 Updating internal token tracking{project_info}...")
        print(f"=💰 Running Totals:")
        print(f"   Tokens: {old_total:,} -> {self.token_usage['total_tokens']:,}")
        print(f"   Input: {old_prompt:,} -> {self.token_usage['prompt_tokens']:,}")
        print(f"   Output: {old_completion:,} -> {self.token_usage['completion_tokens']:,}")
        print(f"   =-> Total Cost: ${total_cost:.6f}")
        print(f"      - Input: ${total_input_cost:.6f}")
        print(f"      - Output: ${total_output_cost:.6f}")
        
        # Log token usage update to JSON audit file
        self.log_token_usage()
        
        return self.token_usage.copy()
    
    def reset_token_tracking(self) -> Dict[str, int]:
        """Reset token tracking to start fresh count (used after summary)"""
        old_total = self.token_usage['total_tokens']
        print(f"= Resetting token count from {old_total:,} to 0")
        
        self.token_usage = {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0
        }
        return self.token_usage.copy()
    
    def should_summarize(self, threshold: int = 500000) -> bool:
        """Check if conversation should be summarized based on token count"""
        return self.token_usage['total_tokens'] >= threshold
    
    def calculate_costs(self, prompt_tokens: int, completion_tokens: int) -> Dict[str, float]:
        """Calculate cost estimates for given token counts"""
        input_cost = (prompt_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (completion_tokens / 1_000_000) * self.output_price_per_million
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': input_cost,
            'output_cost': output_cost, 
            'total_cost': total_cost,
            'input_price_per_million': self.input_price_per_million,
            'output_price_per_million': self.output_price_per_million
        }
    
    # JSON Audit Logging Methods
    
    def _get_audit_log_path(self) -> str:
        """Get path for token usage audit log JSON file"""
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "token_usage_audit.json")
    
    def _load_audit_log(self) -> List[Dict]:
        """Load existing audit log entries"""
        try:
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️ Failed to load audit log: {e}")
        return []
    
    def _save_audit_log(self, entries: List[Dict]) -> None:
        """Save audit log entries to JSON file"""
        try:
            with open(self.audit_log_path, 'w') as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save audit log: {e}")
    
    def log_token_usage(self, session_boundary: str = None, generation_id: str = None) -> None:
        """
        Log current token usage to JSON audit file
        
        Args:
            session_boundary: 'start' or 'end' to mark session boundaries, None for regular usage
            generation_id: OpenRouter generation ID if available
        """
        try:
            # Create audit entry
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'project_id': self.project_id,
                'session_id': self.current_session_id,
                'total_input_tokens': self.token_usage.get('total_input_tokens', self.token_usage.get('prompt_tokens', 0)),
                'total_output_tokens': self.token_usage.get('total_output_tokens', self.token_usage.get('completion_tokens', 0)),
                'total_tokens': self.token_usage.get('total_tokens', 0),
                'session_boundary': session_boundary,  # 'start', 'end', or None
                'generation_id': generation_id,
                'done': session_boundary == 'end'  # Mark as done if it's session end
            }
            
            # Load existing entries and append new one
            entries = self._load_audit_log()
            entries.append(audit_entry)
            
            # Save updated entries
            self._save_audit_log(entries)
            
            boundary_info = f" [{session_boundary.upper()}]" if session_boundary else ""
            project_info = f" [Project: {self.project_id}]" if self.project_id else ""
            print(f"📊 Token audit logged{boundary_info}: {audit_entry['total_tokens']:,} tokens{project_info}")
            
        except Exception as e:
            print(f"❌ Failed to log token usage: {e}")
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new session for token tracking"""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        
        self.current_session_id = session_id
        self.session_start_recorded = False
        
        # Log session start
        self.log_token_usage(session_boundary='start')
        self.session_start_recorded = True
        
        print(f"🎯 Token tracking session started: {session_id}")
        return session_id
    
    def end_session(self) -> None:
        """End current session for token tracking"""
        if self.current_session_id:
            # Log session end
            self.log_token_usage(session_boundary='end')
            print(f"🏁 Token tracking session ended: {self.current_session_id}")
            self.current_session_id = None
            self.session_start_recorded = False


class OpenRouterTokenTracker(TokenTracker):
    """Extended token tracker with OpenRouter API integration"""
    
    def __init__(self, api_key: str, project_id: str = None, input_price: float = None, output_price: float = None):
        """Initialize with OpenRouter API key and project ID"""
        super().__init__(project_id, input_price, output_price)
        self.api_key = api_key
        self.current_generation_id = None
    
    def update_token_usage(self, prompt_tokens: int, completion_tokens: int, 
                          total_tokens: int = None) -> Dict[str, int]:
        """Override to include generation_id in audit logging"""
        # Call parent method
        result = super().update_token_usage(prompt_tokens, completion_tokens, total_tokens)
        
        # Override the automatic logging to include generation_id
        # Remove the last entry and add it again with generation_id
        if hasattr(self, 'audit_log_path') and os.path.exists(self.audit_log_path):
            try:
                entries = self._load_audit_log()
                if entries:
                    # Remove the last entry added by parent method
                    last_entry = entries.pop()
                    # Add it back with generation_id
                    last_entry['generation_id'] = self.current_generation_id
                    entries.append(last_entry)
                    self._save_audit_log(entries)
            except Exception as e:
                print(f"⚠️ Failed to update audit entry with generation_id: {e}")
        
        return result
        
    def query_generation_usage(self, generation_id: str, max_retries: int = 3, 
                             base_delay: int = 2, max_delay: int = 10) -> Optional[Dict[str, Any]]:
        """
        Query usage statistics for a generation using OpenRouter API.
        Implements retry logic with exponential backoff since OpenRouter has a delay
        before generations are recorded in their system.
        """
        if not generation_id:
            print(f"-> No generation ID provided for usage query")
            return None
            
        if not self.api_key:
            print(f"-> No API key provided for OpenRouter usage query")
            return None

        project_info = f" [Project: {self.project_id}]" if self.project_id else ""
        print(f"=-> Querying usage for generation ID: {generation_id}{project_info}")
        print(f"=-> Using pricing - Input: ${self.input_price_per_million}/M, Output: ${self.output_price_per_million}/M")
        
        # Store generation_id for audit logging
        self.current_generation_id = generation_id

        for attempt in range(max_retries):
            if attempt > 0:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                print(f"= Retry attempt {attempt + 1}/{max_retries}, waiting {delay}s...")
                time.sleep(delay)

            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            try:
                response = requests.get(
                    f"https://openrouter.ai/api/v1/generation?id={generation_id}",
                    headers=headers,
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        gen_data = data['data']
                        prompt_tokens = gen_data.get('tokens_prompt', 0) or 0
                        completion_tokens = gen_data.get('tokens_completion', 0) or 0
                        total_tokens = prompt_tokens + completion_tokens

                        # Calculate cost estimates
                        costs = self.calculate_costs(prompt_tokens, completion_tokens)
                        iteration_cost = costs['total_cost']

                        print(f"\n=-> Usage Statistics (Generation {generation_id}):")
                        print(f"Total Tokens: {total_tokens:,}")
                        print(f"Prompt Tokens: {prompt_tokens:,}")
                        print(f"Completion Tokens: {completion_tokens:,}")
                        print(f"=-> This Iteration Cost (Our Estimate): ${iteration_cost:.6f}")
                        print(f"   - Input cost: ${costs['input_cost']:.6f} ({prompt_tokens:,} -> ${self.input_price_per_million}/M)")
                        print(f"   - Output cost: ${costs['output_cost']:.6f} ({completion_tokens:,} -> ${self.output_price_per_million}/M)")
                        
                        if gen_data.get('total_cost'):
                            actual_cost = gen_data.get('total_cost')
                            print(f"=-> OpenRouter Actual Cost: ${actual_cost:.6f}")
                            print(f"=-> Cost Comparison: Our ${iteration_cost:.6f} vs OpenRouter ${actual_cost:.6f}")
                            cost_diff = abs(iteration_cost - actual_cost)
                            cost_accuracy = (1 - cost_diff / max(iteration_cost, actual_cost)) * 100
                            print(f"<-> Cost Accuracy: {cost_accuracy:.2f}%")

                        # Update internal tracking
                        self.update_token_usage(prompt_tokens, completion_tokens, total_tokens)

                        return {
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens,
                            'total_tokens': total_tokens,
                            'iteration_cost': iteration_cost,
                            'total_cost_estimate': costs['total_cost'],
                            'openrouter_cost': gen_data.get('total_cost'),
                            'generation_id': generation_id,
                            'cost_accuracy': cost_accuracy if gen_data.get('total_cost') else None
                        }
                    else:
                        print(f"-> Unexpected response format: {data}")
                        if attempt == max_retries - 1:
                            break
                        continue

                elif response.status_code == 404:
                    if attempt == max_retries - 1:
                        print(f"L Generation not found after {max_retries} attempts")
                        print(f"=-> This usually means the generation ID is invalid or expired")
                        print(f"=-> Generation ID: {generation_id}")
                        break
                    else:
                        print(f"-> Generation not found yet (attempt {attempt + 1}), will retry...")
                        continue

                else:
                    print(f"-> Usage query failed ({response.status_code}): {response.text[:200]}")
                    if attempt == max_retries - 1:
                        break
                    continue

            except requests.Timeout:
                print(f"-> Request timed out (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    print(f"L All attempts timed out")
                    break
                continue

            except requests.RequestException as e:
                print(f"< Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    break
                continue

        # If we get here, all retries failed
        print(f"L Failed to query usage after {max_retries} attempts")
        print(f"=-> The generation may not be recorded yet, or there's an API issue")
        return None
    
    def extract_generation_id(self, chunk) -> Optional[str]:
        """Extract generation ID from streaming chunk"""
        if hasattr(chunk, 'id') and chunk.id:
            generation_id = chunk.id
            print(f"<-> Captured generation ID: {generation_id}")
            return generation_id
        return None
    
    def process_usage_from_response(self, response) -> Optional[Dict[str, int]]:
        """Process token usage from response object (for non-streaming calls)"""
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
            total_tokens = getattr(usage, 'total_tokens', prompt_tokens + completion_tokens)
            
            print(f"=-> Response usage: {total_tokens} tokens")
            self.update_token_usage(prompt_tokens, completion_tokens, total_tokens)
            
            return {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            }
        return None


# Convenience functions for backward compatibility
def initialize_token_usage() -> Dict[str, int]:
    """Initialize token usage dictionary"""
    return {
        'total_tokens': 0,
        'prompt_tokens': 0,
        'completion_tokens': 0
    }

def create_token_tracker(api_key: str = None, project_id: str = None, 
                        input_price: float = None, output_price: float = None) -> TokenTracker:
    """Create appropriate token tracker based on API key availability"""
    if api_key:
        return OpenRouterTokenTracker(api_key, project_id, input_price, output_price)
    else:
        return TokenTracker(project_id, input_price, output_price)

def should_summarize_conversation(token_usage: Dict[str, int], threshold: int = 500000) -> bool:
    """Check if conversation should be summarized based on token count"""
    return token_usage.get('total_tokens', 0) >= threshold

def calculate_token_costs(prompt_tokens: int, completion_tokens: int, 
                         input_price: float = TokenTracker.DEFAULT_INPUT_PRICE_PER_MILLION,
                         output_price: float = TokenTracker.DEFAULT_OUTPUT_PRICE_PER_MILLION) -> Dict[str, float]:
    """Calculate cost estimates for given token counts"""
    input_cost = (prompt_tokens / 1_000_000) * input_price
    output_cost = (completion_tokens / 1_000_000) * output_price
    total_cost = input_cost + output_cost
    
    return {
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_cost': total_cost
    }


if __name__ == "__main__":
    # Example usage
    print(">-> Token Tracking Module Test")
    
    # Basic token tracker
    tracker = TokenTracker()
    print("Basic tracker initialized:", tracker.get_token_usage())
    
    # Update usage
    tracker.update_token_usage(100, 200, 300)
    print("After update:", tracker.get_token_usage())
    
    # Test cost calculation
    costs = tracker.calculate_costs(1000, 2000)
    print("Cost calculation:", costs)
    
    # Test summarization check
    print("Should summarize:", tracker.should_summarize())
    
    print(" Token tracking module ready for use")