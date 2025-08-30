from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from models import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    UserOrganizationCreate, UserOrganizationUpdate, UserOrganizationResponse,
    UserRole, InvitationCreate, InvitationResponse, InvitationStatus
)
from json_db import JsonDBSession, get_db
from routes.auth import get_current_active_user, AuthUserResponse # Import AuthUserResponse

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])

# Helper to check user role within an organization
def check_organization_role(
    db_session: JsonDBSession,
    user_id: int,
    organization_id: int,
    required_roles: Optional[List[UserRole]] = None
) -> UserOrganizationResponse:
    user_org = db_session.db.find_one(
        "user_organizations", user_id=user_id, organization_id=organization_id
    )
    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    user_org_model = UserOrganizationResponse(**user_org)
    if required_roles and user_org_model.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required roles: {', '.join([r.value for r in required_roles])}"
        )
    return user_org_model

# --- Organization Endpoints ---

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_data: OrganizationCreate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Create a new organization."""
    # Check if user already owns an organization with this name
    existing_org = db_session.db.find_one("organizations", name=org_data.name)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this name already exists."
        )

    org_dict = org_data.dict()
    org_dict["owner_id"] = current_user.id
    new_org = db_session.db.insert("organizations", org_dict)

    # Automatically add the creator as an OWNER of the organization
    user_org_data = {
        "user_id": current_user.id,
        "organization_id": new_org["id"],
        "role": UserRole.OWNER.value
    }
    db_session.db.insert("user_organizations", user_org_data)

    return OrganizationResponse(**new_org)

@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Get details of a specific organization."""
    org = db_session.db.find_one("organizations", id=org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Ensure user is a member of this organization
    check_organization_role(db_session, current_user.id, org_id)

    return OrganizationResponse(**org)

@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Update an organization's details (Admin/Owner only)."""
    # Check if user has permission (Admin or Owner)
    check_organization_role(db_session, current_user.id, org_id, [UserRole.ADMIN, UserRole.OWNER])

    updated_org = db_session.db.update_one("organizations", {"id": org_id}, org_update.dict(exclude_unset=True))
    if not updated_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse(**updated_org)

@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Delete an organization (Owner only)."""
    # Check if user is the owner
    org = db_session.db.find_one("organizations", id=org_id)
    if not org or org["owner_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete the organization")

    # Delete all associated user_organizations, tasks, comments, invitations
    db_session.db.delete_many("user_organizations", organization_id=org_id)
    db_session.db.delete_many("tasks", organization_id=org_id)
    db_session.db.delete_many("comments", organization_id=org_id) # Assuming comments have org_id or cascade from tasks
    db_session.db.delete_many("invitations", organization_id=org_id)

    if not db_session.db.delete_one("organizations", id=org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return

@router.get("/me/organizations", response_model=List[OrganizationResponse])
def get_my_organizations(
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Get all organizations the current user is a member of."""
    user_orgs = db_session.db.find_all("user_organizations", user_id=current_user.id)
    org_ids = [uo["organization_id"] for uo in user_orgs]
    
    organizations = []
    for org_id in org_ids:
        org = db_session.db.find_one("organizations", id=org_id)
        if org:
            organizations.append(OrganizationResponse(**org))
    return organizations

# --- UserOrganization (Membership) Endpoints ---

@router.get("/{org_id}/members", response_model=List[UserOrganizationResponse])
def get_organization_members(
    org_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Get all members of a specific organization."""
    # Ensure user is a member of this organization
    check_organization_role(db_session, current_user.id, org_id)

    members = db_session.db.find_all("user_organizations", organization_id=org_id)
    return [UserOrganizationResponse(**m) for m in members]

@router.patch("/{org_id}/members/{member_id}", response_model=UserOrganizationResponse)
def update_member_role(
    org_id: int,
    member_id: int,
    user_org_update: UserOrganizationUpdate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Update a member's role within an organization (Admin/Owner only)."""
    # Check if current user has permission (Admin or Owner)
    current_user_org = check_organization_role(db_session, current_user.id, org_id, [UserRole.ADMIN, UserRole.OWNER])

    # Prevent changing owner role if not owner themselves
    if user_org_update.role == UserRole.OWNER and current_user_org.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can assign owner role."
        )
    
    # Prevent owner from demoting themselves if they are the only owner
    if current_user_org.user_id == member_id and user_org_update.role != UserRole.OWNER:
        all_owners = db_session.db.find_all("user_organizations", organization_id=org_id, role=UserRole.OWNER.value)
        if len(all_owners) == 1 and all_owners[0]["user_id"] == member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the sole owner of the organization."
            )

    updated_member = db_session.db.update_one(
        "user_organizations",
        {"user_id": member_id, "organization_id": org_id},
        user_org_update.dict(exclude_unset=True)
    )
    if not updated_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this organization")
    return UserOrganizationResponse(**updated_member)

@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    org_id: int,
    member_id: int,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Remove a member from an organization (Admin/Owner only)."""
    # Check if current user has permission (Admin or Owner)
    current_user_org = check_organization_role(db_session, current_user.id, org_id, [UserRole.ADMIN, UserRole.OWNER])

    # Prevent owner from removing themselves if they are the only owner
    if current_user_org.user_id == member_id:
        all_owners = db_session.db.find_all("user_organizations", organization_id=org_id, role=UserRole.OWNER.value)
        if len(all_owners) == 1 and all_owners[0]["user_id"] == member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the sole owner of the organization."
            )

    if not db_session.db.delete_one("user_organizations", user_id=member_id, organization_id=org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this organization")
    return

# --- Invitation Endpoints ---

@router.post("/{org_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    org_id: int,
    invitation_data: InvitationCreate,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Create an invitation to join an organization (Admin/Owner only)."""
    # Check if current user has permission (Admin or Owner)
    check_organization_role(db_session, current_user.id, org_id, [UserRole.ADMIN, UserRole.OWNER])

    # Ensure the organization exists
    org = db_session.db.find_one("organizations", id=org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check if user is already a member
    existing_member = db_session.db.find_one("user_organizations", user_id=current_user.id, organization_id=org_id)
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization."
        )

    # Check if an invitation already exists for this email and organization
    existing_invitation = db_session.db.find_one(
        "invitations", email=invitation_data.email, organization_id=org_id, status=InvitationStatus.PENDING.value
    )
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation for this email already exists for this organization."
        )

    # Generate a unique token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7) # Invitation valid for 7 days

    invitation_dict = invitation_data.dict()
    invitation_dict.update({
        "organization_id": org_id,
        "token": token,
        "invited_by_user_id": current_user.id,
        "status": InvitationStatus.PENDING.value,
        "expires_at": expires_at.isoformat() # Store as ISO format string
    })

    new_invitation = db_session.db.insert("invitations", invitation_dict)
    return InvitationResponse(**new_invitation)

@router.get("/invitations/{token}", response_model=InvitationResponse)
def get_invitation_by_token(
    token: str,
    db_session: JsonDBSession = Depends(get_db)
):
    """Get invitation details by token."""
    invitation = db_session.db.find_one("invitations", token=token)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or invalid token")
    
    # Check if invitation has expired
    if datetime.fromisoformat(invitation["expires_at"]) < datetime.now():
        # Update status to expired if it's still pending
        if invitation["status"] == InvitationStatus.PENDING.value:
            db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.EXPIRED.value})
            invitation["status"] = InvitationStatus.EXPIRED.value # Update in memory for response
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")

    if invitation["status"] != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation is {invitation['status']}")

    return InvitationResponse(**invitation)

@router.post("/invitations/{token}/accept", response_model=UserOrganizationResponse)
def accept_invitation(
    token: str,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Accept an invitation to join an organization."""
    invitation = db_session.db.find_one("invitations", token=token)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or invalid token")

    if datetime.fromisoformat(invitation["expires_at"]) < datetime.now():
        db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.EXPIRED.value})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")

    if invitation["status"] != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation is {invitation['status']}")

    if invitation["email"] != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is not for your email address."
        )

    # Check if user is already a member of this organization
    existing_membership = db_session.db.find_one(
        "user_organizations", user_id=current_user.id, organization_id=invitation["organization_id"]
    )
    if existing_membership:
        db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.ACCEPTED.value})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this organization."
        )

    # Add user to the organization
    user_org_data = {
        "user_id": current_user.id,
        "organization_id": invitation["organization_id"],
        "role": invitation["role"]
    }
    new_membership = db_session.db.insert("user_organizations", user_org_data)

    # Mark invitation as accepted
    db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.ACCEPTED.value})

    return UserOrganizationResponse(**new_membership)

@router.post("/invitations/{token}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_invitation(
    token: str,
    current_user: AuthUserResponse = Depends(get_current_active_user),
    db_session: JsonDBSession = Depends(get_db)
):
    """Decline an invitation to join an organization."""
    invitation = db_session.db.find_one("invitations", token=token)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or invalid token")

    if datetime.fromisoformat(invitation["expires_at"]) < datetime.now():
        db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.EXPIRED.value})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")

    if invitation["status"] != InvitationStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation is {invitation['status']}")

    if invitation["email"] != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is not for your email address."
        )

    db_session.db.update_one("invitations", {"id": invitation["id"]}, {"status": InvitationStatus.DECLINED.value})
    return