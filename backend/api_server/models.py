from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool
    organisation_id: Optional[int]
    role: str
    created_at: datetime

class OrganisationCreate(BaseModel):
    name: str

class OrganisationResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime

class InvitationCreate(BaseModel):
    email: EmailStr
    organisation_id: int

class InvitationResponse(BaseModel):
    id: int
    email: EmailStr
    organisation_id: int
    invited_by: int
    status: str
    created_at: datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int]
    organisation_id: int

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee_id: Optional[int]
    organisation_id: int
    status: str
    created_at: datetime

class CommentCreate(BaseModel):
    task_id: int
    author_id: int
    content: str

class CommentResponse(BaseModel):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime