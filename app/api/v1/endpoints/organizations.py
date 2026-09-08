from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from app.api.deps import CurrentUserDep, OrganizationServiceDep
from app.schemas.auth import AuthResponse
from app.schemas.common import MessageResponse
from app.schemas.organization import (
    PublicStoreResponse,
    TeamMemberUpdateRequest,
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingPortalResponse,
    BillingResponse,
    InviteAcceptRequest,
    InviteCreateRequest,
    InvitePreview,
    InviteRead,
    MembershipRead,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    SwitchOrganizationRequest,
    TeamResponse,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/public", response_model=PublicStoreResponse)
def public_store(slug: str | None = None, organizations: OrganizationServiceDep = None):
    return organizations.public_store(slug)


@router.get("/current", response_model=OrganizationResponse)
def get_current_store(current_user: CurrentUserDep, organizations: OrganizationServiceDep):
    return organizations.get_current(current_user)


@router.patch("/current", response_model=OrganizationResponse)
def update_current_store(
    payload: OrganizationUpdateRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.update_settings(payload, current_user=current_user)


@router.post("/current/logo", response_model=OrganizationResponse)
def upload_current_store_logo(
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
    file: UploadFile = File(...),
):
    return organizations.upload_logo(file, current_user=current_user)


@router.delete("/current/logo", response_model=OrganizationResponse)
def delete_current_store_logo(current_user: CurrentUserDep, organizations: OrganizationServiceDep):
    return organizations.delete_logo(current_user=current_user)


@router.post("", response_model=AuthResponse, status_code=201)
def create_store(
    payload: OrganizationCreateRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.create_store(payload, current_user=current_user)


@router.get("/memberships", response_model=list[MembershipRead])
def list_memberships(current_user: CurrentUserDep, organizations: OrganizationServiceDep):
    return organizations.list_memberships(current_user=current_user)


@router.post("/switch", response_model=AuthResponse)
def switch_store(
    payload: SwitchOrganizationRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.switch(payload, current_user=current_user)


@router.get("/team", response_model=TeamResponse)
def team(current_user: CurrentUserDep, organizations: OrganizationServiceDep):
    return organizations.team(current_user=current_user)


@router.post("/invites", response_model=InviteRead, status_code=201)
def create_invite(
    payload: InviteCreateRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.invite(payload, current_user=current_user)


@router.get("/invites/preview", response_model=InvitePreview)
def preview_invite(token: str, organizations: OrganizationServiceDep):
    return organizations.preview_invite(token)


@router.post("/invites/accept", response_model=AuthResponse)
def accept_invite(payload: InviteAcceptRequest, organizations: OrganizationServiceDep):
    return organizations.accept_invite(payload)


@router.delete("/invites/{invite_id}", response_model=MessageResponse)
def revoke_invite(
    invite_id: UUID,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.revoke_invite(invite_id, current_user=current_user)


@router.patch("/team/{user_id}", response_model=TeamResponse)
def update_team_member(
    user_id: UUID,
    payload: TeamMemberUpdateRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.update_member(user_id, payload, current_user=current_user)


@router.delete("/team/{user_id}", response_model=MessageResponse)
def remove_team_member(
    user_id: UUID,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.remove_member(user_id, current_user=current_user)


@router.get("/billing", response_model=BillingResponse)
def billing(
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
    session_id: str | None = Query(default=None, alias="sessionId"),
):
    return organizations.billing(current_user=current_user, session_id=session_id)


@router.post("/billing/checkout", response_model=BillingCheckoutResponse)
def billing_checkout(
    payload: BillingCheckoutRequest,
    current_user: CurrentUserDep,
    organizations: OrganizationServiceDep,
):
    return organizations.billing_checkout(payload, current_user=current_user)


@router.post("/billing/portal", response_model=BillingPortalResponse)
def billing_portal(current_user: CurrentUserDep, organizations: OrganizationServiceDep):
    return organizations.billing_portal(current_user=current_user)
