from json_db import db
from models import (
    UserCreate, OrganisationCreate, InvitationCreate,
    TaskCreate, CommentCreate
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User services
def create_user(user_data: UserCreate, organisation_id=None, role="member"):
    hashed_password = pwd_context.hash(user_data.password)
    user = db.insert("users", {
        "email": user_data.email,
        "hashed_password": hashed_password,
        "name": user_data.name,
        "is_active": True,
        "organisation_id": organisation_id,
        "role": role
    })
    return user

def get_user_by_email(email: str):
    return db.find_one("users", email=email)

def get_user_by_id(user_id: int):
    return db.find_one("users", id=user_id)

def update_user_org(user_id: int, organisation_id: int):
    return db.update_one("users", {"id": user_id}, {"organisation_id": organisation_id})

# Organisation services
def create_organisation(org_data: OrganisationCreate, owner_id: int):
    org = db.insert("organisations", {
        "name": org_data.name,
        "owner_id": owner_id
    })
    return org

def get_organisation(org_id: int):
    return db.find_one("organisations", id=org_id)

def get_organisations_for_user(user_id: int):
    return db.find_all("organisations", owner_id=user_id)

# Invitation services
def create_invitation(invite_data: InvitationCreate, invited_by: int):
    invitation = db.insert("invitations", {
        "email": invite_data.email,
        "organisation_id": invite_data.organisation_id,
        "invited_by": invited_by,
        "status": "pending"
    })
    return invitation

def get_invitation(invitation_id: int):
    return db.find_one("invitations", id=invitation_id)

def get_invitations_for_org(org_id: int):
    return db.find_all("invitations", organisation_id=org_id)

def update_invitation_status(invitation_id: int, status: str):
    return db.update_one("invitations", {"id": invitation_id}, {"status": status})

# Task services
def create_task(task_data: TaskCreate, creator_id: int):
    task = db.insert("tasks", {
        "title": task_data.title,
        "description": task_data.description,
        "assignee_id": task_data.assignee_id,
        "organisation_id": task_data.organisation_id,
        "status": "todo",
        "creator_id": creator_id
    })
    return task

def get_task(task_id: int):
    return db.find_one("tasks", id=task_id)

def get_tasks_for_org(org_id: int):
    return db.find_all("tasks", organisation_id=org_id)

def update_task_status(task_id: int, status: str):
    return db.update_one("tasks", {"id": task_id}, {"status": status})

def assign_task(task_id: int, assignee_id: int):
    return db.update_one("tasks", {"id": task_id}, {"assignee_id": assignee_id})

# Comment services
def create_comment(comment_data: CommentCreate):
    comment = db.insert("comments", {
        "task_id": comment_data.task_id,
        "author_id": comment_data.author_id,
        "content": comment_data.content
    })
    return comment

def get_comments_for_task(task_id: int):
    return db.find_all("comments", task_id=task_id)