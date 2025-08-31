from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json
from json_db import db, get_db, JsonDBSession
from models import (
    OrganizationCreate, OrganizationResponse,
    MembershipCreate, MembershipResponse,
    OrganizationInvite
)
from datetime import datetime

router = APIRouter(prefix="/organizations", tags=["organizations"])

# Organization endpoints
@router.post("/", response_model=OrganizationResponse)
def create_organization(
    org: OrganizationCreate,
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a new organization"""
    # Create organization
    org_data = org.dict()
    org_data["owner_id"] = 1  # For now, we'll use a placeholder
    org_data["created_at"] = datetime.now().isoformat()
    
    new_org = db_session.db.insert("organizations", org_data)
    
    # Create membership for the owner
    membership_data = {
        "user_id": 1,  # Placeholder for now
        "organization_id": new_org["id"],
        "role": "owner",
        "created_at": datetime.now().isoformat()
    }
    db_session.db.insert("memberships", membership_data)
    
    return new_org

@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    db_session: JsonDBSession = Depends(get_db)
):
    """Get organization by ID"""
    org = db_session.db.find_one("organizations", id=org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    db_session: JsonDBSession = Depends(get_db)
):
    """List all organizations"""
    return db_session.db.find("organizations")

# Membership endpoints
@router.post("/memberships", response_model=MembershipResponse)
def create_membership(
    membership: MembershipCreate,
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a new membership"""
    # Check if membership already exists
    existing = db_session.db.find_one(
        "memberships",
        user_id=membership.user_id,
        organization_id=membership.organization_id
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="Membership already exists")
    
    # Create membership
    membership_data = membership.dict()
    membership_data["created_at"] = datetime.now().isoformat()
    
    return db_session.db.insert("memberships", membership_data)

@router.post("/invite")
def invite_member(invite: OrganizationInvite):
    """Invite a member to an organization (simplified)"""
    # In a real app, this would send an email invitation
    # For now, we'll just return a success message
    return {"message": f"Invitation sent to {invite.email} for organization {invite.organization_id}"}