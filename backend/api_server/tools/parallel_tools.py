"""
Parallel Tool Execution Handler
Handles concurrent execution of multiple actions for improved efficiency
"""

import concurrent.futures
import threading
from typing import Dict, List, Any


class ParallelToolHandler:
    """Handles parallel execution of multiple tool actions"""

    def __init__(self, agent_instance):
        """Initialize with reference to the main agent instance"""
        self.agent = agent_instance

    def handle_parallel_execution(self, action: dict) -> dict:
        """Handle parallel tool execution - run multiple actions concurrently"""
        print(f"⚡ Parallel tool execution triggered")

        try:
            # Extract the list of actions to run in parallel
            actions = action.get('actions', [])
            if not actions:
                return {"status": "error", "message": "No actions provided for parallel execution"}

            print(f"📋 Processing {len(actions)} actions in parallel")

            # Group actions by type for efficient processing
            read_actions = []
            command_actions = []
            other_actions = []

            for act in actions:
                action_type = act.get('type')
                if action_type == 'read_file':
                    read_actions.append(act)
                elif action_type == 'run_command':
                    command_actions.append(act)
                else:
                    other_actions.append(act)

            print(f"📊 Action breakdown: {len(read_actions)} reads, {len(command_actions)} commands, {len(other_actions)} others")

            # Validate that only supported actions are included
            if other_actions:
                unsupported_types = list(set(act.get('type', 'unknown') for act in other_actions))
                return {
                    "status": "error",
                    "message": f"Parallel execution only supports 'read_file' and 'run_command' actions. Unsupported actions found: {', '.join(unsupported_types)}",
                    "unsupported_actions": unsupported_types,
                    "supported_actions": ["read_file", "run_command"]
                }

            results = []
            errors = []

            # Process read_file actions in parallel
            if read_actions:
                print(f"📖 Processing {len(read_actions)} read_file actions...")
                read_results = self._execute_parallel_reads(read_actions)
                results.extend(read_results['results'])
                errors.extend(read_results['errors'])

            # Process run_command actions in parallel
            if command_actions:
                print(f"💻 Processing {len(command_actions)} run_command actions...")
                command_results = self._execute_parallel_commands(command_actions)
                results.extend(command_results['results'])
                errors.extend(command_results['errors'])


            # Compile final result
            success_count = len([r for r in results if r.get('success')])
            total_count = len(actions)

            result_summary = {
                "status": "success" if len(errors) == 0 else "partial_success",
                "total_actions": total_count,
                "successful_actions": success_count,
                "failed_actions": len(errors),
                "results": results,
                "errors": errors
            }

            print(f"✅ Parallel execution completed: {success_count}/{total_count} actions successful")
            if errors:
                print(f"❌ {len(errors)} actions failed")

            return result_summary

        except Exception as e:
            print(f"❌ Parallel execution failed: {e}")
            return {"status": "error", "message": f"Parallel execution failed: {str(e)}"}

    def _execute_parallel_reads(self, read_actions: list) -> dict:
        """Execute multiple read_file actions in parallel"""
        results = []
        errors = []
        lock = threading.Lock()

        def read_single_file(act):
            try:
                file_path = act.get('path')
                start_line = act.get('start_line')
                end_line = act.get('end_line')

                print(f"📖 Reading file: {file_path}")
                content = self.agent._read_file_via_api(file_path, start_line, end_line)

                if content is not None:
                    # Track that this file has been read
                    with lock:
                        self.agent.read_files_tracker.add(file_path)
                        self.agent.read_files_persistent.add(file_path)
                        self.agent._save_read_files_tracking()

                    result = {
                        "action_type": "read_file",
                        "file_path": file_path,
                        "success": True,
                        "content": content,
                        "content_length": len(content)
                    }
                    print(f"✅ Successfully read {len(content)} chars from {file_path}")
                else:
                    result = {
                        "action_type": "read_file",
                        "file_path": file_path,
                        "success": False,
                        "error": "Failed to read file"
                    }
                    print(f"❌ Failed to read file: {file_path}")

                with lock:
                    results.append(result)

            except Exception as e:
                error_info = {
                    "action_type": "read_file",
                    "file_path": act.get('path'),
                    "success": False,
                    "error": str(e)
                }
                with lock:
                    errors.append(error_info)
                    results.append(error_info)

        # Execute reads in parallel with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(read_actions), 5)) as executor:
            futures = [executor.submit(read_single_file, act) for act in read_actions]
            concurrent.futures.wait(futures)

        return {"results": results, "errors": errors}

    def _execute_parallel_commands(self, command_actions: list) -> dict:
        """Execute multiple run_command actions in parallel"""
        results = []
        errors = []
        lock = threading.Lock()

        def run_single_command(act):
            try:
                command = act.get('command')
                working_dir = act.get('working_dir') or act.get('cwd')

                print(f"💻 Executing command: {command}")
                if working_dir:
                    print(f"   Working directory: {working_dir}")

                # Execute command using VM API
                output = self.agent._execute_command_on_vm(command, working_dir, act)

                result = {
                    "action_type": "run_command",
                    "command": command,
                    "working_dir": working_dir,
                    "success": True,
                    "output": output,
                    "output_length": len(output) if output else 0
                }
                print(f"✅ Command completed: {command[:50]}...")

                with lock:
                    results.append(result)

            except Exception as e:
                error_info = {
                    "action_type": "run_command",
                    "command": act.get('command'),
                    "success": False,
                    "error": str(e)
                }
                with lock:
                    errors.append(error_info)
                    results.append(error_info)

        # Execute commands in parallel with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(command_actions), 3)) as executor:
            futures = [executor.submit(run_single_command, act) for act in command_actions]
            concurrent.futures.wait(futures)

        return {"results": results, "errors": errors}

    def _execute_single_action(self, action: dict):
        """Execute a single action (fallback for unsupported parallel actions)"""
        action_type = action.get('type')
        print(f"🔄 Executing single action: {action_type}")

        # Route to appropriate handler based on action type
        if action_type == 'read_file':
            content = self.agent._handle_read_file_interrupt(action)
            return {
                "action_type": "read_file",
                "file_path": action.get('path'),
                "success": content is not None,
                "content": content
            }
        elif action_type == 'run_command':
            output = self.agent._handle_run_command_interrupt(action)
            return {
                "action_type": "run_command",
                "command": action.get('command'),
                "success": True,
                "output": output
            }
        else:
            # For other action types, try to find and call the appropriate handler
            handler_name = f"_handle_{action_type}_interrupt"
            if hasattr(self.agent, handler_name):
                handler = getattr(self.agent, handler_name)
                result = handler(action)
                return {
                    "action_type": action_type,
                    "success": result.get('status') == 'success' if isinstance(result, dict) else True,
                    "result": result
                }
            else:
                raise Exception(f"No handler found for action type: {action_type}")