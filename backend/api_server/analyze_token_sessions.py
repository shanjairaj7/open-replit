#!/usr/bin/env python3
"""
Token Session Analysis Script

Analyzes the JSON audit log to calculate average total tokens per session vs
average satisfaction ratings over time across multiple chat stream sessions.
Creates line chart visualization showing trends over time.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

class TokenSessionAnalyzer:
    """Analyzes token usage audit log and creates session-based metrics"""
    
    def __init__(self, audit_log_path: str = None):
        """Initialize analyzer with audit log path"""
        if audit_log_path is None:
            audit_log_path = os.path.join(os.path.dirname(__file__), "logs", "token_usage_audit.json")
        
        self.audit_log_path = audit_log_path
        print(f"📊 Token session analyzer initialized")
        print(f"📁 Audit log path: {audit_log_path}")
    
    def load_audit_data(self) -> List[Dict]:
        """Load audit log entries from JSON file"""
        try:
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded {len(data)} audit entries from log")
                return data
            else:
                print(f"❌ Audit log file not found: {self.audit_log_path}")
                return []
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"❌ Failed to load audit data: {e}")
            return []
    
    def extract_sessions(self, audit_data: List[Dict]) -> List[Dict]:
        """
        Extract complete sessions from audit data using session boundaries
        Returns list of session summaries with start/end tokens and duration
        """
        sessions = []
        session_map = {}  # session_id -> session data
        
        for entry in audit_data:
            session_id = entry.get('session_id')
            if not session_id:
                continue
            
            project_id = entry.get('project_id', 'unknown')
            timestamp = entry.get('timestamp')
            session_boundary = entry.get('session_boundary')
            
            # Initialize session if not exists
            if session_id not in session_map:
                session_map[session_id] = {
                    'session_id': session_id,
                    'project_id': project_id,
                    'start_time': None,
                    'end_time': None,
                    'start_tokens': 0,
                    'end_tokens': 0,
                    'entries': []
                }
            
            session = session_map[session_id]
            session['entries'].append(entry)
            
            # Handle session boundaries
            if session_boundary == 'start':
                session['start_time'] = timestamp
                session['start_tokens'] = entry.get('total_tokens', 0)
            elif session_boundary == 'end':
                session['end_time'] = timestamp
                session['end_tokens'] = entry.get('total_tokens', 0)
        
        # Convert to session summaries
        for session_id, session_data in session_map.items():
            if session_data['start_time'] and session_data['end_time']:
                # Calculate session token usage (delta from start to end)
                session_tokens = session_data['end_tokens'] - session_data['start_tokens']
                
                # Calculate duration
                start_dt = datetime.fromisoformat(session_data['start_time'])
                end_dt = datetime.fromisoformat(session_data['end_time'])
                duration_seconds = (end_dt - start_dt).total_seconds()
                
                session_summary = {
                    'session_id': session_id,
                    'project_id': session_data['project_id'],
                    'start_time': session_data['start_time'],
                    'end_time': session_data['end_time'],
                    'session_tokens': max(0, session_tokens),  # Ensure non-negative
                    'duration_seconds': duration_seconds,
                    'entry_count': len(session_data['entries']),
                    # TODO: Add satisfaction rating mechanism
                    'satisfaction_rating': 5.0  # Default rating for now
                }
                
                sessions.append(session_summary)
        
        print(f"📈 Extracted {len(sessions)} complete sessions from audit data")
        return sessions
    
    def calculate_time_series_averages(self, sessions: List[Dict], time_window_hours: int = 24) -> Tuple[List[datetime], List[float], List[float]]:
        """
        Calculate average tokens and satisfaction over time windows
        
        Args:
            sessions: List of session summaries
            time_window_hours: Hours per time window for averaging
            
        Returns:
            Tuple of (timestamps, avg_tokens, avg_satisfaction)
        """
        if not sessions:
            return [], [], []
        
        # Sort sessions by start time
        sessions.sort(key=lambda s: s['start_time'])
        
        # Group sessions into time windows
        time_windows = defaultdict(list)
        
        for session in sessions:
            start_dt = datetime.fromisoformat(session['start_time'])
            # Round down to time window boundary
            window_start = start_dt.replace(minute=0, second=0, microsecond=0)
            # Group by time_window_hours intervals
            hours_since_midnight = window_start.hour
            window_group = hours_since_midnight // time_window_hours
            window_key = window_start.replace(hour=window_group * time_window_hours)
            
            time_windows[window_key].append(session)
        
        # Calculate averages for each time window
        timestamps = []
        avg_tokens = []
        avg_satisfaction = []
        
        for window_time in sorted(time_windows.keys()):
            window_sessions = time_windows[window_time]
            
            # Calculate averages
            total_tokens = sum(s['session_tokens'] for s in window_sessions)
            total_satisfaction = sum(s['satisfaction_rating'] for s in window_sessions)
            session_count = len(window_sessions)
            
            avg_tokens_per_session = total_tokens / session_count if session_count > 0 else 0
            avg_satisfaction_rating = total_satisfaction / session_count if session_count > 0 else 0
            
            timestamps.append(window_time)
            avg_tokens.append(avg_tokens_per_session)
            avg_satisfaction.append(avg_satisfaction_rating)
            
            print(f"⏰ {window_time.strftime('%Y-%m-%d %H:%M')}: {session_count} sessions, "
                  f"Avg tokens: {avg_tokens_per_session:.1f}, Avg satisfaction: {avg_satisfaction_rating:.1f}")
        
        return timestamps, avg_tokens, avg_satisfaction
    
    def create_efficiency_bars(self, sessions: List[Dict], save_path: str = "efficiency_bars.png"):
        """Create bar chart showing efficiency (avg_tokens / avg_satisfaction) over time intervals"""
        
        if not sessions:
            print("❌ No sessions available for visualization")
            return
        
        # Sort sessions chronologically
        sessions.sort(key=lambda s: s['start_time'])
        
        # Calculate time span and determine interval
        first_date = datetime.fromisoformat(sessions[0]['start_time'])
        last_date = datetime.fromisoformat(sessions[-1]['start_time'])
        time_span_days = (last_date - first_date).days + 1
        
        # Determine interval based on data span
        if time_span_days <= 7:
            interval_days = 1  # Daily
            interval_name = "Daily"
        elif time_span_days <= 30:
            interval_days = 3  # Every 3 days
            interval_name = "3-Day"
        elif time_span_days <= 90:
            interval_days = 7  # Weekly
            interval_name = "Weekly"
        else:
            interval_days = 30  # Monthly
            interval_name = "Monthly"
        
        print(f"📊 Data span: {time_span_days} days, using {interval_name} intervals")
        
        # Group sessions by intervals
        from collections import defaultdict
        intervals = defaultdict(list)
        
        for session in sessions:
            session_date = datetime.fromisoformat(session['start_time'])
            days_from_start = (session_date - first_date).days
            interval_key = (days_from_start // interval_days) * interval_days
            intervals[interval_key].append(session)
        
        # Calculate efficiency for each interval
        interval_labels = []
        efficiency_values = []
        
        for interval_start in sorted(intervals.keys()):
            interval_sessions = intervals[interval_start]
            
            # Calculate averages for this interval
            total_tokens = sum(s['session_tokens'] for s in interval_sessions)
            total_satisfaction = sum(s['satisfaction_rating'] for s in interval_sessions)
            count = len(interval_sessions)
            
            avg_tokens = total_tokens / count
            avg_satisfaction = total_satisfaction / count
            
            # Efficiency = avg_tokens / avg_satisfaction (lower is better)
            efficiency = avg_tokens / avg_satisfaction if avg_satisfaction > 0 else float('inf')
            
            # Create label
            interval_date = first_date + timedelta(days=interval_start)
            if interval_days == 1:
                label = interval_date.strftime('%m-%d')
            elif interval_days <= 7:
                end_date = min(interval_date + timedelta(days=interval_days-1), last_date)
                label = f"{interval_date.strftime('%m-%d')} to {end_date.strftime('%m-%d')}"
            else:
                label = interval_date.strftime('%m-%d')
            
            interval_labels.append(label)
            efficiency_values.append(efficiency)
            
            print(f"📈 {label}: {count} sessions, {avg_tokens:.0f} avg tokens, {avg_satisfaction:.1f} avg satisfaction, efficiency: {efficiency:.0f}")
        
        if not efficiency_values:
            print("❌ No valid efficiency data")
            return
        
        # Create bar chart
        plt.figure(figsize=(12, 6))
        bars = plt.bar(interval_labels, efficiency_values, color='steelblue', alpha=0.7)
        
        plt.xlabel('Time Period')
        plt.ylabel('Efficiency (Avg Tokens / Avg Satisfaction)')
        plt.title(f'{interval_name} Efficiency - Lower is Better')
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars with tokens and satisfaction
        interval_data = []
        for interval_start in sorted(intervals.keys()):
            interval_sessions = intervals[interval_start]
            total_tokens = sum(s['session_tokens'] for s in interval_sessions)
            total_satisfaction = sum(s['satisfaction_rating'] for s in interval_sessions)
            count = len(interval_sessions)
            avg_tokens = total_tokens / count
            avg_satisfaction = total_satisfaction / count
            interval_data.append((avg_tokens, avg_satisfaction))
        
        for bar, value, (avg_tokens, avg_satisfaction) in zip(bars, efficiency_values, interval_data):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(efficiency_values)*0.01,
                    f'{value:.0f}\n({avg_tokens:.0f}t, {avg_satisfaction:.1f}s)', 
                    ha='center', va='bottom', fontsize=9)
        
        # Calculate improvement
        if len(efficiency_values) >= 2:
            first_efficiency = efficiency_values[0]
            last_efficiency = efficiency_values[-1]
            improvement = ((first_efficiency - last_efficiency) / first_efficiency) * 100 if first_efficiency > 0 else 0
            status = "IMPROVED" if improvement > 0 else "DECLINED" if improvement < 0 else "UNCHANGED"
            
            plt.text(0.02, 0.98, f'{status}: {improvement:+.1f}%', transform=plt.gca().transAxes, 
                    fontsize=12, verticalalignment='top', 
                    bbox=dict(boxstyle='round', facecolor='lightgreen' if improvement > 0 else 'lightcoral'))
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Bar chart saved to: {save_path}")
        
        return plt.gcf()
    
    def run_analysis(self, chart_path: str = None):
        """Run complete analysis and generate efficiency chart"""
        
        print("🔍 Loading audit data...")
        audit_data = self.load_audit_data()
        
        if not audit_data:
            print("❌ No audit data found. Make sure token tracking sessions have been recorded.")
            return
        
        print("📊 Extracting sessions from audit data...")
        sessions = self.extract_sessions(audit_data)
        
        if not sessions:
            print("❌ No complete sessions found. Make sure sessions have both start and end boundaries.")
            return
        
        # Generate efficiency visualization
        chart_path = chart_path or f"efficiency_bars_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.create_efficiency_bars(sessions, chart_path)
        
        # Print summary
        print("\n" + "="*60)
        print("📈 EFFICIENCY ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total Sessions Analyzed: {len(sessions)}")
        
        if sessions:
            avg_tokens = sum(s['session_tokens'] for s in sessions) / len(sessions)
            avg_satisfaction = sum(s['satisfaction_rating'] for s in sessions) / len(sessions)
            overall_efficiency = avg_satisfaction / (avg_tokens / 1000) if avg_tokens > 0 else 0
            
            print(f"Average Tokens per Session: {avg_tokens:.1f}")
            print(f"Average Satisfaction: {avg_satisfaction:.1f}/10")
            print(f"Overall Efficiency: {overall_efficiency:.2f} satisfaction per 1K tokens")
        print("="*60)


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze token usage sessions and create line chart')
    parser.add_argument('--audit-log', help='Path to token usage audit log JSON file')
    parser.add_argument('--chart', help='Output path for chart (optional)')
    
    args = parser.parse_args()
    
    analyzer = TokenSessionAnalyzer(args.audit_log)
    analyzer.run_analysis(args.chart)


if __name__ == "__main__":
    main()