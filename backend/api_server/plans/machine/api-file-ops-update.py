# Add these endpoints to the existing api.py file

@app.post("/file/create")
async def create_file(req: FileCreateRequest):
    """Create a new file in a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "create_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": {
            "file_path": req.file_path,
            "content": req.content,
            "overwrite": req.overwrite
        }
    })
    
    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/update")
async def update_file(req: FileUpdateRequest):
    """Update an existing file in a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "update_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": {
            "file_path": req.file_path,
            "content": req.content,
            "create_if_missing": req.create_if_missing
        }
    })
    
    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

@app.post("/file/delete")
async def delete_file(req: FileDeleteRequest):
    """Delete a file from a project"""
    job_id = str(uuid.uuid4())
    result_path = os.path.join(RESULT_DIR, f"{job_id}.json")

    # Ensure project is available
    success = await ensure_project_available(req.project_id)
    if not success:
        return {"error": f"Project {req.project_id} not found or failed to download"}

    # Create job message
    job_message = json.dumps({
        "job_id": job_id,
        "type": "delete_file",
        "project_id": req.project_id,
        "working_dir": req.working_dir,
        "payload": req.file_path
    })
    
    queue_client.send_message(job_message)

    # Wait for result
    time_waited = 0
    while not os.path.exists(result_path):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        time_waited += POLL_INTERVAL_SECONDS
        if time_waited > REQUEST_TIMEOUT_SECONDS:
            return {"error": "Request timed out"}

    with open(result_path, 'r') as f:
        result = json.load(f)

    os.remove(result_path)
    return result

# Add these Pydantic models at the top of the file with other models

class FileCreateRequest(BaseModel):
    project_id: str
    file_path: str
    content: str
    working_dir: Optional[str] = None
    overwrite: Optional[bool] = False

class FileUpdateRequest(BaseModel):
    project_id: str
    file_path: str
    content: str
    working_dir: Optional[str] = None
    create_if_missing: Optional[bool] = True

class FileDeleteRequest(BaseModel):
    project_id: str
    file_path: str
    working_dir: Optional[str] = None