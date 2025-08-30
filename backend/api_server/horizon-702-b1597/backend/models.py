"""
Pydantic models for the Project Management App.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- Enums ---
class UserRole(str, Enum):
    """Defines roles a user can have within an organization."""
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner" # Owner is implicitly an admin

class TaskStatus(str, Enum):
    """Defines possible statuses for a task."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BLOCKED = "Blocked"
    REVIEW = "Review"

class TaskPriority(str, Enum):
    """Defines possible priorities for a task."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class InvitationStatus(str, Enum):
    """Defines the status of an organization invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

# --- Base Models (for common fields like ID and timestamps) ---
class AppBaseModel(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# --- Organization Models ---
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class Organization(OrganizationBase, AppBaseModel):
    owner_id: int # ID of the user who owns/created the organization

class OrganizationResponse(Organization, AppBaseModel):
    pass

# --- UserOrganization (Membership) Models ---
class UserOrganizationBase(BaseModel):
    user_id: int
    organization_id: int
    role: UserRole = UserRole.MEMBER

class UserOrganizationCreate(UserOrganizationBase):
    pass

class UserOrganizationUpdate(BaseModel):
    role: Optional[UserRole] = None

class UserOrganization(UserOrganizationBase, AppBaseModel):
    pass

class UserOrganizationResponse(UserOrganization, AppBaseModel):
    pass

# --- Task Models ---
class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to_user_id: Optional[int] = None # User ID within the organization
    organization_id: int # The organization this task belongs to

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to_user_id: Optional[int] = None

class Task(TaskBase, AppBaseModel):
    created_by_user_id: int # User ID who created the task

class TaskResponse(Task, AppBaseModel):
    pass

# --- Comment Models ---
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    task_id: int
    user_id: int # User ID who made the comment

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=500)

class Comment(CommentBase, AppBaseModel):
    pass

class CommentResponse(Comment, AppBaseModel):
    pass

# --- Invitation Models ---
class InvitationBase(BaseModel):
    email: EmailStr
    organization_id: int
    role: UserRole = UserRole.MEMBER # Role the invited user will have

class InvitationCreate(InvitationBase):
    pass

class InvitationUpdate(BaseModel):
    status: Optional[InvitationStatus] = None
    role: Optional[UserRole] = None # Allow changing role before acceptance

class Invitation(InvitationBase, AppBaseModel):
    token: str # Unique token for the invitation link
    invited_by_user_id: int # User ID who sent the invitation
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: Optional[datetime] = None

class InvitationResponse(Invitation, AppBaseModel):
    pass