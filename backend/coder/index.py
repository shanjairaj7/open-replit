from shared_models import StreamingXMLParser, GroqAgentState
import json
import os
from datetime import datetime

def coder(messages, self: GroqAgentState):
    # Log messages and token count at each coder() call
    _log_coder_call(messages, self)
    
    max_iterations = 30  # Prevent infinite loops
    iteration = 0
    full_response = ""
    
    while iteration < max_iterations:
        iteration += 1
        print(f"📝 Generation iteration {iteration}")
        
        try:
            # Create streaming response
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=16000,
                stream=True,
            )
            
            # Process stream with interrupt detection
            parser = StreamingXMLParser()
            accumulated_content = ""
            should_interrupt = False
            interrupt_action = None
            
            # Early detection state for update_file actions
            update_file_detected = False
            update_file_buffer = ""
            update_file_validated = False  # Track if we already validated this file
            
            # Token tracking
            final_chunk = None
            
            for chunk in completion:
                final_chunk = chunk  # Keep track of last chunk for token usage

                # print(chunk)

                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    usage = chunk.usage
                    if hasattr(usage, 'total_tokens'):
                        print(f"\nUsage Statistics:")
                        print(f"Total Tokens: {usage.total_tokens}")
                        print(f"Prompt Tokens: {usage.prompt_tokens}")
                        print(f"Completion Tokens: {usage.completion_tokens}")
                        if hasattr(usage, 'cost'):
                            print(f"Cost: {usage.cost} credits")
                        
                        # Update internal tracking
                        self.token_usage['prompt_tokens'] = usage.prompt_tokens
                        self.token_usage['completion_tokens'] = usage.completion_tokens
                        self.token_usage['total_tokens'] = usage.total_tokens
                        
                        print(f"💰 Running Total: {self.token_usage['total_tokens']:,} tokens")


                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    accumulated_content += content
                    
                    # Early detection: Check for update_file action start
                    if not update_file_detected and '<action type="update_file"' in accumulated_content:
                        update_file_detected = True
                        update_file_buffer = accumulated_content
                        print(f"\n🚨 EARLY DETECTION: Found update_file action, waiting for path...")
                    
                    # Early detection: Check for complete file creation action
                    if not update_file_detected and '<action type="file"' in accumulated_content:
                        # Check if we have the complete action (with closing tag)
                        if '</action>' in accumulated_content:
                            print(f"\n🚨 COMPLETE FILE ACTION DETECTED: Creating file immediately...")
                            # Process file creation in real-time
                            should_interrupt = True
                            interrupt_action = {
                                'type': 'create_file_realtime',
                                'content': accumulated_content
                            }
                            break
                        else:
                            # Keep streaming until we get the complete action - no print to maintain code flow
                            pass
                    
                    # If we detected update_file, keep buffering until we get the path
                    if update_file_detected and not update_file_validated:
                        # Look for path attribute in the current buffer
                        import re
                        path_match = re.search(r'(?:path|filePath)="([^"]*)"', accumulated_content)
                        if path_match:
                            file_path = path_match.group(1)
                            print(f"\n🔍 Found file path: {file_path}")
                            
                            # Check if this file has been read (only validate once)
                            if file_path not in self.read_files_tracker and file_path not in self.read_files_persistent:
                                print(f"\n🚨 INTERRUPT: File '{file_path}' needs to be read before updating!")
                                print(f"📖 Automatically reading file first...")
                                
                                # Create a read_file interrupt action
                                should_interrupt = True
                                interrupt_action = {
                                    'type': 'read_file',
                                    'path': file_path
                                }
                                update_file_validated = True  # Mark as validated, stop checking
                                break  # Break out of chunk processing to handle interrupt
                            else:
                                print(f"\n✅ File '{file_path}' was previously read, update allowed")
                                update_file_validated = True  # Mark as validated, stop checking
                    
                    # Check for read_file, run_command, and update_file actions
                    for action in parser.process_chunk(content):
                        if action.get('type') == 'read_file':
                            print(f"\n🚨 INTERRUPT: Detected read_file action for {action.get('path')}")
                            should_interrupt = True
                            interrupt_action = action
                            break
                        elif action.get('type') == 'run_command':
                            print(f"\n🚨 INTERRUPT: Detected run_command action: {action.get('command')} in {action.get('cwd')}")
                            should_interrupt = True
                            interrupt_action = action
                            break
                        elif action.get('type') == 'update_file':
                            file_path = action.get('path') or action.get('filePath')
                            if file_path:
                                # Check if file was read (using our early validation tracking)
                                if file_path not in self.read_files_tracker and file_path not in self.read_files_persistent:
                                    # This should have been caught by early detection, but double-check
                                    print(f"\n🚨 ERROR: File '{file_path}' not read before update!")
                                    continue
                                else:
                                    print(f"\n🚨 INTERRUPT: Detected update_file action for {action.get('path')}")
                                    should_interrupt = True
                                    interrupt_action = action
                                    break
                        elif action.get('type') == 'rename_file':
                            print(f"\n🚨 INTERRUPT: Detected rename_file action: {action.get('path')} -> {action.get('new_name')}")
                            should_interrupt = True
                            interrupt_action = action
                            break
                        elif action.get('type') == 'delete_file':
                            print(f"\n🚨 INTERRUPT: Detected delete_file action for {action.get('path')}")
                            should_interrupt = True
                            interrupt_action = action
                            break
                    
                    if should_interrupt:
                        break
            
            print()  # New line after streaming
            full_response += accumulated_content
            

                # check if total tokens is more than 20k, summarise the conversation using the available functions, then make this process continue as usual
            
            # If we detected a read_file or run_command action, process it and continue
            if should_interrupt and interrupt_action:
                if interrupt_action.get('type') == 'read_file':
                    file_content = self._handle_read_file_interrupt(interrupt_action)
                    if file_content is not None:
                        # Add the read file content to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"File content for {interrupt_action.get('path')}:\n\n```\n{file_content}\n```\n\nPlease continue with your response based on this file content."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        # Pass the read error back to the model so it can continue with different approach
                        file_path = interrupt_action.get('path', 'unknown')
                        print(f"❌ Failed to read file {file_path}, passing error to model")
                        
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        error_msg = {"role": "user", "content": f"❌ Error: Cannot update file '{file_path}' because it doesn't exist.\n\n✅ SOLUTION: Use <action type=\"file\" filePath=\"{file_path}\">YOUR_FILE_CONTENT</action> to create the file first.\n\nDo NOT use update_file for non-existent files. Use the file action to create it.\n\nPlease continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(error_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(error_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'create_file_realtime':
                    # Handle real-time file creation
                    create_result = self._handle_create_file_realtime(interrupt_action)
                    if create_result is not None:
                        file_path = create_result.get('file_path')
                        print(f"✅ Created file: {file_path}")
                        
                        # Mark file as read since we just created it
                        self.read_files_tracker.add(file_path)
                        self.read_files_persistent.add(file_path)
                        self._save_read_files_tracking()
                        
                        # Add the creation result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        
                        # Check for validation errors
                        python_errors = create_result.get('python_errors', '')
                        typescript_errors = create_result.get('typescript_errors', '')
                        
                        error_messages = []
                        if python_errors:
                            error_messages.append(f"Python validation errors:\n{python_errors}")
                        if typescript_errors:
                            error_messages.append(f"TypeScript validation errors:\n{typescript_errors}")

                        if error_messages:
                            user_content = f"""✅ File '{file_path}' created.

                        **Static Analysis Results:**
                        {'\n\n'.join(error_messages)}

                        **NEXT STEPS:**
                        1. Fix these static errors first
                        2. If this is a backend service, create a test file (e.g., `backend/test_api.py`) to verify it works
                        3. Run the test file with `python backend/test_api.py`
                        4. Fix any runtime errors
                        5. Delete the test file when done

                        Continue with your implementation and testing."""
                        else:
                            user_content = f"""✅ File '{file_path}' created successfully.

                        If this was a backend service:
                        1. Create a test file (e.g., `backend/test_api.py`) 
                        2. Write Python code to test your endpoints
                        3. Run it with `python backend/test_api.py`
                        4. Verify it works, then delete the test file."""

                        user_msg = {"role": "user", "content": user_content}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'run_command':
                    command_output = self._handle_run_command_interrupt(interrupt_action)
                    if command_output is not None:
                        # Add the command output to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {
                            "role": "user", "content": f"""
                            Command output for `{interrupt_action.get('command')}` in {interrupt_action.get('cwd')}:
                            {command_output}

                            **Instructions:**
                            - These are the logs from the terminal command execution
                            - If there are any errors, warnings, or issues in the output above, please fix them immediately
                            - Use `<action type=\"read_file\" path=\"...\"/>` to examine files that have errors
                            - Use `<action type=\"update_file\" path=\"...\">` to fix any issues found
                            - Continue with your response and next steps after addressing any problems

                            Please continue with your next steps..
                            """
                        }
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to run command {interrupt_action.get('command')}, stopping generation")
                        break
                elif interrupt_action.get('type') == 'update_file':
                    update_result = self._handle_update_file_interrupt(interrupt_action)
                    if update_result is not None:
                        # Add the update result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"File '{interrupt_action.get('path')}' has been updated successfully. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to update file {interrupt_action.get('path')}, stopping generation")
                        break
                elif interrupt_action.get('type') == 'rename_file':
                    rename_result = self._handle_rename_file_interrupt(interrupt_action)
                    if rename_result is not None:
                        # Add the rename result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        old_path = interrupt_action.get('path')
                        new_name = interrupt_action.get('new_name')
                        user_msg = {"role": "user", "content": f"File '{old_path}' has been renamed to '{new_name}' successfully. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to rename file {interrupt_action.get('path')}, stopping generation")
                        break
                elif interrupt_action.get('type') == 'delete_file':
                    delete_result = self._handle_delete_file_interrupt(interrupt_action)
                    if delete_result is not None:
                        # Add the delete result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        file_path = interrupt_action.get('path')
                        user_msg = {"role": "user", "content": f"File '{file_path}' has been deleted successfully. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to delete file {interrupt_action.get('path')}, stopping generation")
                        break
            else:
                # No interruption, process any remaining actions and finish
                self._process_remaining_actions(accumulated_content)
                break
    
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            break
    
    # Add current project errors as context at the end of generation
    project_errors = _get_project_errors(self)
    if project_errors:
        error_msg = {"role": "user", "content": f"Current codebase errors:\n\n{project_errors}\n\nNote: Fix critical errors if needed, otherwise continue with main task."}
        messages.append(error_msg)
        self.conversation_history.append(error_msg)
    
    return full_response

def _get_project_errors(self):
    """Get current TypeScript errors for this project (quick read)"""
    try:
        project_id = getattr(self, 'project_id', None)
        if not project_id:
            return ""
            
        error_file_path = f"/opt/codebase-platform/projects/{project_id}/frontend/.ts-errors.txt"
        
        # Read current errors if file exists
        import os
        if os.path.exists(error_file_path):
            with open(error_file_path, 'r') as f:
                content = f.read().strip()
                if content and content != "No errors":
                    return content
        return ""
    except Exception as e:
        print(f"Failed to read project errors: {e}")
        return ""

def _run_file_diagnostics(self, file_path):
    """Run diagnostic commands after file operations and return formatted results"""
    print(f"\n🔍 DIAGNOSTICS: Starting diagnostic checks for file: {file_path}")
    
    # Only run diagnostics for frontend TypeScript/React files
    if not file_path.startswith('frontend/src/') or not file_path.endswith(('.ts', '.tsx')):
        print(f"⏭️  DIAGNOSTICS: Skipping non-TypeScript file: {file_path}")
        return ""
    
    print(f"✅ DIAGNOSTICS: File qualifies for TypeScript/React diagnostics")
    
    # Extract relative file path for specific file checks
    relative_file = file_path.replace('frontend/', '')
    print(f"📁 DIAGNOSTICS: Relative file path: {relative_file}")

    def _extract_section(full_output, start_marker, end_marker):
        """Extract a section of output between markers"""
        print(f"🔍 EXTRACT: Looking for section between '{start_marker}' and '{end_marker}'")
        
        try:
            start_pos = full_output.find(f"=== {start_marker} ===")
            end_pos = full_output.find(f"=== {end_marker} ===")
            
            print(f"📍 EXTRACT: Start marker at position: {start_pos}")
            print(f"📍 EXTRACT: End marker at position: {end_pos}")
            
            if start_pos == -1 or end_pos == -1:
                print(f"❌ EXTRACT: One or both markers not found")
                return None
                
            # Extract content between markers
            start_pos += len(f"=== {start_marker} ===")
            section_content = full_output[start_pos:end_pos].strip()
            
            print(f"✅ EXTRACT: Successfully extracted {len(section_content)} characters")
            if len(section_content) > 0:
                print(f"📄 EXTRACT: First 100 chars: {section_content[:100]}...")
            
            return section_content
            
        except Exception as e:
            print(f"❌ EXTRACT: Exception during extraction: {str(e)}")
            return None

    
    # Define diagnostic commands
    commands = [
        {
            "name": "TypeScript Check",
            "command": "npx tsc --noEmit",
            "description": "Checking for TypeScript errors"
        },
        {
            "name": "ESLint Check", 
            "command": "npx eslint src/**/*.{ts,tsx} --report-unused-disable-directives",
            "description": "Checking for linting issues"
        },
        {
            "name": "File Compilation",
            "command": f"npx tsc {relative_file} --noEmit",
            "description": f"Compiling {relative_file}"
        }
    ]
    
    print(f"📋 DIAGNOSTICS: Configured {len(commands)} diagnostic commands")
    for i, cmd in enumerate(commands, 1):
        print(f"   {i}. {cmd['name']}: {cmd['command']}")
    
    try:
        # Combine all commands into a single shell script with separators
        combined_command = "echo '=== TYPESCRIPT_CHECK_START ==='; " + \
                          "npx tsc --noEmit 2>&1; " + \
                          "echo '=== TYPESCRIPT_CHECK_END ==='; " + \
                          "echo '=== ESLINT_CHECK_START ==='; " + \
                          "npx eslint src/**/*.{ts,tsx} --report-unused-disable-directives 2>&1; " + \
                          "echo '=== ESLINT_CHECK_END ==='; " + \
                          "echo '=== FILE_COMPILATION_START ==='; " + \
                          f"npx tsc {relative_file} --noEmit 2>&1; " + \
                          "echo '=== FILE_COMPILATION_END ==='"
        
        print(f"🔗 DIAGNOSTICS: Combined command length: {len(combined_command)} characters")
        print(f"🚀 DIAGNOSTICS: Executing combined diagnostic command via API...")
        
        # Execute single combined command via API
        result = self._execute_command_via_api(combined_command, "frontend")
        
        if not result:
            print(f"❌ DIAGNOSTICS: API call failed - no result returned")
            return f"<diagnostics>\n**All Checks:** ❌ ERROR - Command execution failed\n</diagnostics>"
        
        print(f"📥 DIAGNOSTICS: API call successful, processing response...")
        print(f"   Success: {result.get('success', 'unknown')}")
        print(f"   Output length: {len(result.get('output', ''))}")
        print(f"   Error length: {len(result.get('error', ''))}")
        
        # Parse the combined output
        full_output = result.get('output', '') + result.get('error', '')
        print(f"📊 DIAGNOSTICS: Total output length: {len(full_output)} characters")
        
        diagnostics_results = []
        
        # Split output by our markers
        print(f"🔍 DIAGNOSTICS: Parsing output sections...")
        sections = {
            "TypeScript Check": _extract_section(full_output, "TYPESCRIPT_CHECK_START", "TYPESCRIPT_CHECK_END"),
            "ESLint Check": _extract_section(full_output, "ESLINT_CHECK_START", "ESLINT_CHECK_END"), 
            "File Compilation": _extract_section(full_output, "FILE_COMPILATION_START", "FILE_COMPILATION_END")
        }
        
        print(f"📋 DIAGNOSTICS: Extracted {len(sections)} sections:")
        for section_name, content in sections.items():
            if content is not None:
                print(f"   ✅ {section_name}: {len(content)} characters")
            else:
                print(f"   ❌ {section_name}: Not found")
        
        # Process each section
        for cmd_name, section_output in sections.items():
            print(f"🔧 DIAGNOSTICS: Processing section '{cmd_name}'...")
            
            if section_output is None:
                print(f"   ❌ Section '{cmd_name}' not found in output")
                diagnostics_results.append(f"**{cmd_name}:** ❌ ERROR - Output not found")
                continue
                
            # Clean the output (remove the marker lines)
            clean_output = section_output.strip()
            print(f"   📝 Clean output length: {len(clean_output)}")
            
            # Check if command was successful (no meaningful error output)
            if not clean_output or clean_output in ["", "\n"] or "No issues found" in clean_output:
                print(f"   ✅ {cmd_name}: PASSED (no issues)")
                diagnostics_results.append(f"**{cmd_name}:** ✅ PASSED")
            else:
                print(f"   ❌ {cmd_name}: FAILED (has issues)")
                diagnostics_results.append(f"**{cmd_name}:** ❌ FAILED")
                
                # Limit output length for readability
                if len(clean_output) > 500:
                    print(f"   ✂️  Truncating output from {len(clean_output)} to 500 characters")
                    clean_output = clean_output[:500] + "... (truncated)"
                diagnostics_results.append(f"```\n{clean_output}\n```")
        
        print(f"📋 DIAGNOSTICS: Generated {len(diagnostics_results)} result entries")
        
        if diagnostics_results:
            final_result = f"<diagnostics>\n{chr(10).join(diagnostics_results)}\n</diagnostics>"
            print(f"✅ DIAGNOSTICS: Returning formatted results ({len(final_result)} characters)")
            return final_result
        else:
            print(f"⚠️  DIAGNOSTICS: No results generated, returning empty string")
            return ""
            
    except Exception as e:
        print(f"❌ DIAGNOSTICS: Exception occurred: {str(e)}")
        import traceback
        print(f"📚 DIAGNOSTICS: Full traceback:")
        traceback.print_exc()
        return f"<diagnostics>\n**All Checks:** ❌ ERROR - {str(e)}\n</diagnostics>"

def _log_coder_call(messages, self):
    """Log exact messages and token count at each coder() call"""
    try:
        # Create logs directory
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'coder_call_logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # milliseconds
        project_id = getattr(self, 'project_id', 'unknown')
        filename = f"coder_call_{project_id}_{timestamp}"
        
        # Current token usage
        current_tokens = getattr(self, 'token_usage', {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0})
        
        # Calculate approximate input tokens for this call
        input_text = ""
        for msg in messages:
            input_text += f"{msg.get('role', '')}: {msg.get('content', '')}\n"
        
        estimated_input_tokens = len(input_text) // 4  # rough estimate: 4 chars per token
        
        # Create log data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "iteration_info": {
                "total_tokens_before_call": current_tokens.get('total_tokens', 0),
                "prompt_tokens_before_call": current_tokens.get('prompt_tokens', 0),
                "completion_tokens_before_call": current_tokens.get('completion_tokens', 0),
                "estimated_input_tokens_this_call": estimated_input_tokens
            },
            "model": getattr(self, 'model', 'unknown'),
            "messages_count": len(messages),
            "messages": messages,
            "statistics": {
                "total_characters": len(input_text),
                "message_breakdown": [
                    {
                        "role": msg.get('role', ''),
                        "content_length": len(msg.get('content', ''))
                    } for msg in messages
                ]
            }
        }
        
        # Save as JSON file
        json_file = os.path.join(logs_dir, f"{filename}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        # Save as markdown file for readability
        md_file = os.path.join(logs_dir, f"{filename}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Coder Call Log - {timestamp}\n\n")
            f.write(f"**Project ID:** {project_id}\n")
            f.write(f"**Timestamp:** {datetime.now().isoformat()}\n")
            f.write(f"**Model:** {getattr(self, 'model', 'unknown')}\n\n")
            
            f.write("## Token Usage Before This Call\n\n")
            f.write(f"- **Total Tokens:** {current_tokens.get('total_tokens', 0):,}\n")
            f.write(f"- **Prompt Tokens:** {current_tokens.get('prompt_tokens', 0):,}\n") 
            f.write(f"- **Completion Tokens:** {current_tokens.get('completion_tokens', 0):,}\n")
            f.write(f"- **Estimated Input Tokens (this call):** {estimated_input_tokens:,}\n\n")
            
            f.write("## Messages Sent to Model\n\n")
            f.write(f"**Total Messages:** {len(messages)}\n")
            f.write(f"**Total Characters:** {len(input_text):,}\n\n")
            
            for i, msg in enumerate(messages, 1):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                f.write(f"### Message {i} - {role.title()}\n\n")
                f.write(f"**Length:** {len(content):,} characters\n\n")
                f.write("```\n")
                f.write(content)
                f.write("\n```\n\n")
        
        print(f"📊 CODER_LOG: Saved call details to {json_file} and {md_file}")
        
    except Exception as e:
        print(f"❌ CODER_LOG: Error logging coder call: {e}")
        # Don't let logging errors break the main flow

