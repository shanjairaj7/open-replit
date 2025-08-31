from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json
from json_db import db, get_db, JsonDBSession
from models import TaskCreate, TaskResponse, CommentCreate, CommentResponse
from datetime import datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Task endpoints
@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a new task"""
    # Check if organization exists
    org = db_session.db.find_one("organizations", id=task.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Create task
    task_data = task.dict()
    task_data["created_by"] = 1  # Placeholder for now
    task_data["created_at"] = datetime.now().isoformat()
    task_data["updated_at"] = datetime.now().isoformat()
    
    return db_session.db.insert("tasks", task_data)

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db_session: JsonDBSession = Depends(get_db)
):
    """Get task by ID"""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    organization_id: int,
    db_session: JsonDBSession = Depends(get_db)
):
    """List all tasks for an organization"""
    tasks = db_session.db.find("tasks", organization_id=organization_id)
    return tasks

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskCreate,
    db_session: JsonDBSession = Depends(get_db)
):
    """Update a task"""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = task_update.dict()
    task_data["updated_at"] = datetime.now().isoformat()
    
    updated_task = db_session.db.update_one(
        "tasks",
        {"id": task_id},
        task_data
    )
    
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return updated_task

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db_session: JsonDBSession = Depends(get_db)
):
    """Delete a task"""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db_session.db.delete_one("tasks", {"id": task_id})
    return {"message": "Task deleted successfully"}

# Comment endpoints
@router.post("/{task_id}/comments", response_model=CommentResponse)
def create_comment(
    task_id: int,
    comment: CommentCreate,
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a comment on a task"""
    # Check if task exists
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create comment
    comment_data = comment.dict()
    comment_data["task_id"] = task_id
    comment_data["created_by"] = 1  # Placeholder for now
    comment_data["created_at"] = datetime.now().isoformat()
    
    return db_session.db.insert("comments", comment_data)

@router.get("/{task_id}/comments", response_model=List[CommentResponse])
def list_comments(
    task_id: int,
    db_session: JsonDBSession = Depends(get_db)
):
    """List all comments for a task"""
    # Check if task exists
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    comments = db_session.db.find("comments", task_id=task_id)
    return comments