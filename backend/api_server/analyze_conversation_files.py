#!/usr/bin/env python3
"""
Deep analysis of conversation history to extract all file operations
and compare with actual Azure Storage contents
"""

import sys
import json
import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, '/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server')
from cloud_storage import AzureBlobStorage


@dataclass
class FileOperation:
    message_num: int
    operation_type: str  # 'create', 'update', 'write'
    file_path: str
    action_content: str
    context_lines: List[str]
    full_content: str = ""


class ConversationFileAnalyzer:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.cloud_storage = AzureBlobStorage()
        self.conversation = []
        self.azure_files = []
        self.file_operations = []
        
    def load_data(self):
        """Load conversation history and Azure file list"""
        print(f"📜 Loading conversation history for {self.project_id}")
        self.conversation = self.cloud_storage.load_conversation_history(self.project_id)
        print(f"✅ Loaded {len(self.conversation)} messages")
        
        print(f"📂 Loading Azure file list")
        self.azure_files = self.cloud_storage.list_files(self.project_id)
        print(f"✅ Found {len(self.azure_files)} files in Azure")
        
    def extract_file_operations(self):
        """Extract all file operations from conversation"""
        print(f"🔍 Analyzing conversation for file operations...")
        
        for i, message in enumerate(self.conversation):
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role != 'assistant':
                continue
                
            # Look for explicit action tags
            self._find_action_tags(i + 1, content)
            
            # Look for file creation/update mentions
            self._find_file_mentions(i + 1, content)
            
        print(f"✅ Found {len(self.file_operations)} file operations")
        
    def _find_action_tags(self, message_num: int, content: str):
        """Find explicit action tags like <action type="write_file">"""
        patterns = [
            r'<action\s+type=["\'](?:write_file|create_file|update_file)["\'][^>]*>(.+?)</action>',
            r'<action\s+type=["\'](?:write_file|create_file|update_file)["\'][^>]*path=["\']([^"\']+)["\'][^>]*>(.+?)</action>',
            r'<(?:write_file|create_file|update_file)\s+(?:file)?[Pp]ath=["\']([^"\']+)["\'][^>]*>(.+?)</(?:write_file|create_file|update_file)>',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    file_path = groups[-2] if len(groups) > 2 else self._extract_path_from_action(match.group(0))
                    action_content = groups[-1]
                    
                    if file_path:
                        self.file_operations.append(FileOperation(
                            message_num=message_num,
                            operation_type='write_file_action',
                            file_path=file_path.strip(),
                            action_content=action_content.strip(),
                            context_lines=[match.group(0)[:200] + '...'],
                            full_content=action_content.strip()
                        ))
                        
    def _extract_path_from_action(self, action_text: str) -> str:
        """Extract file path from action tag"""
        path_patterns = [
            r'(?:file)?[Pp]ath=["\']([^"\']+)["\']',
            r'filePath=["\']([^"\']+)["\']',
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, action_text)
            if match:
                return match.group(1)
        return ""
        
    def _find_file_mentions(self, message_num: int, content: str):
        """Find implicit file creation/update mentions"""
        lines = content.split('\n')
        
        creation_patterns = [
            r'(?:Creating?|Created|Writing|Wrote|Adding|Added|Generating|Generated)\s+(?:file\s+)?[`"\']*([^\s`"\'\n]+\.(?:tsx?|jsx?|py|json|css|html|md))[`"\']*',
            r'(?:✅|📄|📁)\s*([^\s\n]+\.(?:tsx?|jsx?|py|json|css|html|md))\s*(?:created|added|written|generated)',
            r'FILE:\s*([^\s\n]+\.(?:tsx?|jsx?|py|json|css|html|md))',
        ]
        
        update_patterns = [
            r'(?:Updating?|Updated|Modifying|Modified)\s+(?:file\s+)?[`"\']*([^\s`"\'\n]+\.(?:tsx?|jsx?|py|json|css|html|md))[`"\']*',
            r'(?:✅|📝)\s*([^\s\n]+\.(?:tsx?|jsx?|py|json|css|html|md))\s*(?:updated|modified)',
        ]
        
        for line_num, line in enumerate(lines):
            # Check creation patterns
            for pattern in creation_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    file_path = match.group(1)
                    context = self._get_context_lines(lines, line_num, 2)
                    
                    self.file_operations.append(FileOperation(
                        message_num=message_num,
                        operation_type='create_mention',
                        file_path=file_path,
                        action_content=line,
                        context_lines=context
                    ))
            
            # Check update patterns
            for pattern in update_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    file_path = match.group(1)
                    context = self._get_context_lines(lines, line_num, 2)
                    
                    self.file_operations.append(FileOperation(
                        message_num=message_num,
                        operation_type='update_mention',
                        file_path=file_path,
                        action_content=line,
                        context_lines=context
                    ))
                    
    def _get_context_lines(self, lines: List[str], center: int, radius: int) -> List[str]:
        """Get context lines around a specific line"""
        start = max(0, center - radius)
        end = min(len(lines), center + radius + 1)
        return lines[start:end]
        
    def check_files_in_azure(self) -> Dict[str, bool]:
        """Check which mentioned files actually exist in Azure"""
        print(f"🔍 Checking file existence in Azure...")
        
        results = {}
        azure_files_set = set(self.azure_files)
        
        for operation in self.file_operations:
            file_path = operation.file_path
            normalized_path = self._normalize_path(file_path)
            
            # Direct match
            exists = file_path in azure_files_set or normalized_path in azure_files_set
            
            # Fuzzy match - check if any Azure file ends with this filename
            if not exists:
                filename = file_path.split('/')[-1]
                for azure_file in azure_files_set:
                    if azure_file.endswith(filename) or azure_file.endswith('/' + filename):
                        exists = True
                        break
                        
            results[file_path] = exists
            
        return results
        
    def _normalize_path(self, path: str) -> str:
        """Normalize file path for comparison"""
        # Remove leading slashes and normalize separators
        normalized = path.strip().lstrip('./')
        
        # Handle common path variations
        if not normalized.startswith(('frontend/', 'backend/')):
            if any(ext in normalized for ext in ['.tsx', '.jsx', '.ts', '.js', '.css', '.html']):
                normalized = 'frontend/' + normalized
            elif normalized.endswith('.py'):
                normalized = 'backend/' + normalized
                
        return normalized
        
    def generate_detailed_report(self):
        """Generate comprehensive analysis report"""
        print(f"📊 Generating detailed report...")
        
        file_existence = self.check_files_in_azure()
        
        # Group operations by file
        files_by_path = {}
        for op in self.file_operations:
            if op.file_path not in files_by_path:
                files_by_path[op.file_path] = []
            files_by_path[op.file_path].append(op)
            
        # Categorize files
        missing_files = []
        existing_files = []
        
        for file_path, operations in files_by_path.items():
            exists = file_existence.get(file_path, False)
            
            file_info = {
                'path': file_path,
                'exists': exists,
                'operations': operations,
                'operation_count': len(operations),
                'messages': list(set(op.message_num for op in operations))
            }
            
            if exists:
                existing_files.append(file_info)
            else:
                missing_files.append(file_info)
                
        # Create report
        report_lines = [
            f"# Detailed File Operation Analysis: {self.project_id}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total file operations found:** {len(self.file_operations)}",
            f"- **Unique files mentioned:** {len(files_by_path)}",
            f"- **Files existing in Azure:** {len(existing_files)}",
            f"- **Files MISSING from Azure:** {len(missing_files)}",
            "",
            "## 🚨 MISSING FILES (Critical Issues)",
            ""
        ]
        
        # Detail missing files
        for file_info in sorted(missing_files, key=lambda x: x['operation_count'], reverse=True):
            report_lines.extend([
                f"### ❌ `{file_info['path']}` - **MISSING**",
                f"**Operations:** {file_info['operation_count']} mentions across messages {file_info['messages']}",
                ""
            ])
            
            for op in file_info['operations']:
                report_lines.extend([
                    f"**Message {op.message_num}** - {op.operation_type}:",
                    f"```",
                    op.action_content[:300] + ('...' if len(op.action_content) > 300 else ''),
                    f"```",
                    ""
                ])
                
                if op.full_content and len(op.full_content) > 500:
                    report_lines.extend([
                        f"**Full content available:** {len(op.full_content)} characters",
                        ""
                    ])
                    
        # Detail existing files
        report_lines.extend([
            "## ✅ EXISTING FILES (Confirmed in Azure)",
            ""
        ])
        
        for file_info in sorted(existing_files, key=lambda x: x['operation_count'], reverse=True):
            report_lines.extend([
                f"### ✅ `{file_info['path']}` - **EXISTS**",
                f"**Operations:** {file_info['operation_count']} mentions in messages {file_info['messages']}",
                ""
            ])
            
        # Azure files not mentioned
        mentioned_files = set(files_by_path.keys())
        azure_normalized = {self._normalize_path(f): f for f in self.azure_files}
        
        not_mentioned = []
        for norm_path, actual_path in azure_normalized.items():
            found = False
            for mentioned in mentioned_files:
                if (mentioned == norm_path or 
                    mentioned == actual_path or
                    actual_path.endswith('/' + mentioned.split('/')[-1])):
                    found = True
                    break
            if not found and actual_path.startswith('frontend/'):
                not_mentioned.append(actual_path)
                
        if not_mentioned:
            report_lines.extend([
                "## 📁 Files in Azure but NOT mentioned in conversation",
                ""
            ])
            for f in sorted(not_mentioned)[:20]:
                report_lines.append(f"- `{f}`")
            if len(not_mentioned) > 20:
                report_lines.append(f"- ... and {len(not_mentioned)-20} more files")
                
        return '\n'.join(report_lines)
        
    def run_full_analysis(self):
        """Run complete analysis"""
        print(f"🚀 Starting full analysis of {self.project_id}")
        print("=" * 60)
        
        self.load_data()
        self.extract_file_operations()
        
        report = self.generate_detailed_report()
        
        # Save report
        output_file = f"/Users/shanjairaj/Documents/forks/bolt.diy/backend/api_server/{self.project_id}_DETAILED_ANALYSIS.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"✅ Analysis complete!")
        print(f"📄 Detailed report saved: {output_file}")
        
        # Print summary
        file_existence = self.check_files_in_azure()
        missing_count = sum(1 for exists in file_existence.values() if not exists)
        existing_count = len(file_existence) - missing_count
        
        print(f"\n📊 Summary:")
        print(f"   Total operations: {len(self.file_operations)}")
        print(f"   Files mentioned: {len(file_existence)}")
        print(f"   ✅ Existing: {existing_count}")
        print(f"   ❌ Missing: {missing_count}")
        
        if missing_count > 0:
            print(f"\n🚨 Missing files:")
            for file_path, exists in file_existence.items():
                if not exists:
                    ops_count = len([op for op in self.file_operations if op.file_path == file_path])
                    print(f"     {file_path} ({ops_count} operations)")


if __name__ == "__main__":
    analyzer = ConversationFileAnalyzer("horizon-543-56f69")
    analyzer.run_full_analysis()