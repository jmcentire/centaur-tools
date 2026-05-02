# === Auth Dependencies (backend_api_auth_dependencies) v1 ===
#  Dependencies: uuid, fastapi, sqlalchemy, sqlalchemy.ext.asyncio, backend.api.database, backend.api.models, backend.api.auth.router
# FastAPI dependency injection functions for authentication. Provides user resolution from JWT session cookies with required and optional variants. Validates JWT tokens, queries database for user records, and raises HTTP 401 errors on authentication failures.

# Module invariants:
#   - All authentication failures in get_current_user result in HTTPException with status_code=401
#   - User.id field matches JWT 'sub' claim when successfully authenticated
#   - get_optional_user never raises exceptions, always returns User or None

AsyncSession = primitive  # SQLAlchemy async database session (from sqlalchemy.ext.asyncio)

class User:
    """User model from backend.api.models with at least an 'id' field (UUID)"""
    pass

class HTTPException:
    """FastAPI HTTP exception with status_code and detail fields"""
    pass

async def get_current_user(
    db: AsyncSession,
    session: str | None = None,
) -> User:
    """
    Resolves the authenticated user from a JWT session cookie. Returns User on success, raises HTTPException(401) on any authentication failure (missing cookie, invalid JWT, user not found in database).

    Preconditions:
      - session cookie must be present
      - session cookie must contain valid JWT
      - JWT payload must have 'sub' field containing valid UUID string
      - User with extracted UUID must exist in database

    Postconditions:
      - Returns User object from database matching JWT subject
      - User.id matches UUID extracted from JWT 'sub' field

    Errors:
      - missing_session_cookie (HTTPException): session parameter is None or empty
          status_code: 401
          detail: Not authenticated
      - invalid_jwt_or_uuid (HTTPException): decode_jwt() raises exception OR uuid.UUID() conversion fails
          status_code: 401
          detail: Invalid session
      - user_not_found (HTTPException): Database query returns None (no user with given UUID)
          status_code: 401
          detail: User not found

    Side effects: Executes database SELECT query against User table
    Idempotent: no
    """
    ...

async def get_optional_user(
    db: AsyncSession,
    session: str | None = None,
) -> User | None:
    """
    Resolves the authenticated user from a JWT session cookie, returning None instead of raising errors. Returns User if authentication succeeds, None for any failure (missing cookie, invalid JWT, user not found).

    Postconditions:
      - Returns User object if session valid and user exists in database
      - Returns None if session missing, invalid, or user not found
      - Never raises exceptions

    Side effects: Executes database SELECT query against User table if session cookie present
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['User', 'HTTPException', 'get_current_user', 'get_optional_user']
