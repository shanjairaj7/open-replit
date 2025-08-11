from shared_models import StreamingXMLParser, GroqAgentState
import json
import os
from datetime import datetime

def coder(messages, self: GroqAgentState):
    print("🚀 CODER: Starting coder() function")
    print(f"📊 CODER: Input - {len(messages)} messages, max_iterations=30")
    
    # Log messages and token count at each coder() call
    _log_coder_call(messages, self)
    print("📝 CODER: Call logging completed")
    
    max_iterations = 100  # Prevent infinite loops
    iteration = 0
    full_response = ""
    
    print(f"🔄 CODER: Starting iteration loop (max: {max_iterations})")
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"📝 CODER: Generation iteration {iteration}/{max_iterations}")
        print(f"📊 CODER: Current full_response length: {len(full_response)} chars")
        print(f"🎯 CODER: Using model: {self.model}")
        print(f"📤 CODER: Sending {len(messages)} messages to API")
        
        # Add current todo status as context at the end of generation
        print("🔍 CODER: Checking for todo status...")
        todo_status = self._display_todos()
        if todo_status:
            print('---- TODOS -----\n')
            print(f"⚠️ CODER: Found todo status ({len(todo_status)} chars), adding to context")
            
            # Determine message based on whether todos exist
            if 'no todos created yet' in todo_status:
                note = "No todos have been created yet. Please plan and create todos to then follow and systematically work on tasks."
            else:
                note = "Continue with the highest priority todo."
            
            todo_msg = {"role": "user", "content": f"""
Current todo status:\n\n{todo_status}\n\n
Note: {note}
- Systematically work on each todo until all are completed, integrated and tested to make sure it works end to end. 
- As you work on each todo, update the todo status to in_progress. 
- Once you have completed a todo, update the todo status to completed.
- If you are not sure what to do next, check the todo status and pick the highest priority todo."""}
            
            messages.append(todo_msg)
            self.conversation_history.append(todo_msg)
            print(f"📤 CODER: Added todo status to messages and conversation history: {todo_msg['content']}")
            
            print('---- TODOS -----\n')
        else:
            print("✅ CODER: No todo status found")
        
        try:
            print("🔌 CODER: Creating streaming completion...")
            # Create streaming response
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # temperature=0.1,
                max_completion_tokens=16000,
                stream=True,
                stream_options={"include_usage": True}
            )
            print("✅ CODER: Streaming completion created successfully")
            
            # Process stream with interrupt detection
            print("🔍 CODER: Initializing streaming parser and state variables")
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
            
            print("🌊 CODER: Starting to process streaming chunks...")
            chunk_count = 0
            
            for chunk in completion:
                chunk_count += 1
                final_chunk = chunk  # Keep track of last chunk for token usage
                
                # if chunk_count % 10 == 0:  # Every 10th chunk
                #     # print(f"📊 CODER: Processed {chunk_count} chunks, accumulated: {len(accumulated_content)} chars")
                #     print('')

                # print(chunk)

                # Check for usage information in chunk
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    print(f"💰 CODER: Found usage info in chunk {chunk_count}")
                    usage = chunk.usage
                    if hasattr(usage, 'total_tokens'):
                        print(f"\n📈 Usage Statistics (Chunk {chunk_count}):")
                        print(f"Total Tokens: {usage.total_tokens}")
                        print(f"Prompt Tokens: {usage.prompt_tokens}")
                        print(f"Completion Tokens: {usage.completion_tokens}")
                        if hasattr(usage, 'cost'):
                            print(f"Cost: {usage.cost} credits")
                        
                        # Update internal tracking
                        print("💾 CODER: Updating internal token tracking...")
                        old_total = self.token_usage.get('total_prompt_tokens', 0) + self.token_usage.get('total_completion_tokens', 0)
                        
                        # Update both session and cumulative tracking
                        self.session_token_usage['prompt_tokens'] += usage.prompt_tokens
                        self.session_token_usage['completion_tokens'] += usage.completion_tokens
                        self.session_token_usage['total_tokens'] = (
                            self.session_token_usage['prompt_tokens'] + 
                            self.session_token_usage['completion_tokens']
                        )
                        
                        # Update both sets of keys for compatibility
                        self.token_usage['prompt_tokens'] += usage.prompt_tokens
                        self.token_usage['completion_tokens'] += usage.completion_tokens
                        self.token_usage['total_prompt_tokens'] += usage.prompt_tokens
                        self.token_usage['total_completion_tokens'] += usage.completion_tokens
                        self.token_usage['total_tokens'] = (
                            self.token_usage['prompt_tokens'] + 
                            self.token_usage['completion_tokens']
                        )
                        
                        # Log detailed usage including reasoning tokens if available
                        if hasattr(usage, 'completion_tokens_details'):
                            details = usage.completion_tokens_details
                            if hasattr(details, 'reasoning_tokens') and details.reasoning_tokens > 0:
                                print(f"🧠 Reasoning Tokens: {details.reasoning_tokens}")
                        
                        new_total = self.token_usage['total_tokens']
                        print(f"💰 Session Total: {self.session_token_usage['total_tokens']:,} tokens")
                        print(f"💰 Running Total: {old_total:,} → {new_total:,} tokens")


                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = ""  # Initialize content variable
                    
                    # 🧠 CAPTURE DEEPSEEK'S REASONING/THINKING PROCESS
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        print(f"\n💭 THINKING: {delta.reasoning_content}", end='', flush=True)
                    
                    # Regular response content
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        print(content, end='', flush=True)
                        accumulated_content += content
                    
                    # if len(content) > 50:  # Only log for larger content chunks
                    #     print(f"\n📝 CODER: Added {len(content)} chars, total: {len(accumulated_content)}")
                    
                    # Early detection: Check for update_file action start
                    if not update_file_detected and '<action type="update_file"' in accumulated_content:
                        update_file_detected = True
                        update_file_buffer = accumulated_content
                        print(f"\n🚨 CODER: EARLY DETECTION - Found update_file action, waiting for path...")
                        print(f"🔍 CODER: Update buffer length: {len(update_file_buffer)} chars")
                    
                    # Improved early detection: Use parser to check for complete file creation action
                    if '<action type="file"' in accumulated_content and '</action>' in accumulated_content:
                        print(f"🔧 DEBUG: USING FIXED VERSION - found file action tags, validating...")
                        # Use the proper parser to validate we have a complete, valid action
                        temp_parser = StreamingXMLParser()
                        temp_actions = list(temp_parser.process_chunk(accumulated_content))
                        
                        # Check if we found any complete file actions
                        file_actions = [action for action in temp_actions if action.get('type') == 'file']
                        
                        if file_actions:
                            print(f"\n🚨 CODER: COMPLETE FILE ACTION VALIDATED - Creating {len(file_actions)} file(s) immediately...")
                            print(f"📊 CODER: File action content length: {len(accumulated_content)} chars")
                            print(f"📋 CODER: Files to create: {[action.get('path') for action in file_actions]}")
                            
                            # Process file creation in real-time
                            should_interrupt = True
                            interrupt_action = {
                                'type': 'create_file_realtime',
                                'content': accumulated_content,
                                'validated_actions': file_actions
                            }
                            print("⚡ CODER: Breaking from chunk loop for validated file creation interrupt")
                            break
                        else:
                            print(f"⏳ CODER: File action tags found but not yet complete/valid, continuing to stream...")
                            pass
                    
                    # If we detected update_file, keep buffering until we get the path
                    if update_file_detected and not update_file_validated:
                        print(f"🔍 CODER: Checking for file path in update_file action...")
                        # Look for path attribute in the current buffer
                        import re
                        path_match = re.search(r'(?:path|filePath)="([^"]*)"', accumulated_content)
                        if path_match:
                            file_path = path_match.group(1)
                            print(f"\n🎯 CODER: Found file path in update_file: {file_path}")
                            
                            # Check if this file has been read (only validate once)
                            print(f"📚 CODER: Checking if file was previously read...")
                            print(f"   Read files tracker: {len(self.read_files_tracker)} files")
                            print(f"   Persistent read files: {len(self.read_files_persistent)} files")
                            
                            if file_path not in self.read_files_tracker and file_path not in self.read_files_persistent:
                                print(f"\n🚨 CODER: INTERRUPT REQUIRED - File '{file_path}' needs to be read first!")
                                print(f"📖 CODER: Creating read_file interrupt action...")
                                
                                # Create a read_file interrupt action
                                should_interrupt = True
                                interrupt_action = {
                                    'type': 'read_file',
                                    'path': file_path
                                }
                                update_file_validated = True  # Mark as validated, stop checking
                                print("⚡ CODER: Breaking from chunk loop for read_file interrupt")
                                break  # Break out of chunk processing to handle interrupt
                            else:
                                print(f"\n✅ CODER: File '{file_path}' was previously read, update allowed")
                                update_file_validated = True  # Mark as validated, stop checking
                        else:
                            print("⏳ CODER: File path not yet available in update_file action, continuing...")
                    
                    # Check for read_file, run_command, and update_file actions
                    actions = list(parser.process_chunk(content))  # Convert generator to list
                    if actions:
                        print(f"\n🎬 CODER: Parser detected {len(actions)} actions in this chunk")
                    
                    for action in actions:
                        action_type = action.get('type')
                        print(f"🎯 CODER: Processing action type: {action_type}")
                        
                        if action_type == 'read_file':
                            file_path = action.get('path')
                            print(f"\n🚨 CODER: INTERRUPT - Detected read_file action for {file_path}")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for read_file")
                            break
                        elif action_type == 'run_command':
                            command = action.get('command')
                            cwd = action.get('cwd')
                            print(f"\n🚨 CODER: INTERRUPT - Detected run_command action: {command} in {cwd}")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for run_command")
                            break
                        elif action_type == 'update_file':
                            file_path = action.get('path') or action.get('filePath')
                            print(f"📝 CODER: Found update_file action for: {file_path}")
                            if file_path:
                                # Check if file was read (using our early validation tracking)
                                if file_path not in self.read_files_tracker and file_path not in self.read_files_persistent:
                                    # This should have been caught by early detection, but double-check
                                    print(f"\n🚨 CODER: ERROR - File '{file_path}' not read before update!")
                                    print("⚠️ CODER: This should have been caught by early detection!")
                                    continue
                                else:
                                    print(f"\n🚨 CODER: INTERRUPT - Detected update_file action for {file_path}")
                                    should_interrupt = True
                                    interrupt_action = action
                                    print("⚡ CODER: Breaking from action loop for update_file")
                                    break
                        elif action_type == 'rename_file':
                            old_path = action.get('path')
                            new_name = action.get('new_name')
                            print(f"\n🚨 CODER: INTERRUPT - Detected rename_file action: {old_path} -> {new_name}")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for rename_file")
                            break
                        elif action_type == 'delete_file':
                            file_path = action.get('path')
                            print(f"\n🚨 CODER: INTERRUPT - Detected delete_file action for {file_path}")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for delete_file")
                            break
                        elif action_type == 'start_backend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected start_backend action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for start_backend")
                            break
                        elif action_type == 'start_frontend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected start_frontend action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for start_frontend")
                            break
                        elif action_type == 'restart_backend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected restart_backend action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for restart_backend")
                            break
                        elif action_type == 'restart_frontend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected restart_frontend action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for restart_frontend")
                            break
                        elif action_type == 'check_errors':
                            print(f"\n🚨 CODER: INTERRUPT - Detected check_errors action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for check_errors")
                            break
                        elif action_type.startswith('todo_'):
                            print(f"\n📋 CODER: Processing todo action inline: {action_type}")
                            # Process todo actions inline without interrupting
                            if hasattr(self, '_handle_todo_actions'):
                                self._handle_todo_actions(action)
                            else:
                                print(f"📋 CODER: Todo action {action_type} - system doesn't support todos")
                            
                            # For todo_complete, we should interrupt AFTER processing to prompt continuation
                            if action_type == 'todo_complete':
                                print(f"\n🚨 CODER: INTERRUPT - todo_complete processed, need continuation prompt")
                                should_interrupt = True
                                interrupt_action = action
                                interrupt_action['already_processed'] = True  # Mark that we already handled the action
                                print("⚡ CODER: Breaking from action loop for todo_complete")
                                break
                            # Other todo actions don't interrupt
                    
                    if should_interrupt:
                        print("🛑 CODER: Interrupt flag set, breaking from chunk processing loop")
                        break
            
            print(f"\n🏁 CODER: Finished processing chunks. Total chunks: {chunk_count}")
            print(f"📊 CODER: Accumulated content length: {len(accumulated_content)} chars")
            print(f"📝 CODER: Adding to full_response (current length: {len(full_response)})")
            
            full_response += accumulated_content
            print(f"📈 CODER: New full_response length: {len(full_response)} chars")
            
            # Check interrupt status
            print(f"🔍 CODER: Checking interrupt status...")
            print(f"   should_interrupt: {should_interrupt}")
            print(f"   interrupt_action: {interrupt_action}")
            
            # If we detected a read_file or run_command action, process it and continue
            if should_interrupt and interrupt_action:
                action_type = interrupt_action.get('type')
                print(f"\n🚨 CODER: PROCESSING INTERRUPT - Action type: {action_type}")
                if interrupt_action.get('type') == 'read_file':
                    file_path = interrupt_action.get('path')
                    print(f"📖 CODER: Handling read_file interrupt for: {file_path}")
                    file_content = self._handle_read_file_interrupt(interrupt_action)
                    if file_content is not None:
                        print(f"✅ CODER: Successfully read file, content length: {len(file_content)} chars")
                        # Add the read file content to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"File content for {interrupt_action.get('path')}:\n\n```\n{file_content}\n```\n\nPlease continue with your response based on this file content."}
                        
                        print(f"📤 CODER: Adding assistant message ({len(assistant_msg['content'])} chars) to messages")
                        print(f"📤 CODER: Adding user message ({len(user_msg['content'])} chars) to messages")
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        print("💾 CODER: Adding messages to conversation history")
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        print(f"🔄 CODER: Continuing iteration with {len(messages)} total messages")
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
                elif interrupt_action.get('type') == 'start_backend':
                    service_result = self._handle_start_backend_interrupt(interrupt_action)
                    if service_result is not None:
                        # Add the service result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"Backend service started successfully on port {service_result.get('backend_port')}. API available at {service_result.get('api_url')}. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to start backend service, passing error to model for fixing")
                        # Pass the error back to the model so it can fix the issues
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"❌ Backend failed to start. There are errors that need to be fixed before the backend can run. Please investigate and fix the backend errors, then try starting the backend again. Use check_errors or read relevant files to identify and resolve the issues."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'start_frontend':
                    service_result = self._handle_start_frontend_interrupt(interrupt_action)
                    if service_result is not None:
                        # Add the service result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"Frontend service started successfully on port {service_result.get('frontend_port')}. Available at {service_result.get('frontend_url')}. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to start frontend service, passing error to model for fixing")
                        # Pass the error back to the model so it can fix the issues
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"❌ Frontend failed to start. There may be errors that need to be fixed before the frontend can run. Please investigate and fix any frontend errors, then try starting the frontend again. Use check_errors or read relevant files to identify and resolve the issues."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'restart_backend':
                    service_result = self._handle_restart_backend_interrupt(interrupt_action)
                    if service_result is not None:
                        # Add the service result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"Backend service restarted successfully on port {service_result.get('backend_port')}. API available at {service_result.get('api_url')}. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to restart backend service, passing error to model for fixing")
                        # Pass the error back to the model so it can fix the issues
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"❌ Backend restart failed. There are likely errors that need to be fixed before the backend can run. Please investigate and fix the backend errors, then try restarting the backend again. Use check_errors or read relevant files to identify and resolve the issues."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'restart_frontend':
                    service_result = self._handle_restart_frontend_interrupt(interrupt_action)
                    if service_result is not None:
                        # Add the service result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"Frontend service restarted successfully on port {service_result.get('frontend_port')}. Available at {service_result.get('frontend_url')}. Please continue with your response."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to restart frontend service, passing error to model for fixing")
                        # Pass the error back to the model so it can fix the issues
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        user_msg = {"role": "user", "content": f"❌ Frontend restart failed. There may be errors that need to be fixed before the frontend can run. Please investigate and fix any frontend errors, then try restarting the frontend again. Use check_errors or read relevant files to identify and resolve the issues."}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                elif interrupt_action.get('type') == 'check_errors':
                    error_check_result = self._handle_check_errors_interrupt(interrupt_action)
                    if error_check_result is not None:
                        # Add the error check result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        
                        # Format the error results into a readable message
                        backend_status = "✅ No errors" if error_check_result.get('summary', {}).get('backend_has_errors', True) == False else f"❌ {error_check_result.get('backend', {}).get('error_count', 0)} errors"
                        frontend_status = "✅ No errors" if error_check_result.get('summary', {}).get('frontend_has_errors', True) == False else f"❌ {error_check_result.get('frontend', {}).get('error_count', 0)} errors"
                        
                        error_summary = f"""Error Check Results:
📊 Overall Status: {error_check_result.get('summary', {}).get('overall_status', 'unknown')}
🐍 Backend: {backend_status}
⚛️  Frontend: {frontend_status}
📈 Total Errors: {error_check_result.get('summary', {}).get('total_errors', 0)}

"""
                        
                        # Add detailed errors if any
                        if error_check_result.get('backend', {}).get('errors'):
                            error_summary += f"🐍 **Backend Errors:**\n```\n{error_check_result['backend']['errors'][:1000]}\n```\n\n"
                        
                        if error_check_result.get('frontend', {}).get('errors'):
                            error_summary += f"⚛️  **Frontend Errors:**\n```\n{error_check_result['frontend']['errors'][:1000]}\n```\n\n"
                        
                        error_summary += "Please fix any critical errors and continue with your response."
                        
                        user_msg = {"role": "user", "content": error_summary}
                        
                        messages.append(assistant_msg)
                        messages.append(user_msg)
                        
                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(user_msg)
                        
                        continue
                    else:
                        print(f"❌ Failed to run error check, stopping generation")
                        break
                elif interrupt_action.get('type') == 'todo_complete':
                    # Todo was already processed inline, just need to prompt continuation
                    print(f"✅ CODER: Todo completion processed, prompting continuation")
                    
                    # Get current todo status to show what's next
                    todo_status = self._display_todos()
                    
                    # Add messages to prompt continuation
                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    user_msg = {"role": "user", "content": f"Great! You've completed a todo. Here's the current todo status:\n\n{todo_status}\n\nPlease continue with the next highest priority task."}
                    
                    messages.append(assistant_msg)
                    messages.append(user_msg)
                    
                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self.conversation_history.append(user_msg)
                    
                    continue
            else:
                # No interruption, process any remaining actions and finish
                print("🎬 CODER: No interrupt detected, processing remaining actions...")
                print(f"📝 CODER: Processing remaining actions with {len(accumulated_content)} chars of content")
                self._process_remaining_actions(accumulated_content)
                
                # Check if we have an incomplete action (opened but not closed)
                has_incomplete_action = False
                if '<action' in accumulated_content and accumulated_content.rfind('<action') > accumulated_content.rfind('</action>'):
                    has_incomplete_action = True
                    print("⚠️ CODER: Detected incomplete action tag - stream was likely cut off")
                
                # Check if we only created todos without doing any actual work
                todos_created_without_work = False
                if 'todo_create' in accumulated_content:
                    # Parse to check what actions were in this response
                    temp_parser = StreamingXMLParser()
                    temp_actions = list(temp_parser.process_chunk(accumulated_content))
                    
                    todo_creates = [a for a in temp_actions if a.get('type') == 'todo_create']
                    work_actions = [a for a in temp_actions if a.get('type') in ['file', 'update_file', 'run_command', 'todo_update']]
                    
                    # If we created todos but didn't do any work
                    if todo_creates and not work_actions:
                        todos_created_without_work = True
                        print(f"📋 CODER: Created {len(todo_creates)} todos but no work actions found")
                
                # Check if response contains non-implementation tags (like artifact, planning, etc)
                non_implementation_response = False
                if any(tag in accumulated_content for tag in ['<artifact', '<planning>', '<thinking>']):
                    # Check if there are any actual implementation actions
                    temp_parser = StreamingXMLParser()
                    temp_actions = list(temp_parser.process_chunk(accumulated_content))
                    implementation_actions = [a for a in temp_actions if a.get('type') in ['file', 'update_file', 'run_command']]
                    
                    if not implementation_actions:
                        non_implementation_response = True
                        print("📄 CODER: Response contains only planning/artifact tags without implementation")
                
                if has_incomplete_action:
                    # Add a message to prompt continuation
                    print("🔄 CODER: Prompting model to continue incomplete action")
                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    user_msg = {"role": "user", "content": "The previous response was cut off. Please continue from where you left off to complete the file action."}
                    
                    messages.append(assistant_msg)
                    messages.append(user_msg)
                    
                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self.conversation_history.append(user_msg)
                    
                    print("🔄 CODER: Continuing iteration to complete the action")
                    continue
                elif todos_created_without_work:
                    # Prompt to start working on the todos that were just created
                    print("🔄 CODER: Todos created without implementation - prompting to start work")
                    
                    # Get current todo status
                    todo_status = self._display_todos()
                    
                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    user_msg = {"role": "user", "content": f"Good! You've created the todos. Here's the current status:\n\n{todo_status}\n\nNow please start implementing the highest priority todo. Remember to:\n1. Update the todo status to 'in_progress' using todo_update\n2. Create/modify the necessary files\n3. Test your implementation\n4. Mark the todo as completed when done"}
                    
                    messages.append(assistant_msg)
                    messages.append(user_msg)
                    
                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self.conversation_history.append(user_msg)
                    
                    print("🔄 CODER: Continuing iteration to implement todos")
                    continue
                elif non_implementation_response:
                    # Response only contains planning/artifacts without actual implementation
                    print("🔄 CODER: Planning/artifact only response - prompting for implementation")
                    
                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    user_msg = {"role": "user", "content": "Good planning! Now please proceed with the actual implementation. Start creating or modifying the necessary files to implement what you've planned."}
                    
                    messages.append(assistant_msg)
                    messages.append(user_msg)
                    
                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self.conversation_history.append(user_msg)
                    
                    print("🔄 CODER: Continuing iteration to implement the plan")
                    continue
                else:
                    print("✅ CODER: Finished processing remaining actions, breaking from iteration loop")
                    break
    
        except Exception as e:
            print(f"❌ CODER: Exception during generation in iteration {iteration}: {e}")
            print(f"🔍 CODER: Exception type: {type(e).__name__}")
            import traceback
            print("📚 CODER: Full traceback:")
            traceback.print_exc()
            break
    
    print(f"\n🏁 CODER: Completed iteration loop after {iteration} iterations")
    print(f"📊 CODER: Final full_response length: {len(full_response)} chars")
    
    
    # Add current project errors as context at the end of generation
    print("🔍 -- CHECKING FOR ERRORS -----\n")
    project_errors = _get_project_errors(self)
    if project_errors:
        print(f"⚠️ CODER: Found project errors ({len(project_errors)} chars), adding to context")
        error_msg = {"role": "user", "content": f"Current codebase errors:\n\n{project_errors}\n\nNote: Fix critical errors if needed, otherwise continue with main task."}
        messages.append(error_msg)
        self.conversation_history.append(error_msg)
        print('---- CHECKING FOR ERRORS -----\n')
        print("📤 CODER: Added error context to messages and conversation history")
    else:
        print("✅ CODER: No project errors found")
    
    
    print(f"🎉 CODER: Returning full_response with {len(full_response)} chars")
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

