# === Backend API Authentication Dependencies Interface (contracts_backend_api_auth_dependencies_interface) v1 ===
#  Dependencies: uuid, fastapi, sqlalchemy, sqlalchemy.ext.asyncio, backend.api.database, backend.api.models, backend.api.auth.router
# FastAPI dependency injection functions for user authentication and authorization. Provides get_current_user (strict, raises on failure) and get_optional_user (lenient, returns None on failure) for extracting authenticated users from JWT session cookies.

# Module invariants:
#   - Both functions use the same JWT decoding and user lookup logic
#   - Session cookies contain JWT tokens with 'sub' claim as user UUID
#   - Authentication failures in get_current_user always return 401 status

class User:
    """User model object retrieved from database with id field matching JWT sub claim"""
    id: uuid.UUID                            # required, User unique identifier matching JWT sub claim

class AsyncSession:
    """SQLAlchemy async database session for executing queries"""
    pass

class HTTPException:
    """FastAPI HTTP exception with status code and detail message"""
    status_code: int                         # required, HTTP status code
    detail: str                              # required, Error detail message

async def get_current_user(
    db: sqlalchemy.ext.asyncio.AsyncSession,
    session: str | None = None,
) -> User:
    """
    Retrieves the authenticated user from the session cookie JWT. Raises HTTPException with 401 status on any failure (missing cookie, invalid JWT, user not found in database). Used as a strict authentication dependency.

    Preconditions:
      - session cookie must be present (not None)
      - session must be a valid JWT decodable by decode_jwt
      - JWT payload must contain 'sub' field with valid UUID string
      - User with decoded UUID must exist in database

    Postconditions:
      - Returns User object with id matching JWT 'sub' claim
      - User object is retrieved from database via select query

    Errors:
      - missing_session (HTTPException): session cookie is None
          status_code: 401
          detail: Not authenticated
      - invalid_session (HTTPException): decode_jwt raises any exception OR payload['sub'] is not valid UUID
          status_code: 401
          detail: Invalid session
      - user_not_found (HTTPException): database query returns no user with matching id
          status_code: 401
          detail: User not found

    Side effects: Executes database SELECT query against User table
    Idempotent: yes
    """
    ...

async def get_optional_user(
    db: sqlalchemy.ext.asyncio.AsyncSession,
    session: str | None = None,
) -> User | None:
    """
    Retrieves the authenticated user from the session cookie JWT if present and valid. Returns None on any failure instead of raising exceptions. Used for optional authentication scenarios where anonymous access is permitted.

    Postconditions:
      - Returns User object if session is valid and user exists
      - Returns None if session is missing, invalid, or user not found
      - Never raises exceptions

    Side effects: May execute database SELECT query against User table if session is present
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['User', 'AsyncSession', 'HTTPException', 'get_current_user', 'get_optional_user']
