#!/usr/bin/env python3
"""
Stream Session Analysis & Visualization

Analyzes token usage vs satisfaction data from stream session logs
and creates visualizations showing average tokens per session vs satisfaction ratings.
"""

import json
import statistics
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from utils.stream_session_tracker import StreamSessionLog, get_stream_session_tracker


class StreamSessionAnalyzer:
    """Analyzes stream session data and creates visualizations"""
    
    def __init__(self, log_file_path: str = None):
        """Initialize analyzer with log file path"""
        self.tracker = get_stream_session_tracker() if log_file_path is None else None
        self.log_file_path = log_file_path
    
    def load_session_data(self) -> List[StreamSessionLog]:
        """Load all session data"""
        if self.tracker:
            return self.tracker.get_session_logs()
        
        # Load from specific file
        try:
            with open(self.log_file_path, 'r') as f:
                logs_data = json.load(f)
            return [StreamSessionLog(**log) for log in logs_data]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Failed to load session data: {e}")
            return []
    
    def calculate_session_statistics(self, sessions: List[StreamSessionLog]) -> Dict:
        """Calculate comprehensive statistics from session data"""
        if not sessions:
            return {"error": "No session data available"}
        
        # Extract metrics
        total_tokens = [s.total_tokens for s in sessions]
        input_tokens = [s.total_input_tokens for s in sessions]
        output_tokens = [s.total_output_tokens for s in sessions]
        satisfaction_ratings = [s.satisfaction_rating for s in sessions]
        durations = [s.duration_seconds for s in sessions]
        costs = [s.estimated_cost_usd for s in sessions]
        
        # Filter out zero token sessions for meaningful analysis
        meaningful_sessions = [s for s in sessions if s.total_tokens > 0]
        meaningful_tokens = [s.total_tokens for s in meaningful_sessions]
        meaningful_satisfaction = [s.satisfaction_rating for s in meaningful_sessions]
        
        stats = {
            "total_sessions": len(sessions),
            "meaningful_sessions": len(meaningful_sessions),
            "date_range": {
                "earliest": min(s.start_time for s in sessions),
                "latest": max(s.start_time for s in sessions)
            },
            
            # Token statistics
            "tokens": {
                "total_avg": statistics.mean(total_tokens) if total_tokens else 0,
                "total_median": statistics.median(total_tokens) if total_tokens else 0,
                "total_std": statistics.stdev(total_tokens) if len(total_tokens) > 1 else 0,
                "input_avg": statistics.mean(input_tokens) if input_tokens else 0,
                "output_avg": statistics.mean(output_tokens) if output_tokens else 0,
                "max_tokens": max(total_tokens) if total_tokens else 0,
                "min_tokens": min(total_tokens) if total_tokens else 0,
            },
            
            # Satisfaction statistics
            "satisfaction": {
                "avg": statistics.mean(satisfaction_ratings) if satisfaction_ratings else 0,
                "median": statistics.median(satisfaction_ratings) if satisfaction_ratings else 0,
                "std": statistics.stdev(satisfaction_ratings) if len(satisfaction_ratings) > 1 else 0,
                "max": max(satisfaction_ratings) if satisfaction_ratings else 0,
                "min": min(satisfaction_ratings) if satisfaction_ratings else 0,
            },
            
            # Performance statistics
            "performance": {
                "avg_duration_sec": statistics.mean(durations) if durations else 0,
                "avg_cost_usd": statistics.mean(costs) if costs else 0,
                "total_cost_usd": sum(costs) if costs else 0,
                "avg_tokens_per_second": statistics.mean([s.total_tokens / max(s.duration_seconds, 1) for s in meaningful_sessions]) if meaningful_sessions else 0,
            },
            
            # Correlation analysis
            "correlation": {
                "tokens_vs_satisfaction": self._calculate_correlation(meaningful_tokens, meaningful_satisfaction) if len(meaningful_sessions) > 1 else 0,
            },
            
            # Project breakdown
            "projects": self._analyze_by_projects(sessions),
            "modes": self._analyze_by_modes(sessions),
        }
        
        return stats
    
    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        try:
            return float(np.corrcoef(x_values, y_values)[0, 1])
        except:
            return 0.0
    
    def _analyze_by_projects(self, sessions: List[StreamSessionLog]) -> Dict:
        """Analyze sessions grouped by project"""
        project_groups = {}
        for session in sessions:
            pid = session.project_id
            if pid not in project_groups:
                project_groups[pid] = []
            project_groups[pid].append(session)
        
        project_stats = {}
        for pid, group in project_groups.items():
            if not group:
                continue
            project_stats[pid] = {
                "session_count": len(group),
                "avg_tokens": statistics.mean([s.total_tokens for s in group]),
                "avg_satisfaction": statistics.mean([s.satisfaction_rating for s in group]),
                "total_cost": sum([s.estimated_cost_usd for s in group]),
            }
        
        return project_stats
    
    def _analyze_by_modes(self, sessions: List[StreamSessionLog]) -> Dict:
        """Analyze sessions grouped by mode (create, update, etc.)"""
        mode_groups = {}
        for session in sessions:
            mode = session.mode
            if mode not in mode_groups:
                mode_groups[mode] = []
            mode_groups[mode].append(session)
        
        mode_stats = {}
        for mode, group in mode_groups.items():
            if not group:
                continue
            mode_stats[mode] = {
                "session_count": len(group),
                "avg_tokens": statistics.mean([s.total_tokens for s in group]),
                "avg_satisfaction": statistics.mean([s.satisfaction_rating for s in group]),
                "avg_duration": statistics.mean([s.duration_seconds for s in group]),
            }
        
        return mode_stats
    
    def create_tokens_vs_satisfaction_chart(self, sessions: List[StreamSessionLog], 
                                          save_path: str = "stream_analysis_chart.png"):
        """Create scatter plot and trend line showing tokens vs satisfaction"""
        
        # Filter meaningful sessions
        meaningful_sessions = [s for s in sessions if s.total_tokens > 0]
        
        if len(meaningful_sessions) < 2:
            print("❌ Insufficient data for visualization (need at least 2 sessions with tokens)")
            return
        
        # Extract data
        tokens = [s.total_tokens for s in meaningful_sessions]
        satisfaction = [s.satisfaction_rating for s in meaningful_sessions]
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Stream Session Analysis: Token Usage vs Satisfaction', fontsize=16, fontweight='bold')
        
        # 1. Main scatter plot with trend line
        ax1.scatter(tokens, satisfaction, alpha=0.6, s=60, c='blue', edgecolors='navy', linewidth=0.5)
        
        # Add trend line
        z = np.polyfit(tokens, satisfaction, 1)
        p = np.poly1d(z)
        ax1.plot(tokens, p(tokens), "r--", alpha=0.8, linewidth=2, label=f'Trend: y={z[0]:.2e}x+{z[1]:.2f}')
        
        ax1.set_xlabel('Total Tokens per Session')
        ax1.set_ylabel('Satisfaction Rating (1-10)')
        ax1.set_title('Token Usage vs Satisfaction (Individual Sessions)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Add correlation coefficient
        correlation = self._calculate_correlation(tokens, satisfaction)
        ax1.text(0.05, 0.95, f'Correlation: {correlation:.3f}', transform=ax1.transAxes, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # 2. Token distribution histogram
        ax2.hist(tokens, bins=min(20, len(meaningful_sessions)//2 + 1), alpha=0.7, color='green', edgecolor='darkgreen')
        ax2.set_xlabel('Total Tokens per Session')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Token Usage Distribution')
        ax2.grid(True, alpha=0.3)
        
        # Add statistics
        ax2.axvline(statistics.mean(tokens), color='red', linestyle='--', linewidth=2, label=f'Mean: {statistics.mean(tokens):,.0f}')
        ax2.axvline(statistics.median(tokens), color='orange', linestyle='--', linewidth=2, label=f'Median: {statistics.median(tokens):,.0f}')
        ax2.legend()
        
        # 3. Satisfaction distribution
        ax3.hist(satisfaction, bins=10, alpha=0.7, color='purple', edgecolor='darkpurple')
        ax3.set_xlabel('Satisfaction Rating')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Satisfaction Rating Distribution')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0, 10)
        
        # Add statistics
        ax3.axvline(statistics.mean(satisfaction), color='red', linestyle='--', linewidth=2, label=f'Mean: {statistics.mean(satisfaction):.1f}')
        ax3.axvline(statistics.median(satisfaction), color='orange', linestyle='--', linewidth=2, label=f'Median: {statistics.median(satisfaction):.1f}')
        ax3.legend()
        
        # 4. Cost vs Satisfaction
        costs = [s.estimated_cost_usd for s in meaningful_sessions]
        ax4.scatter(costs, satisfaction, alpha=0.6, s=60, c='orange', edgecolors='darkorange', linewidth=0.5)
        ax4.set_xlabel('Estimated Cost (USD)')
        ax4.set_ylabel('Satisfaction Rating (1-10)')
        ax4.set_title('Cost vs Satisfaction')
        ax4.grid(True, alpha=0.3)
        
        # Add cost trend line
        if len(costs) > 1:
            z_cost = np.polyfit(costs, satisfaction, 1)
            p_cost = np.poly1d(z_cost)
            ax4.plot(costs, p_cost(costs), "r--", alpha=0.8, linewidth=2)
            cost_correlation = self._calculate_correlation(costs, satisfaction)
            ax4.text(0.05, 0.95, f'Correlation: {cost_correlation:.3f}', transform=ax4.transAxes,
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Chart saved to: {save_path}")
        
        return fig
    
    def generate_analysis_report(self, sessions: List[StreamSessionLog], 
                               save_path: str = "stream_analysis_report.md") -> str:
        """Generate comprehensive markdown report"""
        
        stats = self.calculate_session_statistics(sessions)
        
        report = f"""# Stream Session Analysis Report
        
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- **Total Sessions**: {stats['total_sessions']:,}
- **Meaningful Sessions**: {stats['meaningful_sessions']:,} (with tokens > 0)
- **Date Range**: {stats['date_range']['earliest']} to {stats['date_range']['latest']}

## Token Usage Statistics
- **Average Tokens per Session**: {stats['tokens']['total_avg']:,.0f}
- **Median Tokens per Session**: {stats['tokens']['total_median']:,.0f}
- **Standard Deviation**: {stats['tokens']['total_std']:,.0f}
- **Range**: {stats['tokens']['min_tokens']:,.0f} - {stats['tokens']['max_tokens']:,.0f} tokens
- **Average Input Tokens**: {stats['tokens']['input_avg']:,.0f}
- **Average Output Tokens**: {stats['tokens']['output_avg']:,.0f}

## Satisfaction Statistics
- **Average Satisfaction**: {stats['satisfaction']['avg']:.2f}/10
- **Median Satisfaction**: {stats['satisfaction']['median']:.2f}/10
- **Standard Deviation**: {stats['satisfaction']['std']:.2f}
- **Range**: {stats['satisfaction']['min']:.1f} - {stats['satisfaction']['max']:.1f}

## Performance Metrics
- **Average Session Duration**: {stats['performance']['avg_duration_sec']:.1f} seconds
- **Average Cost per Session**: ${stats['performance']['avg_cost_usd']:.6f}
- **Total Cost**: ${stats['performance']['total_cost_usd']:.4f}
- **Processing Speed**: {stats['performance']['avg_tokens_per_second']:.1f} tokens/second

## Correlation Analysis
- **Tokens vs Satisfaction Correlation**: {stats['correlation']['tokens_vs_satisfaction']:.3f}

"""
        
        # Add project breakdown
        if stats.get('projects'):
            report += "\n## Project Breakdown\n\n"
            report += "| Project ID | Sessions | Avg Tokens | Avg Satisfaction | Total Cost |\n"
            report += "|------------|----------|------------|------------------|------------|\n"
            
            for pid, proj_stats in stats['projects'].items():
                report += f"| {pid[:12]}... | {proj_stats['session_count']} | {proj_stats['avg_tokens']:,.0f} | {proj_stats['avg_satisfaction']:.1f} | ${proj_stats['total_cost']:.4f} |\n"
        
        # Add mode breakdown
        if stats.get('modes'):
            report += "\n## Mode Breakdown\n\n"
            report += "| Mode | Sessions | Avg Tokens | Avg Satisfaction | Avg Duration |\n"
            report += "|------|----------|------------|------------------|--------------|\n"
            
            for mode, mode_stats in stats['modes'].items():
                report += f"| {mode} | {mode_stats['session_count']} | {mode_stats['avg_tokens']:,.0f} | {mode_stats['avg_satisfaction']:.1f} | {mode_stats['avg_duration']:.1f}s |\n"
        
        # Save report
        with open(save_path, 'w') as f:
            f.write(report)
        
        print(f"📄 Report saved to: {save_path}")
        return report
    
    def run_full_analysis(self, chart_path: str = None, report_path: str = None):
        """Run complete analysis and generate all outputs"""
        
        print("🔍 Loading session data...")
        sessions = self.load_session_data()
        
        if not sessions:
            print("❌ No session data found. Make sure sessions are being tracked.")
            return
        
        print(f"📊 Analyzing {len(sessions)} sessions...")
        
        # Generate statistics
        stats = self.calculate_session_statistics(sessions)
        print(f"✅ Analysis complete. {stats['meaningful_sessions']} meaningful sessions found.")
        
        # Create visualization
        chart_path = chart_path or f"stream_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        try:
            self.create_tokens_vs_satisfaction_chart(sessions, chart_path)
            print(f"📊 Visualization created: {chart_path}")
        except ImportError:
            print("⚠️ Matplotlib not available. Skipping visualization.")
        except Exception as e:
            print(f"❌ Failed to create visualization: {e}")
        
        # Generate report
        report_path = report_path or f"stream_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.generate_analysis_report(sessions, report_path)
        
        # Print summary
        print("\n" + "="*60)
        print("📈 ANALYSIS SUMMARY")
        print("="*60)
        print(f"Average Tokens per Session: {stats['tokens']['total_avg']:,.0f}")
        print(f"Average Satisfaction: {stats['satisfaction']['avg']:.2f}/10")
        print(f"Correlation: {stats['correlation']['tokens_vs_satisfaction']:.3f}")
        print(f"Total Sessions Analyzed: {stats['meaningful_sessions']}")
        print("="*60)


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze stream session token usage and satisfaction')
    parser.add_argument('--log-file', help='Path to session log file (optional)')
    parser.add_argument('--chart', help='Output path for chart (optional)')
    parser.add_argument('--report', help='Output path for report (optional)')
    
    args = parser.parse_args()
    
    analyzer = StreamSessionAnalyzer(args.log_file)
    analyzer.run_full_analysis(args.chart, args.report)


if __name__ == "__main__":
    main()