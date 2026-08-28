from fastapi import APIRouter, status  # pyright: ignore[reportMissingImports]

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(payload: SignupRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.signup(payload)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate an existing user",
)
def login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.login(payload)


@router.post(
    "/admin/login",
    response_model=AuthResponse,
    summary="Authenticate an admin user",
)
def admin_login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return auth_service.admin_login(payload)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the currently authenticated user",
)
def me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)
