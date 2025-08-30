from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime

from models import (
    TaskCreate, TaskUpdate, TaskResponse, TaskStatus,
    CommentCreate, CommentUpdate, CommentResponse,
    UserRole
)
from json_db import JsonDBSession, get_db
from routes.auth import get_current_active_user, AuthUserResponse # Import AuthUserResponse
from routes.organizations import check_organization_role # Re-use helper from organizations route

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# --- Task Endpoints ---

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a new task within an organization."""
    # Ensure user is a member of the organization the task belongs to
    check_organization_role(db_session, current_user.id, task_data.organization_id)

    # Ensure assigned_to_user_id is a member of the same organization
    if task_data.assigned_to_user_id:
        assigned_member = db_session.db.find_one(
            "user_organizations",
            user_id=task_data.assigned_to_user_id,
            organization_id=task_data.organization_id
        )
        if not assigned_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a member of this organization."
            )

    task_dict = task_data.dict()
    task_dict["created_by_user_id"] = current_user.id
    new_task = db_session.db.insert("tasks", task_dict)
    return TaskResponse(**new_task)

@router.get("/organization/{org_id}", response_model=List[TaskResponse])
def get_tasks_by_organization(
    org_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db),
    status_filter: Optional[TaskStatus] = None,
    assigned_to_me: Optional[bool] = False
):
    """Get all tasks for a specific organization, with optional filters."""
    # Ensure user is a member of this organization
    check_organization_role(db_session, current_user.id, org_id)

    query = {"organization_id": org_id}
    if status_filter:
        query["status"] = status_filter.value
    if assigned_to_me:
        query["assigned_to_user_id"] = current_user.id

    tasks = db_session.db.find_all("tasks", **query)
    return [TaskResponse(**t) for t in tasks]

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Get details of a specific task."""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Ensure user is a member of the organization the task belongs to
    check_organization_role(db_session, current_user.id, task["organization_id"])

    return TaskResponse(**task)

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Update a task's details."""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Ensure user is a member of the organization the task belongs to
    check_organization_role(db_session, current_user.id, task["organization_id"])

    # If assigned_to_user_id is being updated, ensure the new assignee is a member of the same organization
    if task_update.assigned_to_user_id is not None:
        assigned_member = db_session.db.find_one(
            "user_organizations",
            user_id=task_update.assigned_to_user_id,
            organization_id=task["organization_id"]
        )
        if not assigned_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a member of this organization."
            )

    updated_task = db_session.db.update_one("tasks", {"id": task_id}, task_update.dict(exclude_unset=True))
    if not updated_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found after update attempt")
    return TaskResponse(**updated_task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Delete a task (Admin/Owner of org, or task creator)."""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Check if user is admin/owner of the organization or the task creator
    user_org_role = check_organization_role(db_session, current_user.id, task["organization_id"])
    if user_org_role.role not in [UserRole.ADMIN, UserRole.OWNER] and task["created_by_user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins/owners or the task creator can delete this task."
        )

    # Delete associated comments first
    db_session.db.delete_many("comments", task_id=task_id)

    if not db_session.db.delete_one("tasks", id=task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found for deletion")
    return

# --- Comment Endpoints ---

@router.post("/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment_to_task(
    task_id: int,
    comment_data: CommentCreate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Add a comment to a task."""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Ensure user is a member of the organization the task belongs to
    check_organization_role(db_session, current_user.id, task["organization_id"])

    comment_dict = comment_data.dict()
    comment_dict["task_id"] = task_id
    comment_dict["user_id"] = current_user.id # Ensure comment is linked to current user
    new_comment = db_session.db.insert("comments", comment_dict)
    return CommentResponse(**new_comment)

@router.get("/{task_id}/comments", response_model=List[CommentResponse])
def get_comments_for_task(
    task_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Get all comments for a specific task."""
    task = db_session.db.find_one("tasks", id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Ensure user is a member of the organization the task belongs to
    check_organization_role(db_session, current_user.id, task["organization_id"])

    comments = db_session.db.find_all("comments", task_id=task_id)
    return [CommentResponse(**c) for c in comments]

@router.patch("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Update a comment (only by the comment creator)."""
    comment = db_session.db.find_one("comments", id=comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own comments."
        )
    
    # Ensure user is still a member of the organization the task belongs to
    task = db_session.db.find_one("tasks", id=comment["task_id"])
    if not task: # Task might have been deleted
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated task not found.")
    check_organization_role(db_session, current_user.id, task["organization_id"])

    updated_comment = db_session.db.update_one("comments", {"id": comment_id}, comment_update.dict(exclude_unset=True))
    if not updated_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found after update attempt")
    return CommentResponse(**updated_comment)

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Delete a comment (by comment creator or org admin/owner)."""
    comment = db_session.db.find_one("comments", id=comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    task = db_session.db.find_one("tasks", id=comment["task_id"])
    if not task: # Task might have been deleted
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated task not found.")

    user_org_role = check_organization_role(db_session, current_user.id, task["organization_id"])

    # Allow deletion if current user is the comment creator OR an admin/owner of the organization
    if comment["user_id"] != current_user.id and user_org_role.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments or comments as an organization admin/owner."
        )

    if not db_session.db.delete_one("comments", id=comment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found for deletion")
    return