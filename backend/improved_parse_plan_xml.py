def _parse_plan_xml(self, plan_xml: str) -> list:
    """Parse XML plan into structured chunks using regex to handle malformed XML"""
    
    try:
        # Extract plan XML from response
        plan_match = re.search(r'<plan>(.*?)</plan>', plan_xml, re.DOTALL)
        if not plan_match:
            print("❌ No <plan> tags found in response")
            print("Full response for debugging:")
            print(plan_xml[:500] + "..." if len(plan_xml) > 500 else plan_xml)
            return None
        
        plan_content = plan_match.group(1)
        
        # Debug: Show extracted XML
        print("\n📄 Extracted XML plan:")
        print("-" * 60)
        print(f"<plan>{plan_content[:1000]}...</plan>" if len(plan_content) > 1000 else f"<plan>{plan_content}</plan>")
        print("-" * 60)
        
        # Extract steps using regex (more robust than XML parsing)
        steps = []
        steps_match = re.search(r'<steps>(.*?)</steps>', plan_content, re.DOTALL)
        
        if not steps_match:
            print("❌ No <steps> element found in plan")
            return None
        
        steps_content = steps_match.group(1)
        
        # Find all step elements
        step_pattern = r'<step\s+id="(\d+)"\s+name="([^"]+)"\s+priority="([^"]+)"\s+dependencies="([^"]*)">(.*?)</step>'
        
        for match in re.finditer(step_pattern, steps_content, re.DOTALL):
            step_id = match.group(1)
            step_name = match.group(2)
            priority = match.group(3)
            dependencies = match.group(4)
            step_content = match.group(5)
            
            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', step_content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            
            # Extract files
            files = []
            files_match = re.search(r'<files>(.*?)</files>', step_content, re.DOTALL)
            
            if files_match:
                files_content = files_match.group(1)
                
                # Handle both correct and malformed file tags
                # Pattern 1: Correct format <file path="...">...</file>
                file_pattern1 = r'<file\s+path="([^"]+)">([^<]*)</file>'
                
                # Pattern 2: Malformed format <path/to/file.ext>description</file>
                file_pattern2 = r'<([^/>\s]+/[^>]+)>([^<]*)</file>'
                
                # First, find all correctly formatted files
                for file_match in re.finditer(file_pattern1, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    
                    # Convert [id] back to {id} for proper path handling
                    if '[' in desc and ']' in desc:
                        desc = desc.replace('[', '{').replace(']', '}')
                    
                    files.append({
                        'path': path,
                        'description': desc
                    })
                
                # Then, find malformed files
                for file_match in re.finditer(file_pattern2, files_content):
                    path = file_match.group(1)
                    desc = file_match.group(2).strip()
                    
                    # Skip if this was already matched by the correct pattern
                    if not any(f['path'] == path for f in files):
                        print(f"⚠️  Found malformed file tag: <{path}>")
                        
                        # Convert [id] back to {id} for proper path handling
                        if '[' in desc and ']' in desc:
                            desc = desc.replace('[', '{').replace(']', '}')
                        
                        files.append({
                            'path': path,
                            'description': desc
                        })
            
            step_data = {
                'id': step_id,
                'name': step_name,
                'priority': priority,
                'dependencies': dependencies.split(',') if dependencies else [],
                'description': description,
                'files': files
            }
            
            steps.append(step_data)
        
        return steps
        
    except Exception as e:
        print(f"❌ Error parsing plan: {e}")
        return None