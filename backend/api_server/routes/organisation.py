from fastapi import APIRouter, Depends, HTTPException
from models import OrganisationCreate, OrganisationResponse, InvitationCreate, InvitationResponse
from services import (
    create_organisation, get_organisation, get_organisations_for_user,
    create_invitation, get_invitations_for_org, update_invitation_status
)
from routes.auth import get_current_user

router = APIRouter(prefix="/organisations", tags=["organisations"])

@router.post("/", response_model=OrganisationResponse)
def create_org(org: OrganisationCreate, user=Depends(get_current_user)):
    organisation = create_organisation(org, owner_id=user["id"])
    return OrganisationResponse(**organisation)

@router.get("/", response_model=list[OrganisationResponse])
def list_orgs(user=Depends(get_current_user)):
    orgs = get_organisations_for_user(user["id"])
    return [OrganisationResponse(**o) for o in orgs]

@router.get("/{org_id}", response_model=OrganisationResponse)
def get_org(org_id: int, user=Depends(get_current_user)):
    org = get_organisation(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return OrganisationResponse(**org)

@router.post("/{org_id}/invite", response_model=InvitationResponse)
def invite_user(org_id: int, invite: InvitationCreate, user=Depends(get_current_user)):
    if invite.organisation_id != org_id:
        raise HTTPException(status_code=400, detail="Organisation ID mismatch")
    invitation = create_invitation(invite, invited_by=user["id"])
    return InvitationResponse(**invitation)

@router.get("/{org_id}/invitations", response_model=list[InvitationResponse])
def list_invitations(org_id: int, user=Depends(get_current_user)):
    invitations = get_invitations_for_org(org_id)
    return [InvitationResponse(**i) for i in invitations]

@router.post("/invitations/{invitation_id}/status")
def update_invite_status(invitation_id: int, status: str, user=Depends(get_current_user)):
    success = update_invitation_status(invitation_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"success": True}