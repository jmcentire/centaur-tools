# === Backend API Auth Dependencies Interface (contracts_contracts_backend_api_auth_dependencies_interface_interface) v1 ===
#  Dependencies: uuid, fastapi, sqlalchemy, sqlalchemy.ext.asyncio, backend.api.database, backend.api.models, backend.api.auth.router
# FastAPI dependency injection functions for authentication. Provides get_current_user (strict, raises HTTPException on failure) and get_optional_user (permissive, returns None on failure). Both extract and validate JWT session cookies, decode user_id from JWT payload, and query the database for the User record.

# Module invariants:
#   - get_current_user always returns a User or raises HTTPException (never returns None)
#   - get_optional_user always returns User or None (never raises exceptions)
#   - Both functions extract user_id from JWT 'sub' claim as UUID
#   - Database queries use User.id field for lookup
#   - Session token is expected as HTTP cookie named 'session'

class User:
    """SQLAlchemy User model from backend.api.models (external type)"""
    pass

class AsyncSession:
    """SQLAlchemy async database session (external type)"""
    pass

async def get_current_user(
    db: AsyncSession,
    session: str | None = None,
) -> User:
    """
    Strict authentication dependency that requires a valid session cookie. Decodes JWT from 'session' cookie, extracts user_id from 'sub' claim, queries database for User. Raises HTTPException (401) if session missing, invalid, or user not found. Used as FastAPI dependency via Depends().

    Preconditions:
      - session cookie must be present (not None)
      - session must be a valid JWT decodable by decode_jwt()
      - JWT payload must contain 'sub' field with valid UUID string
      - User with id matching JWT 'sub' must exist in database

    Postconditions:
      - Returns User object from database matching JWT user_id
      - User.id equals uuid.UUID(payload['sub'])

    Errors:
      - missing_session (HTTPException): session cookie is None
          status_code: 401
          detail: Not authenticated
      - invalid_session (HTTPException): decode_jwt() raises exception OR uuid.UUID() raises exception
          status_code: 401
          detail: Invalid session
      - user_not_found (HTTPException): Database query returns None (no user with matching id)
          status_code: 401
          detail: User not found

    Side effects: Reads from database (SELECT query on User table)
    Idempotent: yes
    """
    ...

async def get_optional_user(
    db: AsyncSession,
    session: str | None = None,
) -> User | None:
    """
    Permissive authentication dependency that allows anonymous access. Attempts to decode JWT from 'session' cookie and fetch User from database. Returns None on any failure (missing cookie, invalid JWT, invalid UUID, user not found). Never raises exceptions. Used as FastAPI dependency for endpoints that support optional authentication.

    Postconditions:
      - Returns User object if session is valid and user exists in database
      - Returns None if session is missing, invalid, or user not found
      - Never raises exceptions

    Side effects: Reads from database (SELECT query on User table) if session is present
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['User', 'AsyncSession', 'get_current_user', 'HTTPException', 'get_optional_user']
