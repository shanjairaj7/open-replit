from shared_models import StreamingXMLParser, GroqAgentState
import json
import os
from datetime import datetime
from action_registry import action_registry
from conversation_manager import ConversationManager

def coder(messages, self: GroqAgentState):
    print("🚀 CODER: Starting coder() function")
    print(f"📊 CODER: Input - {len(messages)} messages, max_iterations=100")
    
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
        
        # Add current todo status as context
        print("🔍 CODER: Checking for todo status...")
        todo_status = self._display_todos()
        if todo_status:
            ConversationManager.add_todo_context(messages, self.conversation_history, todo_status)
        else:
            print("✅ CODER: No todo status found")
        
        try:
            print("🔌 CODER: Creating streaming completion...")
            # Create streaming response
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=16000,
                stream=True,
                stream_options={"include_usage": "true"}
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
            update_file_validated = False
            
            # Token tracking
            final_chunk = None
            
            print("🌊 CODER: Starting to process streaming chunks...")
            chunk_count = 0
            
            for chunk in completion:
                chunk_count += 1
                final_chunk = chunk  # Keep track of last chunk for token usage
                
                # Check for usage information in chunk
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    print(f"💰 CODER: Found usage info in chunk {chunk_count}")
                    _update_token_usage(self, chunk.usage)
                
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        print(content, end='', flush=True)
                        accumulated_content += content
                    
                    # Early detection: Check for update_file action start
                    if not update_file_detected and '<action type="update_file"' in accumulated_content:
                        update_file_detected = True
                        update_file_buffer = accumulated_content
                        print(f"\n🚨 CODER: EARLY DETECTION - Found update_file action, waiting for path...")
                    
                    # Improved early detection: Check for complete file creation action
                    if '<action type="file"' in accumulated_content and '</action>' in accumulated_content:
                        print(f"🔧 DEBUG: Found file action tags, validating...")
                        temp_parser = StreamingXMLParser()
                        temp_actions = list(temp_parser.process_chunk(accumulated_content))
                        
                        file_actions = [action for action in temp_actions if action.get('type') == 'file']
                        
                        if file_actions:
                            print(f"\n🚨 CODER: COMPLETE FILE ACTION VALIDATED - Creating {len(file_actions)} file(s) immediately...")
                            should_interrupt = True
                            interrupt_action = {
                                'type': 'create_file_realtime',
                                'content': accumulated_content,
                                'validated_actions': file_actions
                            }
                            break
                    
                    # If we detected update_file, check for early file read validation
                    if update_file_detected and not update_file_validated:
                        import re
                        path_match = re.search(r'(?:path|filePath)="([^"]*)"', accumulated_content)
                        if path_match:
                            file_path = path_match.group(1)
                            print(f"\n🎯 CODER: Found file path in update_file: {file_path}")
                            
                            # Check if this file has been read
                            if file_path not in self.read_files_tracker and file_path not in self.read_files_persistent:
                                print(f"\n🚨 CODER: INTERRUPT REQUIRED - File '{file_path}' needs to be read first!")
                                should_interrupt = True
                                interrupt_action = {'type': 'read_file', 'path': file_path}
                                update_file_validated = True
                                break
                            else:
                                print(f"\n✅ CODER: File '{file_path}' was previously read, update allowed")
                                update_file_validated = True
                    
                    # Check for actions using the registry
                    actions = list(parser.process_chunk(content))
                    for action in actions:
                        should_interrupt, interrupt_action = action_registry.process_action_detection(action, self)
                        if should_interrupt:
                            print(f"\n🚨 CODER: INTERRUPT - Detected {action.get('type')} action")
                            break
                    
                    if should_interrupt:
                        print("🛑 CODER: Interrupt flag set, breaking from chunk processing loop")
                        break
            
            print(f"\n🏁 CODER: Finished processing chunks. Total chunks: {chunk_count}")
            print(f"📊 CODER: Accumulated content length: {len(accumulated_content)} chars")
            
            full_response += accumulated_content
            print(f"📈 CODER: New full_response length: {len(full_response)} chars")
            
            # Process interrupt if needed
            if should_interrupt and interrupt_action:
                if _process_interrupt(self, interrupt_action, accumulated_content, messages):
                    continue  # Continue the iteration loop
                else:
                    break  # Stop if interrupt processing failed
            else:
                # No interruption, process any remaining actions and check for continuation needs
                print("🎬 CODER: No interrupt detected, processing remaining actions...")
                self._process_remaining_actions(accumulated_content)
                
                # Check various conditions that require continuation
                if _check_continuation_needed(accumulated_content, messages, self):
                    continue
                else:
                    print("✅ CODER: Finished processing, breaking from iteration loop")
                    break
    
        except Exception as e:
            print(f"❌ CODER: Exception during generation in iteration {iteration}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n🏁 CODER: Completed iteration loop after {iteration} iterations")
    print(f"📊 CODER: Final full_response length: {len(full_response)} chars")
    
    # Add current project errors as context at the end
    _add_project_errors_context(messages, self)
    
    print(f"🎉 CODER: Returning full_response with {len(full_response)} chars")
    return full_response


def _process_interrupt(self: GroqAgentState, interrupt_action: dict, accumulated_content: str, messages: list) -> bool:
    """
    Process an interrupt action using the registry
    Returns True if iteration should continue, False if it should break
    """
    action_type = interrupt_action.get('type')
    print(f"\n🚨 CODER: PROCESSING INTERRUPT - Action type: {action_type}")
    
    # Get handler method from registry
    handler_method = action_registry.get_handler_method(action_type)
    if not handler_method or not hasattr(self, handler_method):
        print(f"❌ CODER: No handler found for action type: {action_type}")
        return False
    
    # Call the handler
    handler = getattr(self, handler_method)
    result = handler(interrupt_action)
    
    # Handle special cases
    if action_type == 'read_file':
        if result is not None:
            print(f"✅ CODER: Successfully read file, content length: {len(result)} chars")
            user_content = f"File content for {interrupt_action.get('path')}:\n\n```\n{result}\n```\n\nPlease continue with your response based on this file content."
            ConversationManager.create_continuation_messages(accumulated_content, user_content, messages, self.conversation_history)
            return True
        else:
            # Pass read error back to model
            file_path = interrupt_action.get('path', 'unknown')
            error_msg = action_registry.get_error_message('read_file', path=file_path)
            ConversationManager.create_continuation_messages(accumulated_content, error_msg, messages, self.conversation_history)
            return True
    
    elif action_type == 'create_file_realtime':
        if result is not None:
            file_path = result.get('file_path')
            print(f"✅ Created file: {file_path}")
            
            # Mark file as read since we just created it
            self.read_files_tracker.add(file_path)
            self.read_files_persistent.add(file_path)
            self._save_read_files_tracking()
            
            ConversationManager.handle_create_file_result(result, accumulated_content, messages, self.conversation_history)
            return True
    
    elif action_type == 'check_errors':
        if result is not None:
            ConversationManager.handle_check_errors_result(result, accumulated_content, messages, self.conversation_history)
            return True
    
    elif action_type == 'todo_complete':
        # Todo was already processed inline
        todo_status = self._display_todos()
        ConversationManager.handle_todo_complete(todo_status, accumulated_content, messages, self.conversation_history)
        return True
    
    # For all other action types, use generic continuation message
    elif result is not None:
        # Build kwargs for message template
        kwargs = {'path': interrupt_action.get('path', '')}
        if action_type == 'run_command':
            kwargs.update({
                'command': interrupt_action.get('command'),
                'cwd': interrupt_action.get('cwd'),
                'result': result
            })
        elif action_type == 'rename_file':
            kwargs['new_name'] = interrupt_action.get('new_name')
        elif action_type.startswith('start_') or action_type.startswith('restart_'):
            if 'backend' in action_type:
                kwargs.update({
                    'backend_port': result.get('backend_port'),
                    'api_url': result.get('api_url')
                })
            else:
                kwargs.update({
                    'frontend_port': result.get('frontend_port'),
                    'frontend_url': result.get('frontend_url')
                })
        
        # Get and use continuation message
        continue_msg = action_registry.get_continue_message(action_type, **kwargs)
        if continue_msg:
            ConversationManager.create_continuation_messages(accumulated_content, continue_msg, messages, self.conversation_history)
            return True
    else:
        # Handler returned None - check for error message
        error_msg = action_registry.get_error_message(action_type, path=interrupt_action.get('path', 'unknown'))
        if error_msg:
            ConversationManager.create_continuation_messages(accumulated_content, error_msg, messages, self.conversation_history)
            return True
        else:
            print(f"❌ Failed to handle {action_type}, stopping generation")
            return False
    
    return False


def _update_token_usage(self: GroqAgentState, usage) -> None:
    """Update token usage tracking"""
    if hasattr(usage, 'total_tokens'):
        print(f"\n📈 Usage Statistics:")
        print(f"Total Tokens: {usage.total_tokens}")
        print(f"Prompt Tokens: {usage.prompt_tokens}")
        print(f"Completion Tokens: {usage.completion_tokens}")
        
        old_total = self.token_usage.get('total_tokens', 0)
        
        # Update token tracking
        self.token_usage['total_tokens'] += usage.total_tokens
        self.token_usage['prompt_tokens'] += usage.prompt_tokens
        self.token_usage['completion_tokens'] += usage.completion_tokens
        self.token_usage['total_prompt_tokens'] += usage.prompt_tokens
        self.token_usage['total_completion_tokens'] += usage.completion_tokens
        
        new_total = self.token_usage['total_tokens']
        print(f"💰 Total: {old_total:,} → {new_total:,} tokens")


def _check_continuation_needed(accumulated_content: str, messages: list, self: GroqAgentState) -> bool:
    """
    Check if we need to continue the iteration loop
    Returns True if continuation is needed, False otherwise
    """
    # Check if we have an incomplete action
    if '<action' in accumulated_content and accumulated_content.rfind('<action') > accumulated_content.rfind('</action>'):
        print("⚠️ CODER: Detected incomplete action tag - stream was likely cut off")
        assistant_msg = {"role": "assistant", "content": accumulated_content}
        user_msg = {"role": "user", "content": "The previous response was cut off. Please continue from where you left off to complete the file action."}
        messages.extend([assistant_msg, user_msg])
        self.conversation_history.extend([assistant_msg, user_msg])
        return True
    
    # Check if we only created todos without doing any actual work
    if 'todo_create' in accumulated_content:
        temp_parser = StreamingXMLParser()
        temp_actions = list(temp_parser.process_chunk(accumulated_content))
        
        todo_creates = [a for a in temp_actions if a.get('type') == 'todo_create']
        work_actions = [a for a in temp_actions if a.get('type') in ['file', 'update_file', 'run_command', 'todo_update']]
        
        if todo_creates and not work_actions:
            print(f"📋 CODER: Created {len(todo_creates)} todos but no work actions found")
            todo_status = self._display_todos()
            assistant_msg = {"role": "assistant", "content": accumulated_content}
            user_msg = {"role": "user", "content": f"Good! You've created the todos. Here's the current status:\n\n{todo_status}\n\nNow please start implementing the highest priority todo. Remember to:\n1. Update the todo status to 'in_progress' using todo_update\n2. Create/modify the necessary files\n3. Test your implementation\n4. Mark the todo as completed when done"}
            messages.extend([assistant_msg, user_msg])
            self.conversation_history.extend([assistant_msg, user_msg])
            return True
    
    # Check if response contains non-implementation tags
    if any(tag in accumulated_content for tag in ['<artifact', '<planning>', '<thinking>']):
        temp_parser = StreamingXMLParser()
        temp_actions = list(temp_parser.process_chunk(accumulated_content))
        implementation_actions = [a for a in temp_actions if a.get('type') in ['file', 'update_file', 'run_command']]
        
        if not implementation_actions:
            print("📄 CODER: Response contains only planning/artifact tags without implementation")
            assistant_msg = {"role": "assistant", "content": accumulated_content}
            user_msg = {"role": "user", "content": "Good planning! Now please proceed with the actual implementation. Start creating or modifying the necessary files to implement what you've planned."}
            messages.extend([assistant_msg, user_msg])
            self.conversation_history.extend([assistant_msg, user_msg])
            return True
    
    return False


def _add_project_errors_context(messages: list, self: GroqAgentState) -> None:
    """Add current project errors as context if any exist"""
    print("🔍 -- CHECKING FOR ERRORS -----\n")
    project_errors = _get_project_errors(self)
    if project_errors:
        print(f"⚠️ CODER: Found project errors ({len(project_errors)} chars), adding to context")
        error_msg = {"role": "user", "content": f"Current codebase errors:\n\n{project_errors}\n\nNote: Fix critical errors if needed, otherwise continue with main task."}
        messages.append(error_msg)
        self.conversation_history.append(error_msg)
        print('---- CHECKING FOR ERRORS -----\n')
    else:
        print("✅ CODER: No project errors found")


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


def _log_coder_call(messages, self):
    """Log exact messages and token count at each coder() call"""
    try:
        # Create logs directory
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'coder_call_logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        project_id = getattr(self, 'project_id', 'unknown')
        filename = f"coder_call_{project_id}_{timestamp}"
        
        # Current token usage
        current_tokens = getattr(self, 'token_usage', {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0})
        
        # Calculate approximate input tokens
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