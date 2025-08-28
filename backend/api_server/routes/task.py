from fastapi import APIRouter, Depends, HTTPException
from models import TaskCreate, TaskResponse, CommentCreate, CommentResponse
from services import (
    create_task, get_task, get_tasks_for_org, update_task_status, assign_task,
    create_comment, get_comments_for_task
)
from routes.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
def create_new_task(task: TaskCreate, user=Depends(get_current_user)):
    new_task = create_task(task, creator_id=user["id"])
    return TaskResponse(**new_task)

@router.get("/organisation/{org_id}", response_model=list[TaskResponse])
def list_tasks(org_id: int, user=Depends(get_current_user)):
    tasks = get_tasks_for_org(org_id)
    return [TaskResponse(**t) for t in tasks]

@router.get("/{task_id}", response_model=TaskResponse)
def get_task_detail(task_id: int, user=Depends(get_current_user)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task)

@router.post("/{task_id}/status")
def update_status(task_id: int, status: str, user=Depends(get_current_user)):
    success = update_task_status(task_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@router.post("/{task_id}/assign")
def assign(task_id: int, assignee_id: int, user=Depends(get_current_user)):
    success = assign_task(task_id, assignee_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@router.post("/{task_id}/comments", response_model=CommentResponse)
def add_comment(task_id: int, comment: CommentCreate, user=Depends(get_current_user)):
    if comment.task_id != task_id:
        raise HTTPException(status_code=400, detail="Task ID mismatch")
    new_comment = create_comment(comment)
    return CommentResponse(**new_comment)

@router.get("/{task_id}/comments", response_model=list[CommentResponse])
def list_comments(task_id: int, user=Depends(get_current_user)):
    comments = get_comments_for_task(task_id)
    return [CommentResponse(**c) for c in comments]