from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User models
class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

# Organization models
class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: int
    owner_id: int
    created_at: datetime

class OrganizationInvite(BaseModel):
    email: str
    organization_id: int

# Task models
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "To Do"

class TaskCreate(TaskBase):
    organization_id: int

class TaskResponse(TaskBase):
    id: int
    created_by: int
    assigned_to: Optional[int] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime

# Comment models
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    task_id: int

class CommentResponse(CommentBase):
    id: int
    task_id: int
    created_by: int
    created_at: datetime

# Membership models
class MembershipBase(BaseModel):
    user_id: int
    organization_id: int
    role: str = "member"

class MembershipCreate(MembershipBase):
    pass

class MembershipResponse(MembershipBase):
    id: int
    created_at: datetime