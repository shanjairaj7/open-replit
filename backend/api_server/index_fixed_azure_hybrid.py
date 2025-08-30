from shared_models import StreamingXMLParser, GroqAgentState
import json
import os
from datetime import datetime
import re

class StreamingXMLFilter:
    """Smart filter to exclude XML action tags from streaming content"""

    def __init__(self):
        self.buffer = ""
        self.inside_action_tag = False
        self.pending_output = ""

    def process_chunk(self, content: str) -> str:
        """
        Process a streaming chunk and return filtered content.
        Filters out XML action tags but keeps content inside them.
        """
        self.buffer += content
        result = ""

        # Process the buffer looking for complete patterns
        i = 0
        while i < len(self.buffer):
            if not self.inside_action_tag:
                # Look for start of action tag
                if self.buffer[i:].startswith('<action'):
                    # Found opening action tag, find the end
                    tag_end = self.buffer.find('>', i)
                    if tag_end == -1:
                        # Tag not complete, keep remaining in buffer
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Skip the opening tag completely
                        self.inside_action_tag = True
                        i = tag_end + 1
                elif self.buffer[i] == '<' and len(self.buffer[i:]) < 7:
                    # Check if this could possibly be <action
                    remaining = self.buffer[i:].lower()
                    if '<action'.startswith(remaining):
                        # Might be start of <action but not enough chars yet
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Not a potential <action tag, include the character
                        result += self.buffer[i]
                        i += 1
                else:
                    # Regular character, add to result
                    result += self.buffer[i]
                    i += 1
            else:
                # We're inside action tag, look for closing tag
                if self.buffer[i:].startswith('</action>'):
                    # Found complete closing tag
                    self.inside_action_tag = False
                    i += 9  # Skip '</action>'
                elif self.buffer[i] == '<' and len(self.buffer[i:]) < 9:
                    # Check if this could possibly be </action>
                    remaining = self.buffer[i:].lower()
                    if '</action>'.startswith(remaining):
                        # Might be closing tag but not enough chars yet
                        self.buffer = self.buffer[i:]
                        return result
                    else:
                        # Not a potential </action> tag, include the character
                        result += self.buffer[i]
                        i += 1
                else:
                    # Content inside action tag, include it
                    result += self.buffer[i]
                    i += 1

        # Clear buffer since we processed everything
        self.buffer = ""
        return result

def _create_error_fingerprint(log_line: str) -> str:
    """Create a unique fingerprint for an error, ignoring timestamps and variable details"""
    import hashlib
    import re

    # Extract the core error message, removing timestamps and variable parts
    # Remove timestamps like [2025-08-13T07:17:21.308Z]
    cleaned = re.sub(r'\[[\d\-T:\.Z]+\]', '', log_line)
    # Remove line numbers and specific file paths that change
    cleaned = re.sub(r':\d+:\d+', ':XX:XX', cleaned)
    # Remove specific URLs that might have ports/timestamps
    cleaned = re.sub(r'http://localhost:\d+', 'http://localhost:PORT', cleaned)
    # Remove cache busters like ?v=0d702775
    cleaned = re.sub(r'\?v=[a-f0-9]+', '?v=HASH', cleaned)

    # Convert to lowercase and create hash
    return hashlib.md5(cleaned.lower().strip().encode()).hexdigest()[:8]

def _handle_attempt_completion_interrupt(self: GroqAgentState, action: dict, accumulated_content: str) -> dict:
    """Handle attempt_completion action - ends the session with completion message

    Handles multiple formats:
    1. <action type="attempt_completion">content</action>
    2. Plain text "attempt_completion"
    3. Other variations in action structure
    """
    print(f"🎯 Processing attempt completion...")

    try:
        completion_message = ""

        # Method 1: Extract from action content directly
        if action.get('content'):
            completion_message = action.get('content', '').strip()
            print(f"📄 Method 1 - Found content in action: {len(completion_message)} chars")

        # Method 2: Extract from action text (for different parser results)
        if not completion_message and action.get('text'):
            completion_message = action.get('text', '').strip()
            print(f"📄 Method 2 - Found text in action: {len(completion_message)} chars")

        # Method 3: Extract from raw XML action tag in accumulated content
        if not completion_message and accumulated_content:
            import re
            # Look for <action type="attempt_completion">content</action>
            action_match = re.search(r'<action[^>]*type="attempt_completion"[^>]*>(.*?)</action>', accumulated_content, re.DOTALL | re.IGNORECASE)
            if action_match:
                completion_message = action_match.group(1).strip(' \t')  # Keep newlines, remove only spaces/tabs
                print(f"📄 Method 3 - Extracted from XML action tag: {len(completion_message)} chars")

            # Look for other attempt_completion patterns in content
            elif 'attempt_completion' in accumulated_content.lower():
                # Try to extract content after attempt_completion markers
                lines = accumulated_content.split('\n')
                capture_content = False
                captured_lines = []

                for line in lines:
                    line_lower = line.lower()
                    if 'attempt_completion' in line_lower:
                        capture_content = True
                        # Skip the line with the marker itself unless it has substantial content
                        if len(line.strip()) > len('attempt_completion') + 20:  # Has more than just the marker
                            captured_lines.append(line.strip())
                    elif capture_content:
                        # Stop capturing if we hit another action or XML tag
                        if line.strip().startswith('<') or 'type=' in line:
                            break
                        if line.strip():  # Non-empty line
                            captured_lines.append(line.strip())

                if captured_lines:
                    completion_message = '\n'.join(captured_lines).strip()
                    print(f"📄 Method 4 - Extracted from content patterns: {len(completion_message)} chars")

        # Method 5: Extract from different action formats that parsers might create
        if not completion_message:
            # Check for nested content in action details
            details = action.get('action_details', {}) or action.get('actionDetails', {})
            if details and isinstance(details, dict):
                completion_message = details.get('content', '') or details.get('message', '')
                if completion_message:
                    print(f"📄 Method 5 - Found in action details: {len(completion_message)} chars")

        # Method 6: Look for completion message in action raw attributes
        if not completion_message:
            raw_attrs = action.get('raw_attrs', {})
            if raw_attrs and isinstance(raw_attrs, dict):
                completion_message = raw_attrs.get('content', '') or raw_attrs.get('message', '')
                if completion_message:
                    print(f"📄 Method 6 - Found in raw attributes: {len(completion_message)} chars")

        # Clean up the completion message
        if completion_message:
            # Remove XML tags if they're still present
            completion_message = re.sub(r'<[^>]+>', '', completion_message)
            # Clean up extra whitespace but preserve line breaks
            # Only collapse spaces/tabs, not newlines
            completion_message = re.sub(r'[ \t]+', ' ', completion_message)
            # Remove leading/trailing whitespace from each line but preserve line structure
            lines = completion_message.split('\n')
            lines = [line.strip() for line in lines]
            completion_message = '\n'.join(lines).strip()

        # Fallback to default message
        if not completion_message:
            completion_message = "Task completed successfully."
            print(f"📄 Using fallback completion message")

        print(f"📝 Final completion message ({len(completion_message)} chars): {completion_message[:100]}...")

        # Create completion result
        result = {
            'success': True,
            'message': completion_message,
            'session_ended': True,
            'timestamp': datetime.now().isoformat()
        }

        print(f"✅ Attempt completion processed successfully")
        return result

    except Exception as e:
        print(f"❌ Error processing attempt completion: {e}")
        return {
            'success': False,
            'error': f"Failed to process completion: {str(e)}",
            'message': 'Task completion failed',
            'session_ended': False
        }

def _handle_check_logs_interrupt(self: GroqAgentState, interrupt_action: dict) -> dict:
    """Handle check_logs interrupt by fetching logs from the API"""
    try:
        print(f"🐛 DEBUG: interrupt_action = {interrupt_action}")

        # Check both top level and raw_attrs for service parameter (parser inconsistency)
        # Empty strings are falsy, so we need to explicitly check for them
        service = interrupt_action.get('service')
        if not service:  # Empty string or None
            service = interrupt_action.get('raw_attrs', {}).get('service', 'backend')

        new_only = interrupt_action.get('new_only')
        if not new_only:  # Empty string or None
            new_only = interrupt_action.get('raw_attrs', {}).get('new_only', True)

        print(f"🐛 DEBUG: Extracted service='{service}', new_only='{new_only}'")

        # Handle string boolean conversion for new_only
        if isinstance(new_only, str):
            new_only = new_only.lower() in ('true', '1', 'yes')
        elif new_only is True:
            new_only = True
        else:
            new_only = True  # Default fallback

        print(f"📋 Fetching {service} logs (new_only={new_only})")

        # Get project ID from context
        project_id = getattr(self, 'project_id', None)
        if not project_id:
            print("❌ No project ID available for check_logs")
            return None

        # Call the check_logs API
        api_base_url = getattr(self, 'api_base_url', 'http://localhost:8000')
        if api_base_url.endswith('/api'):
            api_base_url = api_base_url[:-4]

        logs_url = f"{api_base_url}/api/projects/{project_id}/check-logs"

        # ALWAYS get full logs first to ensure we have content
        params = {
            'service': service,
            'include_new_only': False  # Always get full logs
        }

        import requests
        response = requests.get(logs_url, params=params, timeout=10)

        if response.status_code == 200:
            logs_data = response.json()
            logs_content = logs_data.get('logs', '')

            # For frontend logs, return only logs after the last checkpoint (new errors only)
            if service == 'frontend' and logs_content and logs_content.strip():
                lines = logs_content.split('\n')

                # Find the last checkpoint to get only NEW logs after model's last view
                last_checkpoint_index = -1
                checkpoint_lines = []

                for i, line in enumerate(lines):
                    if line.strip().startswith('<!-- CHECKPOINT:'):
                        last_checkpoint_index = i
                        checkpoint_lines.append(line)

                if last_checkpoint_index >= 0:
                    # Get only logs AFTER the last checkpoint (new activity)
                    new_logs_after_checkpoint = lines[last_checkpoint_index + 1:]
                    # Filter out empty lines
                    new_logs_after_checkpoint = [line for line in new_logs_after_checkpoint if line.strip()]

                    if new_logs_after_checkpoint:
                        # Return only NEW logs since last checkpoint
                        new_logs_content = '\n'.join(new_logs_after_checkpoint)

                        # Include the service status from the last checkpoint for context
                        last_checkpoint = checkpoint_lines[-1] if checkpoint_lines else ""
                        service_status_info = f"Service Status: Last checkpoint - {last_checkpoint}\n\nNew activity since checkpoint:\n{new_logs_content}" if new_logs_content else f"Service Status: {last_checkpoint}\n\nNo new activity since last checkpoint."

                        logs_data['logs'] = service_status_info
                        logs_data['total_lines'] = len(lines)
                        logs_data['new_lines'] = len(new_logs_after_checkpoint)

                        print(f"✅ Successfully fetched {service} logs: {len(new_logs_after_checkpoint)} NEW lines since last checkpoint")
                        return logs_data
                    else:
                        # No new logs, just return checkpoint status
                        last_checkpoint = checkpoint_lines[-1] if checkpoint_lines else "No checkpoints found"
                        status_only = f"Service Status: {last_checkpoint}\n\nNo new activity since last checkpoint."

                        logs_data['logs'] = status_only
                        logs_data['total_lines'] = len(lines)
                        logs_data['new_lines'] = 0

                        print(f"✅ No new {service} activity since last checkpoint")
                        return logs_data
                else:
                    # No checkpoints found, return recent logs (last 50 lines)
                    clean_lines = [line for line in lines if line.strip()]
                    recent_logs = '\n'.join(clean_lines[-50:]) if len(clean_lines) > 50 else '\n'.join(clean_lines)

                    logs_data['logs'] = f"Service Status: No checkpoints found - showing recent activity:\n\n{recent_logs}"
                    logs_data['total_lines'] = len(clean_lines)
                    logs_data['new_lines'] = min(50, len(clean_lines))

                    print(f"✅ No checkpoints found for {service}, returning recent logs")
                    return logs_data

            # For backend logs, use the old logic (latest portion only)
            elif logs_content and logs_content.strip():
                lines = logs_content.split('\n')
                # Remove checkpoint lines
                clean_lines = [line for line in lines if not line.strip().startswith('<!-- CHECKPOINT:')]

                if clean_lines:
                    # Return latest half of logs (but at least 50 lines if available)
                    half_point = max(len(clean_lines) // 2, len(clean_lines) - 100)
                    latest_logs = '\n'.join(clean_lines[half_point:])

                    # Update the logs_data with the processed content
                    logs_data['logs'] = latest_logs
                    logs_data['total_lines'] = len(clean_lines)
                    logs_data['new_lines'] = len(clean_lines) - half_point

                    print(f"✅ Successfully fetched {service} logs: {len(clean_lines)} total lines, returning {len(clean_lines) - half_point} lines")
                    return logs_data
                else:
                    print(f"⚠️  No actual log content found for {service}")
                    return logs_data
            else:
                print(f"⚠️  Empty logs content for {service}")
                return logs_data
        else:
            print(f"❌ Failed to fetch logs: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error handling check_logs interrupt: {e}")
        return None

def coder(messages, self: GroqAgentState, streaming_callback=None):
    print("🚀 CODER: Starting coder() function")
    print(f"📊 CODER: Input - {len(messages)} messages, max_iterations=30")

    def _emit_stream(event_type: str, content: str, metadata: dict = None):
        """Helper function to emit streaming events"""
        if streaming_callback:
            try:
                streaming_callback(event_type, content, metadata or {})
            except Exception as e:
                print(f"⚠️ CODER: Streaming callback error: {e}")


    max_iterations = 200  # Prevent infinite loops
    iteration = 0
    full_response = ""

    print(f"🔄 CODER: Starting iteration loop (max: {max_iterations})")

    # Message accumulator that persists across iterations
    full_user_msg = ""

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"📝 CODER: Generation iteration {iteration}/{max_iterations}")
        print(f"📊 CODER: Current full_response length: {len(full_response)} chars")
        print(f"🎯 CODER: Using model: {self.model}")

        # Add accumulated messages from previous iteration (action results + todo status + service status)
        if full_user_msg.strip():
            print(f"📤 CODER: Adding accumulated context from previous iteration ({len(full_user_msg)} chars)")
            messages.append({"role": "user", "content": full_user_msg})
            self.conversation_history.append({"role": "user", "content": full_user_msg})
            self._save_conversation_history()  # Save after each iteration
            full_user_msg = ""  # Reset for this iteration



        print(f"📤 CODER: Sending {len(messages)} messages to API")

        try:
            print("🔌 CODER: Creating streaming completion...")
            # Create streaming response
            # Azure-compatible completion creation
            completion_params = {
                "model": self.model,
                "messages": self._get_filtered_conversation_history(),
                "temperature": 0.1,
                "stream": True,
                "stream_options": {"include_usage": True}
            }

            # Use max_completion_tokens for Azure, max_tokens for OpenRouter
            if hasattr(self, 'is_azure_mode') and self.is_azure_mode:
                completion_params["max_completion_tokens"] = 16000
            else:
                completion_params["max_tokens"] = 16000

            completion = self.client.chat.completions.create(**completion_params)
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

            # XML action tag filtering for assistant messages
            xml_filter = StreamingXMLFilter()
            buffer_xml_filter = StreamingXMLFilter()  # Separate filter for buffered content

            # Assistant message buffering to detect action tags
            assistant_buffer = ""
            assistant_chunks_processed = 0
            assistant_buffer_delay = 10  # Wait 10 chunks before streaming assistant content
            has_action_tags = False
            buffered_content_streamed = False  # Track if we've flushed buffered content

            # Token tracking
            final_chunk = None
            generation_id = None  # Track generation ID for usage query

            print("🌊 CODER: Starting to process streaming chunks...")
            chunk_count = 0

            for chunk in completion:
                chunk_count += 1
                final_chunk = chunk  # Keep track of last chunk for token usage

                # Capture generation ID from first chunk for separate usage query
                if generation_id is None and hasattr(chunk, 'id') and chunk.id:
                    generation_id = chunk.id
                    print(f"🆔 CODER: Captured generation ID: {generation_id}")

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
                        old_total = self.token_usage.get('total_tokens', 0)
                        self.token_usage['prompt_tokens'] += usage.prompt_tokens
                        self.token_usage['completion_tokens'] += usage.completion_tokens
                        self.token_usage['total_tokens'] += usage.total_tokens

                        print(f"💰 Running Total: {old_total:,} → {self.token_usage['total_tokens']:,} tokens")


                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = ""  # Initialize content variable

                    # Azure-specific: Handle reasoning content (for models that support it)
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        print(f"\n💭 THINKING: {delta.reasoning_content}", end='', flush=True)

                    # Process regular content
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        print(content, end='', flush=True)
                        accumulated_content += content

                        # Buffer assistant messages to detect action tags
                        assistant_buffer += content
                        assistant_chunks_processed += 1

                        # Check for action tags in accumulated content
                        if '<action' in assistant_buffer and not has_action_tags:
                            has_action_tags = True
                            print(f"\n🚫 CODER: Action tag detected in assistant message - will not stream assistant content")

                        # Stream assistant content based on buffer analysis
                        if not has_action_tags:
                            if assistant_chunks_processed == assistant_buffer_delay and not buffered_content_streamed:
                                # We've reached the buffer limit - flush all buffered content first
                                print(f"\n✅ CODER: No action tags detected after {assistant_buffer_delay} chunks - flushing buffered content")
                                # Process all buffered content through separate filter
                                buffered_filtered = buffer_xml_filter.process_chunk(assistant_buffer)
                                if buffered_filtered:
                                    _emit_stream("assistant_message", buffered_filtered)
                                buffered_content_streamed = True
                            elif assistant_chunks_processed > assistant_buffer_delay:
                                # We're past the buffer delay - stream all content immediately
                                filtered_content = xml_filter.process_chunk(content)
                                if filtered_content:
                                    _emit_stream("assistant_message", filtered_content)
                            else:
                                # Still buffering
                                if assistant_chunks_processed % 2 == 0:  # Only print every other chunk to reduce noise
                                    print(f"\n🔄 CODER: Buffering assistant content ({assistant_chunks_processed}/{assistant_buffer_delay} chunks)")
                        else:
                            # Has action tags - don't stream any assistant messages
                            # Still process through XML filter to maintain state but don't stream
                            xml_filter.process_chunk(content)

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

                            # Emit streaming event for file creation actions
                            for action in file_actions:
                                file_path = action.get('path', 'unknown')
                                _emit_stream("action_start", f"Creating file: {file_path}", {
                                    "action_type": "create_file",
                                    "file_path": file_path,
                                    "action_details": action
                                })

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

                                # Emit streaming event for read_file action
                                _emit_stream("action_start", f"Reading file: {file_path}", {
                                    "action_type": "read_file",
                                    "file_path": file_path
                                })

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

                    # Check for invalid XML tags first
                    invalid_tags = _detect_invalid_xml_tags(content)
                    if invalid_tags:
                        print(f"\n🚨 CODER: INVALID XML TAGS DETECTED: {invalid_tags}")
                        for invalid_tag in invalid_tags:
                            full_user_msg += f"""
<action_result type="invalid_tool_action">
❌ Invalid tool action detected: `{invalid_tag}`

**Available Action Tags:**
- `<action type="read_file" path="file/path"/>` - Read a file
- `<action type="file" filePath="path">content</action>` - Create new file
- `<action type="update_file" path="path">content</action>` - Update existing file
- `<action type="run_command" cwd="directory" command="command"/>` - Run terminal command
- `<action type="start_backend"/>` - Start backend service
- `<action type="check_errors"/>` - Check for project errors
- `<action type="ast_analyze" target="backend|frontend" focus="routes|imports|env|database|structure|all"/>` - Deep structural code analysis
- `<action type="todo_create" id="task_id" priority="high|medium|low">task description</action>` - Create todo
- `<action type="todo_update" id="task_id" status="in_progress|completed"/>` - Update todo status

Please use the correct action tags to perform actions based on your plan and the user's requirements.
</action_result>
"""

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

                            # Emit streaming event for read_file action
                            _emit_stream("action_start", f"Reading file: {file_path}", {
                                "action_type": "read_file",
                                "file_path": file_path,
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for read_file")
                            break
                        elif action_type == 'run_command':
                            command = action.get('command')
                            cwd = action.get('cwd')
                            print(f"\n🚨 CODER: INTERRUPT - Detected run_command action: {command} in {cwd}")

                            # Emit streaming event for run_command action
                            _emit_stream("action_start", f"Running command: {command}", {
                                "action_type": "run_command",
                                "command": command,
                                "cwd": cwd,
                                "action_details": action
                            })

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

                                    # Emit streaming event for update_file action
                                    _emit_stream("action_start", f"Updating file: {file_path}", {
                                        "action_type": "update_file",
                                        "file_path": file_path,
                                        "action_details": action
                                    })

                                    should_interrupt = True
                                    interrupt_action = action
                                    print("⚡ CODER: Breaking from action loop for update_file")
                                    break
                        elif action_type == 'rename_file':
                            old_path = action.get('path')
                            new_name = action.get('new_name')
                            print(f"\n🚨 CODER: INTERRUPT - Detected rename_file action: {old_path} -> {new_name}")

                            # Emit streaming event for rename_file action
                            _emit_stream("action_start", f"Renaming file: {old_path} → {new_name}", {
                                "action_type": "rename_file",
                                "file_path": old_path,
                                "new_name": new_name,
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for rename_file")
                            break
                        elif action_type == 'delete_file':
                            file_path = action.get('path')
                            print(f"\n🚨 CODER: INTERRUPT - Detected delete_file action for {file_path}")

                            # Emit streaming event for delete_file action
                            _emit_stream("action_start", f"Deleting file: {file_path}", {
                                "action_type": "delete_file",
                                "file_path": file_path,
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for delete_file")
                            break
                        elif action_type == 'start_backend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected start_backend action")

                            # Emit streaming event for start_backend action
                            _emit_stream("action_start", "Starting backend service", {
                                "action_type": "start_backend",
                                "service": "backend",
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for start_backend")
                            break
                        elif action_type == 'start_frontend':
                            print(f"\n🚨 CODER: INTERRUPT - Detected start_frontend action")

                            # Emit streaming event for start_frontend action
                            _emit_stream("action_start", "Starting frontend service", {
                                "action_type": "start_frontend",
                                "service": "frontend",
                                "action_details": action
                            })

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

                            # Emit streaming event for check_errors action
                            _emit_stream("action_start", "Checking for errors", {
                                "action_type": "check_errors",
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for check_errors")
                            break
                        elif action_type == 'todo_list':
                            print(f"\n🚨 CODER: INTERRUPT - Detected todo_list action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for todo_list")
                            break
                        elif action_type == 'ast_analyze':
                            print(f"\n🚨 CODER: INTERRUPT - Detected ast_analyze action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for ast_analyze")
                            break
                        elif action_type == 'check_logs':
                            print(f"\n🚨 CODER: INTERRUPT - Detected check_logs action")

                            # Emit streaming event for check_logs action
                            service = action.get('service', 'all')
                            _emit_stream("action_start", f"Checking logs for {service} service", {
                                "action_type": "check_logs",
                                "service": service,
                                "action_details": action
                            })

                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for check_logs")
                            break
                        elif action_type == 'web_search':
                            print(f"\n🚨 CODER: INTERRUPT - Detected web_search action")
                            should_interrupt = True
                            interrupt_action = action
                            print("⚡ CODER: Breaking from action loop for web_search")
                            break
                        elif action_type.startswith('todo_'):
                            print(f"\n📋 CODER: Processing todo action inline: {action_type}")

                            # Emit streaming event for todo action
                            todo_id = action.get('id', 'unknown')
                            if action_type == 'todo_create':
                                description = action.get('content', action.get('text', 'New todo'))
                                priority = action.get('priority', 'medium')
                                _emit_stream("action_start", f"Creating todo: {description}", {
                                    "action_type": "todo_create",
                                    "todo_id": todo_id,
                                    "description": description,
                                    "priority": priority,
                                    "action_details": action
                                })
                            elif action_type == 'todo_update':
                                status = action.get('status', 'updated')
                                _emit_stream("action_start", f"Updating todo {todo_id} → {status}", {
                                    "action_type": "todo_update",
                                    "todo_id": todo_id,
                                    "status": status,
                                    "action_details": action
                                })
                            elif action_type == 'todo_complete':
                                _emit_stream("action_start", f"Completing todo: {todo_id}", {
                                    "action_type": "todo_complete",
                                    "todo_id": todo_id,
                                    "action_details": action
                                })
                            else:
                                _emit_stream("action_start", f"Todo action: {action_type}", {
                                    "action_type": action_type,
                                    "todo_id": todo_id,
                                    "action_details": action
                                })

                            # Process todo actions inline without interrupting
                            if hasattr(self, '_handle_todo_actions'):
                                todo_result = self._handle_todo_actions(action)

                                # Emit result event for todo action
                                _emit_stream("action_result", f"Todo action {action_type} completed", {
                                    "action_type": action_type,
                                    "todo_id": todo_id,
                                    "status": "success",
                                    "result": str(todo_result) if todo_result else "completed"
                                })
                            else:
                                print(f"📋 CODER: Todo action {action_type} - system doesn't support todos")
                                _emit_stream("action_result", f"Todo system not available", {
                                    "action_type": action_type,
                                    "todo_id": todo_id,
                                    "status": "error",
                                    "result": "Todo system not available"
                                })
                            # Don't set should_interrupt for todo actions

                    if should_interrupt:
                        print("🛑 CODER: Interrupt flag set, breaking from chunk processing loop")
                        break

            print(f"\n🏁 CODER: Finished processing chunks. Total chunks: {chunk_count}")
            print(f"📊 CODER: Accumulated content length: {len(accumulated_content)} chars")

            # Handle any remaining buffered assistant content if no action tags detected
            if assistant_buffer and not has_action_tags and not buffered_content_streamed:
                print(f"💫 CODER: Flushing remaining buffered assistant content ({len(assistant_buffer)} chars) - no action tags found")
                final_filtered = buffer_xml_filter.process_chunk(assistant_buffer)
                if final_filtered:
                    _emit_stream("assistant_message", final_filtered)

            elif has_action_tags:
                # Check if this is an attempt_completion action - if so, extract and send as assistant message
                if 'type="attempt_completion"' in assistant_buffer:
                    print(f"🎯 CODER: Found attempt_completion in assistant buffer - extracting completion message")

                    # Extract the completion message using multiple patterns to handle malformed XML
                    import re
                    completion_message = ""

                    # Pattern 1: Standard closing tag </action>
                    completion_match = re.search(r'<action[^>]*type="attempt_completion"[^>]*>(.*?)</action>', assistant_buffer, re.DOTALL)
                    if completion_match:
                        completion_message = completion_match.group(1).strip()
                        print(f"📝 CODER: Pattern 1 - Extracted with </action> closing tag ({len(completion_message)} chars)")

                    # Pattern 2: Malformed closing tag </action_completion>
                    if not completion_message:
                        completion_match = re.search(r'<action[^>]*type="attempt_completion"[^>]*>(.*?)</action_completion>', assistant_buffer, re.DOTALL)
                        if completion_match:
                            completion_message = completion_match.group(1).strip()
                            print(f"📝 CODER: Pattern 2 - Extracted with </action_completion> closing tag ({len(completion_message)} chars)")

                    # Pattern 3: Extract everything after the opening tag until end of buffer or next tag
                    if not completion_message:
                        opening_match = re.search(r'<action[^>]*type="attempt_completion"[^>]*>(.*)', assistant_buffer, re.DOTALL)
                        if opening_match:
                            raw_content = opening_match.group(1)
                            # Stop at any closing action tag or end of content
                            end_match = re.search(r'^(.*?)(?:</action|</action_completion|$)', raw_content, re.DOTALL)
                            if end_match:
                                completion_message = end_match.group(1).strip()
                                print(f"📝 CODER: Pattern 3 - Extracted raw content after opening tag ({len(completion_message)} chars)")

                    # Pattern 4: Fallback - find content between attempt_completion markers
                    if not completion_message:
                        lines = assistant_buffer.split('\n')
                        capture_content = False
                        captured_lines = []

                        for line in lines:
                            if 'attempt_completion' in line.lower():
                                capture_content = True
                                # Check if this line has content beyond the tag
                                clean_line = re.sub(r'<[^>]*>', '', line).strip()
                                if clean_line:
                                    captured_lines.append(clean_line)
                            elif capture_content:
                                # Stop at closing tags or new action tags
                                if re.match(r'^\s*</', line) or '<action' in line:
                                    break
                                if line.strip():
                                    captured_lines.append(line.strip())

                        if captured_lines:
                            completion_message = '\n'.join(captured_lines).strip()
                            print(f"📝 CODER: Pattern 4 - Extracted from line-by-line parsing ({len(completion_message)} chars)")

                    # Clean up the message
                    if completion_message:
                        # Remove any remaining XML tags
                        completion_message = re.sub(r'<[^>]*>', '', completion_message)
                        # Normalize whitespace
                        completion_message = re.sub(r'\s+', ' ', completion_message).strip()

                        print(f"📝 CODER: Final cleaned completion message ({len(completion_message)} chars): {completion_message[:100]}...")
                        _emit_stream("assistant_message", completion_message)
                    else:
                        print(f"⚠️ CODER: Could not extract completion message from attempt_completion action")
                        print(f"🐛 DEBUG: assistant_buffer preview: {assistant_buffer[:500]}...")
                        _emit_stream("assistant_message", "Task completed successfully.")
                else:
                    print(f"🚫 CODER: Discarded {len(assistant_buffer)} chars of assistant content containing action tags")

            print(f"📝 CODER: Adding to full_response (current length: {len(full_response)})")

            full_response += accumulated_content
            print(f"📈 CODER: New full_response length: {len(full_response)} chars")

            # Query usage statistics using generation ID (OpenRouter only)
            if generation_id and not (hasattr(self, 'is_azure_mode') and self.is_azure_mode):
                query_generation_usage(self, generation_id)
            elif hasattr(self, 'is_azure_mode') and self.is_azure_mode:
                print("✅ CODER: Azure mode - usage already captured from streaming response")
            else:
                print("⚠️ CODER: No generation ID available for usage query")

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

                        # Emit streaming event for successful read_file result
                        _emit_stream("action_result", f"Read {len(file_content)} characters from: {file_path}", {
                            "action_type": "read_file",
                            "file_path": file_path,
                            "status": "success",
                            "result": f"Read {len(file_content)} characters",
                            "content": file_content  # ✅ Include actual file content
                        })
                        # Add the read file content to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        print(f"📤 CODER: Adding assistant message ({len(assistant_msg['content'])} chars) to messages")
                        messages.append(assistant_msg)

                        full_user_msg += f"""
<action_result type=\"read_file\" path=\"{interrupt_action.get('path')}\">
File content for {interrupt_action.get('path')}:
```
{file_content}
```
</action_result>
"""

                        # Also add to conversation history for persistence
                        print("💾 CODER: Adding messages to conversation history")
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # full_user_msg persists to next iteration
                        print(f"💾 CODER: Accumulated messages will carry to next iteration ({len(full_user_msg)} chars)")

                        print(f"🔄 CODER: Continuing iteration with {len(messages)} total messages")
                        continue
                    else:
                        # Pass the read error back to the model so it can continue with different approach
                        file_path = interrupt_action.get('path', 'unknown')
                        print(f"❌ Failed to read file {file_path}, passing error to model")

                        # Emit streaming event for failed read_file result
                        _emit_stream("action_result", f"Error reading file: {file_path}", {
                            "action_type": "read_file",
                            "file_path": file_path,
                            "status": "error",
                            "result": f"Cannot read file '{file_path}' - file doesn't exist"
                        })

                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        error_msg = {"role": "user", "content": f"❌ Error: Cannot update file '{file_path}' because it doesn't exist.\n\n✅ SOLUTION: Use <action type=\"file\" filePath=\"{file_path}\">YOUR_FILE_CONTENT</action> to create the file first.\n\nDo NOT use update_file for non-existent files. Use the file action to create it.\n\nPlease continue with your response."}

                        messages.append(assistant_msg)
                        messages.append(error_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self.conversation_history.append(error_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                elif interrupt_action.get('type') == 'create_file_realtime':
                    # Handle real-time file creation
                    create_result = self._handle_create_file_realtime(interrupt_action)
                    if create_result is not None:
                        # Check if file creation was blocked due to empty content
                        if create_result.get('empty_file_warning'):
                            print(f"⚠️ File creation blocked due to empty content")

                            # Emit streaming event for empty file warning
                            _emit_stream("action_result", f"Warning: Empty file creation blocked", {
                                "action_type": "create_file",
                                "file_path": create_result.get('file_path'),
                                "status": "warning",
                                "result": create_result.get('message', 'Empty file creation blocked')
                            })

                            # Add the empty file warning to user messages
                            assistant_msg = {"role": "assistant", "content": accumulated_content}
                            full_user_msg += f"""
<action_result type=\"create_file_realtime\" file_path=\"{create_result.get('file_path')}\">
{create_result.get('message')}
</action_result>
"""
                            messages.append(assistant_msg)
                            self.conversation_history.append(assistant_msg)
                            self._save_conversation_history()  # Save after each iteration

                            # Add todo and service context before continuing
                            full_user_msg = _add_context_to_message(self, full_user_msg)

                            # Accumulated messages will be added at the start of next iteration
                            print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                            continue

                        file_path = create_result.get('file_path')
                        print(f"✅ Created file: {file_path}")

                        # Emit streaming event for successful file creation
                        _emit_stream("action_result", f"Created file: {file_path}", {
                            "action_type": "create_file",
                            "file_path": file_path,
                            "status": "success",
                            "result": f"File '{file_path}' created successfully",
                            "content": create_result.get('file_content', '')  # ✅ Include actual file content
                        })

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

                        # Check if the created file uses os.environ but doesn't have load_dotenv
                        dotenv_warning = None
                        if file_path.endswith('.py'):
                            # Get the actual file content from the create_result
                            file_content = create_result.get('file_content', '')

                            # Check if file uses os.environ but doesn't import/call load_dotenv
                            uses_environ = 'os.environ' in file_content
                            has_load_dotenv = 'load_dotenv' in file_content

                            if uses_environ and not has_load_dotenv:
                                dotenv_warning = f"""
====
⚠️  **Environment Variable Warning:**
The file '{file_path}' uses `os.environ` but doesn't call `load_dotenv()`.

**To fix this, add these lines at the top of your file:**
"""
                        if error_messages:
                            error_text = '\n\n'.join(error_messages)
                            user_content = f"""
✅ File '{file_path}' created.

**Static Analysis Results:**
{error_text}

**NEXT STEPS:**
1. Fix these static errors first
2. If this is a backend service, create a test file (e.g., `backend/test_api.py`) to verify it works
3. Run the test file with `python backend/test_api.py`
4. Fix any runtime errors
5. Delete the test file when done

Continue with your implementation and testing."""
                        else:
                            user_content = f"""
✅ File '{file_path}' created successfully.

If this was a backend service:
1. Create a test file (e.g., `backend/test_api.py`)
2. Write Python code to test your endpoints
3. Run it with `python backend/test_api.py`
4. Verify it works, then delete the test file."""


                        full_user_msg += f"""
<action_result type=\"create_file_realtime\" file_path=\"{file_path}\">
{user_content}

{dotenv_warning if dotenv_warning else ""}
</action_result>
"""
                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

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
                        full_user_msg += f"""
<action_result type=\"run_command\" command=\"{interrupt_action.get('command')}\" cwd=\"{interrupt_action.get('cwd')}\">
{command_output}
</action_result>
"""

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        print(f"❌ Failed to run command {interrupt_action.get('command')}, stopping generation")
                        break
                elif interrupt_action.get('type') == 'update_file':
                    update_result = self._handle_update_file_interrupt(interrupt_action)
                    if update_result is not None:
                        file_path = interrupt_action.get('path')

                        # Read the updated file content to include in the stream
                        updated_content = None
                        if "successfully" in str(update_result).lower():
                            try:
                                updated_content = self._read_file_via_api(file_path)
                                print(f"📖 Read updated file content: {len(updated_content) if updated_content else 0} characters")
                            except Exception as e:
                                print(f"⚠️ Could not read updated file content: {e}")

                        # Emit streaming event for update_file result
                        emit_data = {
                            "action_type": "update_file",
                            "file_path": file_path,
                            "status": "success" if "successfully" in str(update_result).lower() else "error",
                            "result": str(update_result)
                        }

                        # Include updated content if available
                        if updated_content is not None:
                            emit_data["content"] = updated_content

                        _emit_stream("action_result", f"Updated file: {file_path}", emit_data)
                        # Check if this is an empty file warning
                        if isinstance(update_result, str) and "File update blocked" in update_result:
                            print(f"⚠️ File update blocked due to empty content")
                            # Add the empty file warning to user messages
                            assistant_msg = {"role": "assistant", "content": accumulated_content}
                            full_user_msg += f"""
<action_result type=\"update_file\" path=\"{interrupt_action.get('path')}\">
{update_result}
</action_result>
"""
                            messages.append(assistant_msg)
                            self.conversation_history.append(assistant_msg)
                            self._save_conversation_history()  # Save after each iteration

                            # Add todo and service context before continuing
                            full_user_msg = _add_context_to_message(self, full_user_msg)

                            # Accumulated messages will be added at the start of next iteration
                            print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                            continue

                        # Add the update result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"update_file\" path=\"{interrupt_action.get('path')}\">
File '{interrupt_action.get('path')}' has been updated successfully.
</action_result>
"""
                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

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
                        full_user_msg += f"""
<action_result type=\"rename_file\" path=\"{old_path}\" new_name=\"{new_name}\">
File '{old_path}' has been renamed to '{new_name}' successfully.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

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
                        full_user_msg += f"""
<action_result type=\"delete_file\" path=\"{file_path}\">
File '{file_path}' has been deleted successfully.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        print(f"❌ Failed to delete file {interrupt_action.get('path')}, stopping generation")
                        break
                elif interrupt_action.get('type') == 'start_backend':
                    service_result = self._handle_start_backend_interrupt(interrupt_action)
                    if service_result and service_result.get('status') == 'success':
                        # Success case
                        backend_result = service_result.get('result', {})
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"start_backend\">
Backend service started successfully on port {backend_result.get('backend_port')}. API available at {backend_result.get('backend_url')}.
</action_result>
"""
                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        # Error case - get actual error details
                        error_details = "Unknown error"
                        if service_result and service_result.get('error'):
                            error_details = service_result.get('error')

                        print(f"❌ Failed to start backend service, passing error to model for fixing")
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"start_backend_error\">
❌ Backend failed to start. Error details: {error_details}

Please fix the issues and try starting the backend again.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                elif interrupt_action.get('type') == 'start_frontend':
                    service_result = self._handle_start_frontend_interrupt(interrupt_action)
                    if service_result and service_result.get('status') == 'success':
                        # Success case
                        frontend_result = service_result.get('result', {})
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"start_frontend\">
Frontend service started successfully on port {frontend_result.get('frontend_port')}. Available at {frontend_result.get('frontend_url')}.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        # Error case - get actual error details
                        error_details = "Unknown error"
                        if service_result and service_result.get('error'):
                            error_details = service_result.get('error')

                        print(f"❌ Failed to start frontend service, passing error to model for fixing")
                        # Pass the error back to the model so it can fix the issues
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"start_frontend_error\">
❌ Frontend failed to start. Error details: {error_details}

Please fix the issues and try starting the frontend again.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                elif interrupt_action.get('type') == 'restart_backend':
                    service_result = self._handle_restart_backend_interrupt(interrupt_action)
                    if service_result and service_result.get('status') == 'success':
                        # Success case
                        backend_result = service_result.get('result', {})
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"restart_backend\">
Backend service restarted successfully on port {backend_result.get('backend_port')}. API available at {backend_result.get('backend_url')}.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        # Error case - get actual error details
                        error_details = "Unknown error"
                        if service_result and service_result.get('error'):
                            error_details = service_result.get('error')

                        print(f"❌ Failed to restart backend service, passing error to model for fixing")
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"restart_backend_error\">
❌ Backend restart failed. Error details: {error_details}

Please fix the issues and try restarting the backend again.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                elif interrupt_action.get('type') == 'restart_frontend':
                    service_result = self._handle_restart_frontend_interrupt(interrupt_action)
                    if service_result and service_result.get('status') == 'success':
                        # Success case
                        frontend_result = service_result.get('result', {})
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"restart_frontend\">
Frontend service restarted successfully on port {frontend_result.get('frontend_port')}. Available at {frontend_result.get('frontend_url')}.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        # Error case - get actual error details
                        error_details = "Unknown error"
                        if service_result and service_result.get('error'):
                            error_details = service_result.get('error')

                        print(f"❌ Failed to restart frontend service, passing error to model for fixing")
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type=\"restart_frontend_error\">
❌ Frontend restart failed. Error details: {error_details}

Please fix the issues and try restarting the frontend again.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

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

                        full_user_msg += f"""
<action_result type=\"check_errors\">
{error_summary}
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        print(f"❌ Failed to run error check, stopping generation")
                        break
                elif interrupt_action.get('type') == 'todo_list':
                    # Handle todo_list action - display todos and return the status
                    print(f"📋 CODER: Processing todo_list interrupt")

                    # Get current todo status
                    todo_status = self._display_todos()

                    if todo_status:
                        # Add the todo status to the response
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        full_user_msg += f"""
<action_result type="todo_list">
{todo_status}
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        # No todos exist
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        full_user_msg += f"""
<action_result type="todo_list">
No todos have been created yet. Use the following actions to manage todos:
- <action type="todo_create" id="unique_id" priority="high|medium|low">Task description</action>
- <action type="todo_update" id="todo_id" status="in_progress|completed"/>
- <action type="todo_list"/> (to view all todos)
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                elif interrupt_action.get('type') == 'todo_complete':
                    # Todo was already processed inline, just need to prompt continuation
                    print(f"✅ CODER: Todo completion processed, prompting continuation")

                    # Get current todo status to show what's next
                    todo_status = self._display_todos()

                    # Add messages to prompt continuation
                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    full_user_msg += f"""
<action_result type=\"todo_complete\">
Great! You've completed a todo. Please continue with the next highest priority task.
</action_result>
"""

                    messages.append(assistant_msg)

                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self._save_conversation_history()  # Save after each iteration

                    # Add todo and service context before continuing
                    full_user_msg = _add_context_to_message(self, full_user_msg)

                    # Accumulated messages will be added at the start of next iteration
                    print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                    continue
                elif interrupt_action.get('type') == 'ast_analyze':
                    # Handle AST analysis action
                    print(f"🧠 CODER: Processing ast_analyze interrupt")

                    ast_result = self._handle_ast_analyze_interrupt(interrupt_action)
                    if ast_result is not None:
                        # Add the AST analysis result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        # Format the analysis results
                        target = interrupt_action.get('target', 'backend')
                        focus = interrupt_action.get('focus', 'all')

                        analysis_summary = ast_result.get('summary', {})
                        insights = ast_result.get('insights', [])
                        recommendations = ast_result.get('recommendations', [])
                        errors = ast_result.get('errors', [])

                        result_text = f"""AST Analysis Results ({target} - {focus}):

📊 **Summary:**
- Files analyzed: {analysis_summary.get('files_analyzed', 0)}
- Routes found: {analysis_summary.get('total_routes', 0)}
- Functions: {analysis_summary.get('total_functions', 0)}
- Classes: {analysis_summary.get('total_classes', 0)}
- Errors: {analysis_summary.get('errors_found', 0)}

"""

                        if insights:
                            result_text += "💡 **Key Insights:**\n"
                            for insight in insights:
                                result_text += f"- {insight}\n"
                            result_text += "\n"

                        if errors:
                            result_text += "❌ **Critical Issues:**\n"
                            for error in errors[:5]:  # Limit to 5 most critical
                                result_text += f"- {error.get('type', 'error')}: {error.get('message', 'Unknown error')} in {error.get('file', 'unknown file')}\n"
                            result_text += "\n"

                        if recommendations:
                            result_text += "🔧 **Recommendations:**\n"
                            for rec in recommendations[:3]:  # Limit to top 3
                                result_text += f"- {rec.get('description', 'Fix recommended')} (Priority: {rec.get('priority', 'medium')})\n"

                        result_text += "\nUse this analysis to understand the project structure and identify areas that need attention."

                        full_user_msg += f"""
<action_result type="ast_analyze" target="{target}" focus="{focus}">
{result_text}
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        continue
                    else:
                        print(f"❌ Failed to run AST analysis, stopping generation")
                        break
                elif interrupt_action.get('type') == 'web_search':
                    # Handle web_search action
                    print(f"🔍 CODER: Processing web_search interrupt")

                    search_result = self._handle_web_search_interrupt(interrupt_action)
                    if search_result is not None:
                        # Add the search result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        # Format the search results
                        query = search_result.get('query', '')
                        results = search_result.get('results', '')
                        success = search_result.get('success', False)
                        error = search_result.get('error', '')

                        if success:
                            result_text = f"""Web search completed for: "{query}"

**Search Results:**
{results}
"""
                        else:
                            result_text = f"""Web search failed for: "{query}"

❌ **Error:** {error}

💡 **Next Steps:**
- Try rephrasing the query
- Check if the search service is available
- Consider alternative research methods"""

                        # Create user message with search results
                        search_msg = {
                            "role": "user",
                            "content": result_text
                        }

                        # Update conversation history and messages
                        self.conversation_history.extend([assistant_msg, search_msg])
                        messages.extend([assistant_msg, search_msg])

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        print(f"✅ CODER: Web search results added to conversation")

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")

                        # Continue generation with search results
                        continue
                    else:
                        print(f"❌ Failed to perform web search, stopping generation")
                        break
                elif interrupt_action.get('type') == 'check_logs':
                    # Handle check_logs action
                    print(f"📋 CODER: Processing check_logs interrupt")

                    logs_result = self._handle_check_logs_interrupt(interrupt_action)
                    if logs_result is not None:
                        # Add the logs result to messages and conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}

                        # Format the logs results (check both top level and raw_attrs)
                        service = interrupt_action.get('service') or interrupt_action.get('raw_attrs', {}).get('service', 'backend')
                        new_only = interrupt_action.get('new_only') or interrupt_action.get('raw_attrs', {}).get('new_only', True)

                        # Handle string boolean conversion for new_only
                        if isinstance(new_only, str):
                            new_only = new_only.lower() in ('true', '1', 'yes')
                        elif new_only is True:
                            new_only = True
                        else:
                            new_only = True  # Default fallback

                        logs_content = logs_result.get('logs', '')
                        total_lines = logs_result.get('total_lines', 0)
                        new_lines = logs_result.get('new_lines', 0)
                        service_running = logs_result.get('service_running', False)

                        # For frontend logs, don't truncate - show all errors with timestamps
                        if service == 'frontend':
                            print(f"📋 Returning FULL frontend logs ({len(logs_content)} chars) with all errors and timestamps")
                        else:
                            # Truncate backend logs if they're too long
                            if len(logs_content) > 4000:
                                lines = logs_content.split('\n')
                                if len(lines) > 50:
                                    # Keep first 10 and last 40 lines
                                    truncated_logs = '\n'.join(lines[:10] + ['...[truncated]...'] + lines[-40:])
                                else:
                                    # Just truncate by characters
                                    truncated_logs = logs_content[:2000] + '\n...[truncated]...\n' + logs_content[-2000:]
                                logs_content = truncated_logs

                        status_emoji = "🟢" if service_running else "🔴"

                        result_text = f"""Logs for {service} service ({status_emoji} {'Running' if service_running else 'Stopped'}):

📊 **Log Summary:**
- Total lines: {total_lines}
- New lines since last check: {new_lines}
- Service status: {'Running' if service_running else 'Stopped'}

📝 **Log Content:**
```
{logs_content.strip() if logs_content.strip() else 'No logs available'}
```

💡 **Analysis Tips:**
- Look for error messages, stack traces, and warning patterns
- Check startup/initialization logs for issues
- Monitor API request/response logs for debugging
- Use this information to identify and fix problems systematically
"""

                        full_user_msg += f"""
<action_result type="check_logs" service="{service}">
{result_text}
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        # Accumulated messages will be added at the start of next iteration
                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")
                        print(f"📋 CODER: Retrieved {new_lines} new lines from {service} service logs")

                        continue
                    else:
                        print(f"❌ Failed to check logs, stopping generation")
                        break
                elif interrupt_action.get('type') == 'attempt_completion':
                    # Handle attempt completion action - CHECK TODOS FIRST BEFORE ENDING
                    print(f"🎯 CODER: Processing attempt_completion interrupt - CHECKING TODOS FIRST")

                    # Check if there are incomplete todos
                    if hasattr(self, '_has_incomplete_todos') and self._has_incomplete_todos():
                        print(f"🚨 CODER: INCOMPLETE TODOS FOUND - BLOCKING COMPLETION")

                        # Get detailed todo message
                        incomplete_message = self._get_incomplete_todos_message() if hasattr(self, '_get_incomplete_todos_message') else "There are still incomplete todos that need to be finished."

                        # Add the incomplete todos warning to conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()

                        # Continue the conversation instead of ending
                        full_user_msg += f"""
<action_result type="attempt_completion_blocked">
{incomplete_message}
</action_result>
"""

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        messages.append(assistant_msg)
                        print(f"💾 CODER: Blocked completion - continuing iteration with {len(full_user_msg)} chars")
                        continue
                    else:
                        # No incomplete todos - proceed with completion
                        print(f"✅ CODER: No incomplete todos found - PROCEEDING WITH TERMINATION")

                        completion_result = self._handle_attempt_completion_interrupt(interrupt_action, accumulated_content)

                        # Add the completion message to conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()

                        # Session will end after this return - completion message already handled in streaming buffer

                        print(f"🏁 CODER: Session TERMINATED by attempt_completion action")
                        print(f"📝 CODER: Final response length: {len(full_response + accumulated_content)} chars")
                        print(f"🔚 CODER: Ending iteration loop at iteration {iteration}")

                        # IMMEDIATELY RETURN AND END THE ENTIRE CODER FUNCTION
                        return full_response + accumulated_content
            else:
                 # No interruption, process any remaining actions and finish
                print("🎬 CODER: No interrupt detected, processing remaining actions...")
                print(f"📝 CODER: Processing remaining actions with {len(accumulated_content)} chars of content")

                # CRITICAL: Check if attempt_completion was encountered in this iteration
                # Enhanced detection for multiple attempt_completion formats
                attempt_completion_detected = False
                detected_completion_message = ""

                # Method 1: Direct text search (existing)
                if 'attempt_completion' in accumulated_content.lower():
                    attempt_completion_detected = True
                    print("🎯 CODER: Method 1 - attempt_completion detected in content text")

                # Method 2: XML action tag detection
                if not attempt_completion_detected:
                    import re
                    action_pattern = r'<action[^>]*type="attempt_completion"[^>]*>'
                    if re.search(action_pattern, accumulated_content, re.IGNORECASE):
                        attempt_completion_detected = True
                        print("🎯 CODER: Method 2 - attempt_completion detected in XML action tag")

                        # Extract completion message from XML tag
                        full_action_pattern = r'<action[^>]*type="attempt_completion"[^>]*>(.*?)</action>'
                        action_match = re.search(full_action_pattern, accumulated_content, re.DOTALL | re.IGNORECASE)
                        if action_match:
                            detected_completion_message = action_match.group(1).strip()
                            print(f"📝 CODER: Extracted completion message from XML: {len(detected_completion_message)} chars")

                # Method 3: Check for completion-related patterns
                if not attempt_completion_detected:
                    completion_patterns = [
                        r'task\s+complete', r'completed\s+successfully', r'implementation\s+complete',
                        r'project\s+complete', r'work\s+complete', r'finished\s+implementing'
                    ]

                    for pattern in completion_patterns:
                        if re.search(pattern, accumulated_content, re.IGNORECASE):
                            # Additional context clues that suggest this is a completion
                            completion_indicators = ['summary', 'accomplished', 'delivered', 'built', 'created']
                            if any(indicator in accumulated_content.lower() for indicator in completion_indicators):
                                print(f"🎯 CODER: Method 3 - Potential completion detected with pattern: {pattern}")
                                # Note: Don't auto-trigger on this method, just log for debugging
                                break

                if attempt_completion_detected:
                    print("🎯 CODER: attempt_completion detected in content - CHECKING TODOS FIRST")

                    # Check if there are incomplete todos
                    if hasattr(self, '_has_incomplete_todos') and self._has_incomplete_todos():
                        print(f"🚨 CODER: INCOMPLETE TODOS FOUND - BLOCKING COMPLETION")

                        # Get detailed todo message
                        incomplete_message = self._get_incomplete_todos_message() if hasattr(self, '_get_incomplete_todos_message') else "There are still incomplete todos that need to be finished."

                        # Add the incomplete todos warning to conversation history
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()

                        # Continue the conversation instead of ending
                        full_user_msg += f"""
<action_result type="attempt_completion_blocked">
{incomplete_message}
</action_result>
"""

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        messages.append(assistant_msg)
                        print(f"💾 CODER: Blocked completion - continuing iteration with {len(full_user_msg)} chars")
                        continue
                    else:
                        # No incomplete todos - proceed with completion
                        print("✅ CODER: No incomplete todos found - ENDING SESSION IMMEDIATELY")
                        print("🏁 CODER: Session terminated by attempt_completion action")

                        # If we extracted a specific completion message, add it to the response
                        if detected_completion_message:
                            print(f"📝 CODER: Including extracted completion message in final response")
                            # Clean up the completion message
                            detected_completion_message = re.sub(r'<[^>]+>', '', detected_completion_message)
                            detected_completion_message = re.sub(r'\s+', ' ', detected_completion_message).strip()

                            # Ensure the completion message is visible in the response
                            final_response = full_response + accumulated_content
                            if detected_completion_message not in final_response:
                                final_response += f"\n\n{detected_completion_message}"
                            return final_response

                        return full_response + accumulated_content

                self._process_remaining_actions(accumulated_content)

                # Check if we have an incomplete action (opened but not closed)
                has_incomplete_action = False
                if '<action' in accumulated_content:
                    # Find the last action and check if it's properly closed
                    last_action_start = accumulated_content.rfind('<action')
                    if last_action_start != -1:
                        # Look for closing after the last action start
                        remaining_content = accumulated_content[last_action_start:]

                        # Check if this action is self-closing or properly closed
                        has_self_closing = '/>' in remaining_content
                        has_proper_closing = '</action>' in remaining_content

                        # Only incomplete if the action is neither self-closed nor properly closed
                        if not has_self_closing and not has_proper_closing:
                            has_incomplete_action = True
                            print(f"⚠️ CODER: Detected incomplete action tag - stream was likely cut off")
                            print(f"🐛 DEBUG: remaining_content = '{remaining_content}'")
                            print(f"🐛 DEBUG: has_self_closing = {has_self_closing}, has_proper_closing = {has_proper_closing}")
                        else:
                            print(f"✅ CODER: Action is properly closed (self_closing={has_self_closing}, proper_closing={has_proper_closing})")

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
                    full_user_msg += f"""
<action_result type=\"file_action_cutoff\">
The previous response was cut off. Please continue from where you left off to complete the file action.
</action_result>
"""

                    messages.append(assistant_msg)

                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self._save_conversation_history()  # Save after each iteration

                    # Store accumulated messages for next iteration
                    unified_user_message = full_user_msg
                    print(f"💾 CODER: Stored unified message before continue ({len(unified_user_message)} chars)")

                    print("🔄 CODER: Continuing iteration to complete the action")
                    continue
                elif todos_created_without_work:
                    # Prompt to start working on the todos that were just created
                    print("🔄 CODER: Todos created without implementation - prompting to start work")

                    # Get current todo status
                    todo_status = self._display_todos()

                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    full_user_msg += f"""
<action_result>
Good! You've created the todos. Here's the current status:\n\n{todo_status}\n\nNow please start implementing the highest priority todo. Remember to:\n1. Update the todo status to 'in_progress' using todo_update\n2. Create/modify the necessary files\n3. Test your implementation\n4. Mark the todo as completed when done
</action_result>
"""

                    messages.append(assistant_msg)

                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self._save_conversation_history()  # Save after each iteration

                    # Store accumulated messages for next iteration
                    unified_user_message = full_user_msg
                    print(f"💾 CODER: Stored unified message before continue ({len(unified_user_message)} chars)")

                    print("🔄 CODER: Continuing iteration to implement todos")
                    continue
                elif non_implementation_response:
                    # Response only contains planning/artifacts without actual implementation
                    print("🔄 CODER: Planning/artifact only response - prompting for implementation")

                    assistant_msg = {"role": "assistant", "content": accumulated_content}
                    full_user_msg += f"""
<action_result>
Good planning! Now please proceed with the actual implementation. Start creating or modifying the necessary files to implement what you've planned.
</action_result>
"""

                    messages.append(assistant_msg)

                    # Also add to conversation history for persistence
                    self.conversation_history.append(assistant_msg)
                    self._save_conversation_history()  # Save after each iteration

                    # Store accumulated messages for next iteration
                    unified_user_message = full_user_msg
                    print(f"💾 CODER: Stored unified message before continue ({len(unified_user_message)} chars)")

                    print("🔄 CODER: Continuing iteration to implement the plan")
                    continue
                else:
                    print("✅ CODER: Finished processing remaining actions")

                    # Check if there are more todos to work on
                    pending_todos = [todo for todo in getattr(self, 'todos', []) if todo.get('status') == 'pending']
                    in_progress_todos = [todo for todo in getattr(self, 'todos', []) if todo.get('status') == 'in_progress']

                    print(f"📋 CODER: Current todo status - Pending: {len(pending_todos)}, In Progress: {len(in_progress_todos)}")

                    if pending_todos or in_progress_todos:
                        print("🔄 CODER: There are still todos to work on, continuing iteration...")

                        # Get current todo status to show what's next
                        todo_status = self._display_todos() if hasattr(self, '_display_todos') else "Todo status not available"

                        # Add a message to prompt continuation with next todo
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type="continue_todos">
Great! You've made progress. Here's the current todo status:

{todo_status}

Please continue working on the next highest priority todo. Remember to:
1. Update the todo status to 'in_progress' using <action type="todo_update" id="todo_id" status="in_progress"/>
2. Implement the required functionality
3. Test your implementation
4. Mark the todo as completed when done using <action type="todo_update" id="todo_id" status="completed"/>
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")
                        continue
                    else:
                        print("✅ CODER: All todos completed or no todos exist, continuing iteration with completion prompt")

                        # Add a message prompting the model to use attempt_completion if conversation is done
                        assistant_msg = {"role": "assistant", "content": accumulated_content}
                        full_user_msg += f"""
<action_result type="no_actions_taken">
No actions were performed in this iteration. All current todos appear to be completed.

If you believe the task is fully complete and the user's request has been satisfied, please use the attempt_completion tool to summarize what was accomplished and end the conversation.

If there's more work to be done, please continue with additional implementation or create new todos for the remaining work.
</action_result>
"""

                        messages.append(assistant_msg)

                        # Also add to conversation history for persistence
                        self.conversation_history.append(assistant_msg)
                        self._save_conversation_history()  # Save after each iteration

                        # Add todo and service context before continuing
                        full_user_msg = _add_context_to_message(self, full_user_msg)

                        print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of context for next iteration")
                        continue


            # 💡 additional context - Add todo and service status
            full_user_msg = _add_context_to_message(self, full_user_msg)

            # Accumulated messages (action results + todo status + service status) will be added at start of next iteration
            print(f"💾 CODER: Accumulated {len(full_user_msg)} chars of full context for next iteration")

        except Exception as e:
            print(f"❌ CODER: Exception during generation in iteration {iteration}: {e}")
            print(f"🔍 CODER: Exception type: {type(e).__name__}")

            # If this is a FrontendCommandInterrupt, re-raise it to bubble up to streaming API
            if e.__class__.__name__ == 'FrontendCommandInterrupt':
                print("🚨 CODER: FrontendCommandInterrupt detected - re-raising to streaming API...")
                raise e

            import traceback
            print("📚 CODER: Full traceback:")
            traceback.print_exc()
            break

    print(f"\n🏁 CODER: Completed iteration loop after {iteration} iterations")
    print(f"📊 CODER: Final full_response length: {len(full_response)} chars")

    # Add any remaining accumulated messages to conversation history
    if full_user_msg.strip():
        print(f"📤 CODER: Adding final accumulated context to conversation ({len(full_user_msg)} chars)")
        # Add todo and service context to the final message
        full_user_msg = _add_context_to_message(self, full_user_msg)
        print(f"📊 CODER: Final message with context: {len(full_user_msg)} chars")
        messages.append({"role": "user", "content": full_user_msg})
        self.conversation_history.append({"role": "user", "content": full_user_msg})
        self._save_conversation_history()  # Save after each iteration

    print(f"🎉 CODER: Returning full_response with {len(full_response)} chars")
    return full_response


def _is_service_actually_working(self, service):
    """Check if the service is actually working by testing connectivity"""
    try:
        if service == 'backend':
            # Check if backend is responding
            backend_url = getattr(self, 'backend_url', None)
            if not backend_url:
                # Try to detect backend URL from processes
                project_id = getattr(self, 'project_id', None)
                if project_id and hasattr(self, 'processes') and project_id in self.processes:
                    backend_port = self.processes[project_id].get('backend_port')
                    if backend_port:
                        backend_url = f"http://localhost:{backend_port}"

            if backend_url:
                import requests
                # Try multiple health endpoints
                endpoints_to_try = [
                    f"{backend_url}/health",
                    f"{backend_url}/",
                    f"{backend_url}/api"
                ]

                for endpoint in endpoints_to_try:
                    try:
                        response = requests.get(endpoint, timeout=3)
                        if response.status_code in [200, 404, 405]:  # Server responding
                            print(f"✅ CODER: {service} is responding at {endpoint}")
                            return True
                    except:
                        continue

            print(f"❌ CODER: {service} is not responding to health checks")
            return False

        elif service == 'frontend':
            # Check if frontend is responding
            frontend_url = getattr(self, 'preview_url', None)
            if not frontend_url:
                # Try to detect frontend URL from processes
                project_id = getattr(self, 'project_id', None)
                if project_id and hasattr(self, 'processes') and project_id in self.processes:
                    frontend_port = self.processes[project_id].get('frontend_port')
                    if frontend_port:
                        frontend_url = f"http://localhost:{frontend_port}"

            if frontend_url:
                import requests
                try:
                    response = requests.get(frontend_url, timeout=3)
                    if response.status_code in [200, 404]:  # Frontend responding
                        print(f"✅ CODER: {service} is responding at {frontend_url}")
                        return True
                except:
                    pass

            print(f"❌ CODER: {service} is not responding to health checks")
            return False

    except Exception as e:
        print(f"⚠️ CODER: Error checking {service} health: {e}")

    return False

def _add_context_to_message(self, full_user_msg):
    """Add todo status and service status to the message accumulator"""
    # Add current todo status as context
    print("🔍 CODER: Adding todo and service context...")
    todo_status = self._display_todos()
    if todo_status:
        print(f"⚠️ CODER: Found todo status ({len(todo_status)} chars), adding to context")

        # Check if no todos exist yet
        if 'no todos created yet' in todo_status:
            full_user_msg += f"""
<todo_status>
Current todo status:\n\n{todo_status}\n\n

====
Note: No todos have been created yet. Please plan and create todos to then follow and systematically work on tasks.
- First, analyze the user's request and break it down into specific, actionable todos
- Create todos with appropriate priorities (high, medium, low)
- Then systematically work on each todo until all are completed, integrated and tested to make sure it works end to end
- As you work on each todo, update the todo status to in_progress
- Once you have completed a todo, update the todo status to completed
</todo_status>
"""
        else:
            full_user_msg += f"""
<todo_status>
Current todo status:\n\n{todo_status}\n\n

====
Note: Continue with the highest priority todo.
- Systematically work on each todo until all are completed, integrated and tested to make sure it works end to end.
- As you work on each todo, update the todo status to in_progress.
- Once you have completed a todo, update the todo status to completed.
- If you are not sure what to do next, check the todo status and pick the highest priority todo.
</todo_status>
"""
    else:
        print("✅ CODER: No todo status found")

    # Add comprehensive service status context (backend errors, deployment info, etc.)
    print("🔍 CODER: Adding service status context...")
    service_status_context = self._build_service_status_context()
    if service_status_context:
        full_user_msg += f"\n{service_status_context}\n"
        print(f"✅ CODER: Added service status context ({len(service_status_context)} chars)")

    # Also add basic backend deployment info for compatibility
    try:
        backend_deployment_info = self._get_backend_deployment_info()
        if backend_deployment_info.get('status') == 'success':
            backend_url = backend_deployment_info.get('url')
            app_name = backend_deployment_info.get('app_name', 'Unknown')
            backend_status = f"Deployed on Modal.com ({app_name})"
        else:
            backend_url = None
            backend_status = "Not deployed"
    except Exception as e:
        backend_url = None
        backend_status = f"Error checking deployment: {str(e)}"

    frontend_url = self.preview_url

    # Ping backend and frontend to check status using multiple methods
    frontend_status = "Not running"

    # Backend status is already determined by Modal.com deployment info above
    # (Commented out old localhost backend status checking logic)

    # Simplify frontend status
    if frontend_url:
        frontend_status = "Running"

    # Check for errors in logs (only new lines since last checkpoint)
    def _check_service_has_errors(service):
        """Quick check if service has any errors in recent logs (new lines only)"""
        try:
            project_id = getattr(self, 'project_id', None)
            if not project_id:
                return False

            # Import requests for API call
            import requests

            # Call the check_logs API with new_only=True to check only since last checkpoint
            api_base_url = getattr(self, 'api_base_url', 'http://localhost:8000')
            if api_base_url.endswith('/api'):
                api_base_url = api_base_url[:-4]

            logs_url = f"{api_base_url}/api/projects/{project_id}/check-logs"
            params = {
                'service': service,
                'include_new_only': True  # Only check new logs since last checkpoint
            }

            response = requests.get(logs_url, params=params, timeout=5)
            if response.status_code == 200:
                logs_data = response.json()
                logs_content = logs_data.get('logs', '').lower()
                new_lines = logs_data.get('new_lines', 0)

                # Simple error detection: if "error" appears in logs, it's an error
                error_keywords = ['error', 'exception', 'failed', 'crash', 'fatal', 'critical']

                # Smart error detection: Check new logs first, then verify if service is actually broken

                # Step 1: Check for NEW errors since last checkpoint
                if new_lines > 0 and logs_content.strip():
                    # Skip checkpoint-only logs (just contains "CHECKPOINT:")
                    checkpoint_only = ('<!-- checkpoint:' in logs_content and
                                     logs_content.count('\n') <= 3 and
                                     not any(keyword in logs_content for keyword in error_keywords))
                    if checkpoint_only:
                        print(f"🔍 CODER: {service} new logs contain only checkpoints, checking recent full logs...")
                        # If only checkpoints, check recent full logs for active errors
                        full_params = {'service': service, 'include_new_only': False}
                        full_response = requests.get(logs_url, params=full_params, timeout=5)

                        if full_response.status_code == 200:
                            full_logs_data = full_response.json()
                            full_logs_content = full_logs_data.get('logs', '').lower()

                            # Check last 100 lines for recent errors (skip checkpoint-only lines)
                            all_lines = full_logs_content.split('\n') if full_logs_content else []
                            recent_lines = [line for line in all_lines[-100:] if line.strip() and not line.strip().startswith('<!--')]
                            recent_logs = '\n'.join(recent_lines)

                            has_recent_errors = any(keyword in recent_logs for keyword in error_keywords)
                            if has_recent_errors:
                                print(f"🚨 CODER: Found recent {service} errors in last 10 lines of logs")
                                return True
                            else:
                                print(f"🔍 CODER: No recent errors found in {service} logs")
                                return False
                    else:
                        # Check for actual errors in new content
                        has_new_errors = any(keyword in logs_content for keyword in error_keywords)
                        if has_new_errors:
                            print(f"🚨 CODER: Detected FRESH {service} errors since last checkpoint ({new_lines} new lines)")
                            return True
                        else:
                            print(f"🔍 CODER: {service} has {new_lines} new log lines but no error patterns")

                # Step 2: No new errors found, but check if service is actually working
                # This prevents false positives when errors were fixed but not yet logged
                print(f"🔍 CODER: No new {service} errors, verifying if service is actually working...")

                if _is_service_actually_working(self, service):
                    print(f"✅ CODER: {service} service is working - no errors to report")
                    return False
                else:
                    # Service is broken, check recent logs for the cause
                    print(f"⚠️ CODER: {service} service appears broken, checking recent logs for active errors...")

                    # Get recent logs to check for persistent errors causing the service failure
                    full_params = {'service': service, 'include_new_only': False}
                    full_response = requests.get(logs_url, params=full_params, timeout=5)

                    if full_response.status_code == 200:
                        full_logs_data = full_response.json()
                        full_logs_content = full_logs_data.get('logs', '').lower()

                        # Check only the most recent logs (last 20 lines) for active errors
                        recent_lines = full_logs_content.split('\n')[-20:] if full_logs_content else []
                        recent_logs = '\n'.join(recent_lines)

                        # Look for error keywords that could be causing current service failure
                        has_active_errors = any(keyword in recent_logs for keyword in error_keywords)

                        if has_active_errors:
                            print(f"🚨 CODER: Found active {service} errors causing service failure")
                            return True
                        else:
                            print(f"🔍 CODER: {service} service broken but no clear error patterns in recent logs")
                            return False

                return False
        except Exception as e:
            print(f"⚠️ CODER: Error checking {service} logs: {e}")

        return False

    # Commented out error checking for Modal.com deployment approach
    # # Check for errors in both services (regardless of whether they're running)
    # # This is important because crashed services won't have URLs but may have errors in logs
    # backend_has_errors = _check_service_has_errors('backend')
    # frontend_has_errors = _check_service_has_errors('frontend')
    #
    # # Create error indicators with critical urgency
    # backend_error_indicator = " 🚨 CRITICAL ERRORS - SERVICE BROKEN! Use <action type=\"check_logs\" service=\"backend\"/> to see errors and FIX IMMEDIATELY" if backend_has_errors else ""
    # frontend_error_indicator = " 🚨 CRITICAL ERRORS - SERVICE BROKEN! Use <action type=\"check_logs\" service=\"frontend\"/> to see errors and FIX IMMEDIATELY" if frontend_has_errors else ""

    # No error indicators for Modal.com deployment approach
    backend_error_indicator = ""
    frontend_error_indicator = ""

    # Add service status to full_user_msg
    backend_running = f"🟢 Deployed ・ Available at {backend_url} (accessible to frontend via VITE_APP_BACKEND_URL env variable)" if backend_url else "🚫 Not deployed"
    frontend_running = f"Running"
    backend_instructions = "" if backend_url else "Backend is not deployed. Use <action type=\"start_backend\"/> to deploy to Modal.com or <action type=\"restart_backend\"/> to redeploy it."
    frontend_instructions = "Frontend is always running. The user can your changes in realtime. So don't half do anything. Implement everything fully and proeprly. Fulfilled UI."

    full_user_msg += f"""
<service_status>
Backend: {backend_running} ・ {backend_status}{backend_error_indicator}
Frontend: {frontend_running} ・ {frontend_status}{frontend_error_indicator}

{backend_instructions}
    - Remember to load_dotenv() in your backend code to use the environment variables.
{frontend_instructions}
</service_status>
"""
    print(f"🔍 CODER: Backend status: {backend_status}")
    print(f"🔍 CODER: Frontend status: {frontend_status}")
    print(f"🔍 CODER: Backend URL: {backend_url}")
    print(f"🔍 CODER: Frontend URL: {frontend_url}")
    # print(f"🔍 CODER: Backend has errors: {backend_has_errors}")  # Commented out for Modal.com approach
    # print(f"🔍 CODER: Frontend has errors: {frontend_has_errors}")  # Commented out for Modal.com approach

    return full_user_msg


def query_generation_usage(self, generation_id):
    """
    Query usage statistics for a generation using OpenRouter API.
    Implements retry logic with exponential backoff since OpenRouter has a delay
    before generations are recorded in their system.
    """
    if not generation_id:
        print(f"⚠️ CODER: No generation ID provided for usage query")
        return None

    # Configurable pricing (can be updated based on actual OpenRouter rates)
    INPUT_PRICE_PER_MILLION = 0.20   # $0.20 per 1M input tokens
    OUTPUT_PRICE_PER_MILLION = 0.80  # $0.80 per 1M output tokens

    try:
        import requests
        import time

        print(f"💰 CODER: Querying usage for generation ID: {generation_id}")
        print(f"📊 CODER: Using pricing - Input: ${INPUT_PRICE_PER_MILLION}/M, Output: ${OUTPUT_PRICE_PER_MILLION}/M")

        # Retry logic with exponential backoff
        max_retries = 1
        base_delay = 2  # Start with 2 seconds
        max_delay = 5  # Cap at 60 seconds

        for attempt in range(max_retries):
            if attempt > 0:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                print(f"🔄 CODER: Retry attempt {attempt + 1}/{max_retries}, waiting {delay}s...")
                time.sleep(delay)

            headers = {
                "Authorization": f"Bearer {self.client.api_key}"
            }

            try:
                response = requests.get(
                    f"https://openrouter.ai/api/v1/generation?id={generation_id}",
                    headers=headers,
                    timeout=15  # Increased timeout for retries
                )

                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        gen_data = data['data']
                        prompt_tokens = gen_data.get('tokens_prompt', 0) or 0
                        completion_tokens = gen_data.get('tokens_completion', 0) or 0
                        total_tokens = prompt_tokens + completion_tokens

                        # Calculate cost estimates using configurable pricing
                        input_cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_PER_MILLION
                        output_cost = (completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_MILLION
                        iteration_cost = input_cost + output_cost

                        print(f"\n📈 Usage Statistics (Generation {generation_id}):")
                        print(f"Total Tokens: {total_tokens}")
                        print(f"Prompt Tokens: {prompt_tokens}")
                        print(f"Completion Tokens: {completion_tokens}")
                        print(f"💰 This Iteration Cost (Our Estimate): ${iteration_cost:.6f}")
                        print(f"   - Input cost: ${input_cost:.6f} ({prompt_tokens:,} × ${INPUT_PRICE_PER_MILLION}/M)")
                        print(f"   - Output cost: ${output_cost:.6f} ({completion_tokens:,} × ${OUTPUT_PRICE_PER_MILLION}/M)")
                        if gen_data.get('total_cost'):
                            print(f"💳 OpenRouter Actual Cost: ${gen_data.get('total_cost'):.6f}")
                            print(f"📊 Cost Comparison: Our ${iteration_cost:.6f} vs OpenRouter ${gen_data.get('total_cost'):.6f}")

                        # Update internal tracking
                        print("💾 CODER: Updating internal token tracking...")
                        old_total = self.token_usage.get('total_tokens', 0)
                        old_prompt = self.token_usage.get('prompt_tokens', 0)
                        old_completion = self.token_usage.get('completion_tokens', 0)

                        self.token_usage['prompt_tokens'] += prompt_tokens
                        self.token_usage['completion_tokens'] += completion_tokens
                        self.token_usage['total_tokens'] += total_tokens

                        # Calculate running cost totals using configurable pricing
                        total_input_cost = (self.token_usage['prompt_tokens'] / 1_000_000) * INPUT_PRICE_PER_MILLION
                        total_output_cost = (self.token_usage['completion_tokens'] / 1_000_000) * OUTPUT_PRICE_PER_MILLION
                        total_cost = total_input_cost + total_output_cost

                        print(f"💰 Running Totals:")
                        print(f"   Tokens: {old_total:,} → {self.token_usage['total_tokens']:,}")
                        print(f"   Input: {old_prompt:,} → {self.token_usage['prompt_tokens']:,}")
                        print(f"   Output: {old_completion:,} → {self.token_usage['completion_tokens']:,}")
                        print(f"   💲 Total Cost: ${total_cost:.6f}")
                        print(f"      - Input: ${total_input_cost:.6f}")
                        print(f"      - Output: ${total_output_cost:.6f}")

                        return {
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens,
                            'total_tokens': total_tokens,
                            'iteration_cost': iteration_cost,
                            'total_cost_estimate': total_cost,
                            'openrouter_cost': gen_data.get('total_cost')
                        }
                    else:
                        print(f"⚠️ CODER: Unexpected response format: {data}")
                        if attempt == max_retries - 1:
                            break
                        continue

                elif response.status_code == 404:
                    if attempt == max_retries - 1:
                        print(f"❌ CODER: Generation not found after {max_retries} attempts")
                        print(f"💡 This usually means the generation ID is invalid or expired")
                        print(f"🔍 Generation ID: {generation_id}")
                        break
                    else:
                        print(f"⏳ CODER: Generation not found yet (attempt {attempt + 1}), will retry...")
                        continue

                else:
                    print(f"⚠️ CODER: Usage query failed ({response.status_code}): {response.text[:200]}")
                    if attempt == max_retries - 1:
                        break
                    continue

            except requests.Timeout:
                print(f"⏰ CODER: Request timed out (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    print(f"❌ CODER: All attempts timed out")
                    break
                continue

            except requests.RequestException as e:
                print(f"🌐 CODER: Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    break
                continue

        # If we get here, all retries failed
        print(f"❌ CODER: Failed to query usage after {max_retries} attempts")
        print(f"💡 The generation may not be recorded yet, or there's an API issue")

        # Fallback: try to estimate tokens from the response content
        print(f"🔄 CODER: Attempting fallback token estimation...")
        try:
            # This is a rough estimate - 1 token ≈ 4 characters
            estimated_tokens = len(self.last_response_content or "") // 4
            if estimated_tokens > 0:
                print(f"📊 CODER: Fallback estimate: ~{estimated_tokens} tokens")
                # Don't update token tracking with estimates, just log it
                return {
                    'prompt_tokens': 0,
                    'completion_tokens': estimated_tokens,
                    'total_tokens': estimated_tokens,
                    'iteration_cost': 0,
                    'total_cost_estimate': 0,
                    'openrouter_cost': None,
                    'note': 'Fallback estimation used'
                }
        except Exception as e:
            print(f"⚠️ CODER: Fallback estimation also failed: {e}")

    except Exception as e:
        print(f"❌ CODER: Unexpected error in usage query: {e}")
        import traceback
        traceback.print_exc()

    return None


def _detect_invalid_xml_tags(content):
    """
    Detect invalid action-like XML tags in model responses.
    Only flags tags that appear to be intended as action tags but are malformed.
    Returns a list of invalid tags found.
    """
    import re

    # Find tags that look like they're trying to be action tags but might be malformed
    # Look for patterns like <something type="..."> or similar action-like structures
    potential_action_pattern = r'<[a-zA-Z_][a-zA-Z0-9_\-]*\s+type="[^"]*"[^>]*/?>'
    potential_actions = re.findall(potential_action_pattern, content)

    # Also look for self-closing tags that might be actions
    potential_self_closing = r'<[a-zA-Z_][a-zA-Z0-9_\-]*\s+[^>]*path="[^"]*"[^>]*/?>'
    potential_actions.extend(re.findall(potential_self_closing, content))

    # Valid action tag patterns that we expect
    valid_action_patterns = [
        r'<action\s+type="(read_file|file|update_file|rename_file|delete_file|run_command|start_backend|start_frontend|restart_backend|restart_frontend|check_errors|check_logs|todo_create|todo_update|todo_complete|todo_list)"[^>]*>',
        r'<action\s+type="(read_file|file|update_file|rename_file|delete_file|run_command|start_backend|start_frontend|restart_backend|restart_frontend|check_errors|check_logs|todo_create|todo_update|todo_complete|todo_list)"[^>]*/?>',
        r'<artifact\s+[^>]*>',
        r'<thinking>'
    ]

    invalid_tags = []

    for tag in potential_actions:
        is_valid = False

        # Check if this tag matches any valid action pattern
        for valid_pattern in valid_action_patterns:
            if re.match(valid_pattern, tag):
                is_valid = True
                break

        if not is_valid:
            invalid_tags.append(tag)

    # Remove duplicates and return
    return list(set(invalid_tags))


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




def _check_and_summarize_conversation_method(self, is_mid_task=False):
    """Check if conversation needs summarization and create detailed summary"""

    token_usage = getattr(self, 'token_usage', {'total_tokens': 0})
    print(f"\n🔄 Conversation has grown large ({token_usage['total_tokens']:,} total tokens)")
    print(f"📋 Creating summary to reset token count...")

    # Generate comprehensive summary
    summary_content = self._generate_detailed_conversation_summary(is_mid_task=is_mid_task)

    if summary_content:
        # Add summary to conversation with XML tag
        summary_message = {
            "role": "assistant",
            "content": f"<summary timestamp='{datetime.now().isoformat()}'>\n{summary_content}\n</summary>",
            "metadata": {
                "type": "conversation_summary",
                "tokens_at_summary": token_usage['total_tokens'],
                "created_at": datetime.now().isoformat()
            }
        }

        self.conversation_history.append(summary_message)
        print(f"✅ Added detailed summary to conversation ({len(summary_content)} characters)")

        # Reset token counter to start fresh count from this point
        self._reset_token_tracking_after_summary()
    else:
        print(f"❌ Failed to generate conversation summary")

def _generate_detailed_conversation_summary_method(self, is_mid_task=False) -> str:
    """Generate comprehensive summary of messages since last summary"""

    # Find the latest VALID summary message index
    latest_summary_index = -1
    for i in range(len(self.conversation_history) - 1, -1, -1):  # Search backwards
        message = self.conversation_history[i]
        if (message.get('role') == 'assistant' and
            '<summary' in message.get('content', '')):
            # VALIDATE that this is actually a real summary
            content = message.get('content', '')
            if self._is_valid_summary(content):
                latest_summary_index = i
                break

    # Get messages to summarize (only NEW messages since last summary)
    if latest_summary_index == -1:
        # No previous summary, summarize everything except system prompt
        messages_to_summarize = self.conversation_history[1:]  # Skip system prompt
        print(f"📋 Summarizing entire conversation: {len(messages_to_summarize)} messages")
    else:
        # Summarize only messages since last summary
        messages_to_summarize = self.conversation_history[latest_summary_index + 1:]
        print(f"📋 Summarizing {len(messages_to_summarize)} messages since last summary")

    # Prepare conversation for summarization
    conversation_text = ""
    for i, message in enumerate(messages_to_summarize):
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        conversation_text += f"\n[{role.upper()}]: {content}\n"

    # Create comprehensive summary prompt
    token_usage = getattr(self, 'token_usage', {'total_tokens': 0})
    project_files = getattr(self, 'project_files', {})

    summary_prompt = f"""Create a comprehensive, detailed summary of this entire project conversation. This summary will be used as context for future updates to this codebase.

CONVERSATION TO SUMMARIZE:
{conversation_text}

PROJECT CONTEXT:
- Project ID: {getattr(self, 'project_id', 'unknown')}
- Total tokens used: {token_usage['total_tokens']:,}
- Files in project: {len(project_files)}

1. Current Work:
   [Detailed description]

2. Key Technical Concepts:
   - [Concept 1]
   - [Concept 2]
   - [...]

3. Relevant Files and Code:
   - [File Name 1]
      - [Summary of why this file is important]
      - [Summary of the changes made to this file, if any]
      - [Important Code Snippet]
   - [File Name 2]
      - [Important Code Snippet]
   - [...]

4. Problem Solving:
   [Detailed description]

5. Pending Tasks and Next Steps:
   - [Task 1 details & next steps]
   - [Task 2 details & next steps]
   - [...]

""" + ("""
8. **CURRENT TASK STATUS & CONTINUATION** ⚠️ MID-TASK SUMMARY
   - What task is currently in progress (analyze the most recent messages)
   - What was just completed in the latest actions
   - What needs to be done next to complete the current task
   - Any pending actions or iterations that were interrupted by token limit
   - Specific next steps for seamless task continuation""" if is_mid_task else "") + """

Make this summary extremely detailed and comprehensive. Include specific file names, function names, command outputs, error messages, and any other details that would help a developer understand the complete context of this project. This summary will replace all previous conversation history, so it must capture everything important.

IMPORTANT: Write this as if explaining the project to a new developer who needs to understand everything that has happened so far."""

    try:
        # Generate summary using API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert technical writer who creates comprehensive project documentation. Create detailed summaries that capture all important context for software development projects."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=10000,  # Allow for very detailed summary
        )

        summary_content = response.choices[0].message.content

        # Track token usage for summary generation
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            if not hasattr(self, 'token_usage'):
                self.token_usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

            self.token_usage['prompt_tokens'] += usage.prompt_tokens
            self.token_usage['completion_tokens'] += usage.completion_tokens
            self.token_usage['total_tokens'] += usage.total_tokens

            print(f"📊 Summary generation used: {usage.total_tokens} tokens")

        return summary_content

    except Exception as e:
        print(f"❌ Error generating conversation summary: {e}")
        return None

def _is_valid_summary_method(self, content: str) -> bool:
    """Validate that a summary is actually a proper summary, not broken garbage"""
    if not content or len(content) < 500:  # Real summaries should be substantial
        return False

    return True

def _reset_token_tracking_after_summary_method(self):
    """Reset token tracking to start fresh count after summary"""
    if not hasattr(self, 'token_usage'):
        self.token_usage = {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0}

    print(f"🔄 Resetting token count from {self.token_usage['total_tokens']:,} to 0")
    self.token_usage = {
        'total_tokens': 0,
        'prompt_tokens': 0,
        'completion_tokens': 0
    }

# Local storage removed - using cloud storage only

print("✅ Added missing conversation history management methods to GroqAgentState")
