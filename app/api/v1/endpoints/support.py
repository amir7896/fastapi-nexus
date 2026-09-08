from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SupportServiceDep
from app.api.pagination import LimitQuery, PageQuery, SearchQuery, build_pagination
from app.schemas.support import (
    SupportChannel,
    SupportColleagueListResponse,
    SupportContextType,
    SupportConversationCreateRequest,
    SupportConversationListResponse,
    SupportConversationResponse,
    SupportConversationStatus,
    SupportMessageCreateRequest,
    SupportMessageListResponse,
    SupportMessageResponse,
    SupportPresenceResponse,
    SupportStaffConversationCreateRequest,
    SupportUnreadResponse,
)

router = APIRouter(prefix="/support", tags=["Support"])


@router.get(
    "/conversations",
    response_model=SupportConversationListResponse,
    response_model_by_alias=True,
    summary="List support conversations",
)
def list_conversations(
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
    page: PageQuery = 1,
    limit: LimitQuery = 20,
    search: SearchQuery = None,
    status: SupportConversationStatus | None = Query(default=None),
    context_type: SupportContextType | None = Query(default=None, alias="contextType"),
    channel: SupportChannel = Query(default=SupportChannel.CUSTOMER),
    assigned_to_me: bool = Query(default=False, alias="assignedToMe"),
    unassigned: bool = Query(default=False),
) -> SupportConversationListResponse:
    return support_service.list_conversations(
        build_pagination(page, limit, search),
        current_user=current_user,
        status=status,
        context_type=context_type,
        channel=channel,
        assigned_to_me=assigned_to_me,
        unassigned=unassigned,
    )


@router.get(
    "/unread-count",
    response_model=SupportUnreadResponse,
    summary="Unread support conversation count",
)
def unread_count(
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
    channel: SupportChannel | None = Query(default=None),
) -> SupportUnreadResponse:
    return support_service.unread_count(current_user=current_user, channel=channel)


@router.get(
    "/colleagues",
    response_model=SupportColleagueListResponse,
    response_model_by_alias=True,
    summary="List staff colleagues for team chat",
)
def list_colleagues(
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportColleagueListResponse:
    return support_service.list_colleagues(current_user=current_user)


@router.get(
    "/presence",
    response_model=SupportPresenceResponse,
    response_model_by_alias=True,
    summary="Who is online in support",
)
def presence(
    _: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportPresenceResponse:
    return support_service.presence()


@router.post(
    "/conversations",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Start or continue a support conversation",
)
def start_conversation(
    payload: SupportConversationCreateRequest,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.start_conversation(payload, current_user=current_user)


@router.post(
    "/team/conversations",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Start or continue a staff team chat",
)
def start_team_conversation(
    payload: SupportStaffConversationCreateRequest,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.start_staff_conversation(payload, current_user=current_user)


@router.get(
    "/conversations/{conversation_id}",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Get a support conversation",
)
def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.get_conversation(conversation_id, current_user=current_user)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=SupportMessageListResponse,
    response_model_by_alias=True,
    summary="List messages in a support conversation",
)
def list_messages(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
    page: PageQuery = 1,
    limit: LimitQuery = 50,
    search: SearchQuery = None,
) -> SupportMessageListResponse:
    return support_service.list_messages(
        conversation_id,
        build_pagination(page, limit, search),
        current_user=current_user,
    )


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Mark a support conversation as seen",
)
def mark_conversation_read(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.mark_seen(conversation_id, current_user=current_user)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SupportMessageResponse,
    response_model_by_alias=True,
    summary="Send a support message",
)
def send_message(
    conversation_id: UUID,
    payload: SupportMessageCreateRequest,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportMessageResponse:
    return support_service.send_message(conversation_id, payload, current_user=current_user)


@router.post(
    "/conversations/{conversation_id}/close",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Close a support conversation",
)
def close_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.set_status(
        conversation_id,
        SupportConversationStatus.CLOSED,
        current_user=current_user,
    )


@router.post(
    "/conversations/{conversation_id}/reopen",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Reopen a support conversation",
)
def reopen_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.set_status(
        conversation_id,
        SupportConversationStatus.OPEN,
        current_user=current_user,
    )


@router.post(
    "/conversations/{conversation_id}/assign-me",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Claim a customer support ticket",
)
def assign_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.assign_to_me(conversation_id, current_user=current_user)


@router.post(
    "/conversations/{conversation_id}/unassign",
    response_model=SupportConversationResponse,
    response_model_by_alias=True,
    summary="Release a customer support ticket",
)
def unassign_conversation(
    conversation_id: UUID,
    current_user: CurrentUserDep,
    support_service: SupportServiceDep,
) -> SupportConversationResponse:
    return support_service.unassign(conversation_id, current_user=current_user)
