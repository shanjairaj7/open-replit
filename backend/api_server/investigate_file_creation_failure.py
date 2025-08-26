#!/usr/bin/env python3
"""
Deep dive investigation into why file creation failed for horizon-543-56f69.
This script will analyze the exact file creation pipeline to identify failure points.
"""

import sys
import json
import re
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


@dataclass
class FileCreationAction:
    message_num: int
    file_path: str
    full_content: str
    action_xml: str
    success_indicators: List[str]
    

class FileCreationInvestigator:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.cloud_storage = AzureBlobStorage()
        self.conversation = []
        self.file_actions = []
        
    def load_conversation(self):
        """Load full conversation history"""
        print(f"📜 Loading conversation for {self.project_id}")
        self.conversation = self.cloud_storage.load_conversation_history(self.project_id)
        print(f"✅ Loaded {len(self.conversation)} messages")
        
    def extract_file_creation_actions(self):
        """Extract detailed file creation actions with full content"""
        print(f"🔍 Extracting file creation actions...")
        
        for i, message in enumerate(self.conversation):
            if message.get('role') != 'assistant':
                continue
                
            content = message.get('content', '')
            
            # Find all write_file actions with detailed patterns
            patterns = [
                r'<action\s+type=["\']write_file["\']\s+(?:[^>]*\s+)?filePath=["\'](.*?)["\'][^>]*>(.*?)</action>',
                r'<action\s+type=["\']write_file["\'][^>]*>(.*?)</action>',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        file_path = groups[0]
                        file_content = groups[1]
                    elif len(groups) == 1:
                        # Extract file path from the action content
                        action_content = groups[0]
                        file_path = self._extract_filepath_from_action(action_content)
                        file_content = action_content
                    else:
                        continue
                    
                    if file_path and file_content:
                        # Look for success indicators in subsequent content
                        success_indicators = self._find_success_indicators(content, match.end())
                        
                        action = FileCreationAction(
                            message_num=i + 1,
                            file_path=file_path.strip(),
                            full_content=file_content.strip(),
                            action_xml=match.group(0),
                            success_indicators=success_indicators
                        )
                        
                        self.file_actions.append(action)
        
        print(f"✅ Found {len(self.file_actions)} file creation actions")
        
    def _extract_filepath_from_action(self, action_content: str) -> str:
        """Extract file path from action content"""
        lines = action_content.split('\n')
        for line in lines[:5]:  # Check first few lines
            if any(keyword in line.lower() for keyword in ['file:', 'path:', 'creating']):
                # Try to extract file path
                path_match = re.search(r'([a-zA-Z0-9_/-]+\.[a-zA-Z]+)', line)
                if path_match:
                    return path_match.group(1)
        return ""
        
    def _find_success_indicators(self, content: str, start_pos: int) -> List[str]:
        """Find indicators that file creation was successful"""
        remaining_content = content[start_pos:start_pos+500]  # Check next 500 chars
        
        indicators = []
        success_patterns = [
            r'✅[^\\n]*(?:created|added|written|saved)',
            r'Successfully (?:created|added|written|saved)',
            r'File (?:created|added|written|saved)',
            r'✓[^\\n]*(?:created|added|written|saved)',
        ]
        
        for pattern in success_patterns:
            matches = re.findall(pattern, remaining_content, re.IGNORECASE)
            indicators.extend(matches)
            
        return indicators
        
    def analyze_missing_files(self):
        """Analyze specifically the missing files from our detailed report"""
        missing_files = [
            "backend/routes/crm_models.py",
            "backend/routes/crm_schemas.py", 
            "backend/routes/crm.py",
            "backend/test_crm_api.py",
            "frontend/src/api/crm_api.ts",
            "frontend/src/pages/ContactsPage.tsx",
            "frontend/src/pages/DealsPage.tsx",
            "frontend/src/pages/AuditLogPage.tsx",
            "frontend/src/components/Sidebar.tsx",
            "frontend/src/components/PageContainer.tsx"
        ]
        
        print(f"🎯 Analyzing missing files specifically...")
        
        analysis = {}
        
        for missing_file in missing_files:
            # Find actions for this file
            file_actions = [action for action in self.file_actions 
                          if action.file_path == missing_file or 
                          action.file_path.endswith(missing_file.split('/')[-1])]
            
            if file_actions:
                analysis[missing_file] = {
                    "actions_found": len(file_actions),
                    "actions": []
                }
                
                for action in file_actions:
                    analysis[missing_file]["actions"].append({
                        "message_num": action.message_num,
                        "content_length": len(action.full_content),
                        "has_success_indicators": len(action.success_indicators) > 0,
                        "success_indicators": action.success_indicators,
                        "action_preview": action.action_xml[:200] + "..." if len(action.action_xml) > 200 else action.action_xml
                    })
            else:
                analysis[missing_file] = {
                    "actions_found": 0,
                    "note": "No file creation actions found"
                }
        
        return analysis
        
    def check_message_60_specifically(self):
        """Message 60 seems to contain multiple file actions - analyze it specifically"""
        print(f"🔍 Analyzing Message 60 specifically...")
        
        if len(self.conversation) < 60:
            return {"error": "Message 60 not found"}
            
        message_60 = self.conversation[59]  # 0-indexed
        content = message_60.get('content', '')
        
        # Count all write_file actions in message 60
        action_pattern = r'<action\s+type=["\']write_file["\'][^>]*>.*?</action>'
        actions = re.findall(action_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # Extract file paths from each action
        file_paths = []
        for action in actions:
            path_match = re.search(r'filePath=["\'](.*?)["\']', action)
            if path_match:
                file_paths.append(path_match.group(1))
                
        return {
            "total_actions": len(actions),
            "file_paths": file_paths,
            "content_length": len(content),
            "message_role": message_60.get('role'),
            "sample_action": actions[0][:300] + "..." if actions else None
        }
        
    def generate_investigation_report(self):
        """Generate comprehensive investigation report"""
        print(f"📊 Generating investigation report...")
        
        missing_analysis = self.analyze_missing_files()
        message_60_analysis = self.check_message_60_specifically()
        
        # Check Azure files to see what actually exists
        azure_files = self.cloud_storage.list_files(self.project_id)
        
        report_lines = [
            f"# File Creation Failure Investigation: {self.project_id}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 🚨 Executive Summary",
            "",
            f"This investigation reveals that **{len(self.file_actions)} file creation actions** were found in the conversation,",
            f"but **10 critical files are missing** from Azure Storage. This indicates a **systematic file upload failure**.",
            "",
            "## 📊 Key Findings",
            "",
            f"- **Total file creation actions found:** {len(self.file_actions)}",
            f"- **Files actually in Azure:** {len(azure_files)}",
            f"- **Missing critical files:** 10",
            f"- **Message 60 actions:** {message_60_analysis.get('total_actions', 0)}",
            "",
            "## 🎯 Missing Files Analysis",
            ""
        ]
        
        for file_path, analysis in missing_analysis.items():
            report_lines.extend([
                f"### ❌ `{file_path}`",
                f"**Actions found:** {analysis['actions_found']}",
                ""
            ])
            
            if analysis['actions_found'] > 0:
                for action in analysis['actions']:
                    report_lines.extend([
                        f"**Message {action['message_num']}:**",
                        f"- Content length: {action['content_length']} characters",
                        f"- Success indicators: {'✅ Yes' if action['has_success_indicators'] else '❌ None'}",
                        f"- Indicators: {action['success_indicators'] if action['success_indicators'] else 'None found'}",
                        ""
                    ])
            else:
                report_lines.append("*No file creation actions found*")
                
            report_lines.append("")
            
        # Message 60 specific analysis
        report_lines.extend([
            "## 🔍 Message 60 Deep Dive",
            "",
            f"Message 60 appears to be a **bulk file creation message** with {message_60_analysis.get('total_actions', 0)} actions:",
            ""
        ])
        
        for file_path in message_60_analysis.get('file_paths', []):
            report_lines.append(f"- `{file_path}`")
            
        report_lines.extend([
            "",
            "## 🚨 Root Cause Hypothesis",
            "",
            "**Primary Theory: Bulk Action Processing Failure**",
            "",
            "1. **Message 60 contained multiple file creation actions**",
            "2. **The bulk processing system failed silently**", 
            "3. **No error was reported back to the conversation**",
            "4. **The AI model assumed all files were created successfully**",
            "",
            "**Secondary Theory: Azure Upload Pipeline Failure**",
            "",
            "1. **Files were processed locally but upload to Azure failed**",
            "2. **Network/permission issues during bulk upload**",
            "3. **Transaction rollback occurred but wasn't reported**",
            "",
            "## 🔧 Recommended Fixes",
            "",
            "### Immediate Actions:",
            "1. **Recreate all missing files** from conversation content",
            "2. **Test bulk file creation API** with similar payload",
            "3. **Verify Azure Storage permissions and connectivity**",
            "",
            "### System Improvements:",
            "1. **Add file verification after each creation**",
            "2. **Improve error handling in bulk operations**",
            "3. **Add transaction logging for file operations**",
            "4. **Implement retry logic for failed uploads**",
            "",
            "---",
            f"*Investigation completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return '\n'.join(report_lines)
        
    def run_investigation(self):
        """Run complete investigation"""
        print(f"🔍 Starting file creation failure investigation for {self.project_id}")
        print("=" * 70)
        
        self.load_conversation()
        self.extract_file_creation_actions()
        
        report = self.generate_investigation_report()
        
        # Save report
        output_file = f"/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/{self.project_id}_FILE_CREATION_INVESTIGATION.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"✅ Investigation complete!")
        print(f"📄 Report saved: {output_file}")
        
        # Print key findings
        message_60_analysis = self.check_message_60_specifically()
        print(f"\n🎯 Key Findings:")
        print(f"   File actions found: {len(self.file_actions)}")
        print(f"   Message 60 actions: {message_60_analysis.get('total_actions', 0)}")
        print(f"   Missing files: 10")
        
        return report


if __name__ == "__main__":
    investigator = FileCreationInvestigator("horizon-543-56f69")
    investigator.run_investigation()