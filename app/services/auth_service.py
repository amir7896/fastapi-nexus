from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest
from app.schemas.user import UserRead

logger = get_logger(__name__)


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def signup(self, payload: SignupRequest) -> AuthResponse:
        if self._users.exists(payload.email):
            raise ConflictError("Email already exists")

        user = self._users.create(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            age=payload.age,
            role=UserRole.USER,
        )
        logger.info("Registered user %s", user.email)

        return AuthResponse(
            message="Signup successful",
            user=UserRead.model_validate(user),
        )

    def login(self, payload: LoginRequest) -> AuthResponse:
        user = self._authenticate(payload)
        return self._auth_response("Login successful", user)

    def admin_login(self, payload: LoginRequest) -> AuthResponse:
        user = self._authenticate(payload)
        if user.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin access required")

        return self._auth_response("Admin login successful", user)

    def _authenticate(self, payload: LoginRequest) -> User:
        user = self._users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        return user

    def _auth_response(self, message: str, user: User) -> AuthResponse:
        token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value,
        )
        return AuthResponse(
            message=message,
            user=UserRead.model_validate(user),
            access_token=token,
            token_type="bearer",
        )
