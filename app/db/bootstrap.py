from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole, as_role
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


def bootstrap_admin() -> None:
    """Create the first store Admin from env, once. Never resets an existing account."""
    settings = get_settings()
    email = settings.BOOTSTRAP_ADMIN_EMAIL.strip().lower()
    password = settings.BOOTSTRAP_ADMIN_PASSWORD
    name = settings.BOOTSTRAP_ADMIN_NAME.strip() or "Admin"
    if not email or not password:
        return
    if len(password) < 8:
        logger.warning("Bootstrap admin skipped: BOOTSTRAP_ADMIN_PASSWORD is too short")
        return

    db = SessionLocal()
    try:
        users = UserRepository(db)
        organizations = OrganizationRepository(db)
        existing = users.get_by_email(email)
        if existing is not None:
            if as_role(existing.role) is UserRole.ADMIN:
                logger.info("Bootstrap admin skipped: %s already exists", email)
            else:
                logger.warning(
                    "Bootstrap admin skipped: %s already exists and is not an admin",
                    email,
                )
            return

        org = organizations.get_by_slug(settings.DEFAULT_ORGANIZATION_SLUG)
        if org is None:
            org = organizations.create(
                name=settings.PROJECT_NAME,
                slug=settings.DEFAULT_ORGANIZATION_SLUG,
                shop_url=settings.SHOP_APP_URL,
            )
        if organizations.has_admin(org.id):
            logger.info("Bootstrap admin skipped: store already has an admin")
            return

        user = users.create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            email_verified=True,
        )
        organizations.add_membership(
            user_id=user.id,
            organization_id=org.id,
            role=UserRole.ADMIN,
        )
        users.set_active_organization(user, org.id, role=UserRole.ADMIN)
        logger.info("Bootstrap admin created for %s", email)
    except Exception:
        logger.exception("Bootstrap admin failed")
        db.rollback()
    finally:
        db.close()
