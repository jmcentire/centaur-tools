# === Backend API Voting Router Interface (contracts_backend_api_voting_router_interface) v1 ===
#  Dependencies: fastapi, sqlalchemy, sqlalchemy.ext.asyncio, backend.auth.dependencies, backend.database, backend.models
# FastAPI router providing voting endpoints for tools. Allows authenticated users to vote for tools (marking them as useful) and remove their votes. Implements vote uniqueness constraint per user-tool pair and returns current vote counts.

# Module invariants:
#   - Each user can only have one vote per tool (enforced by database query check)
#   - Only tools with is_active=True can be voted on
#   - Vote counts reflect actual database state after commit
#   - Router prefix is '/api/tools' with 'voting' tag

class VoteResponse:
    """Response structure for successful vote operations"""
    status: str                              # required, Vote operation status: 'voted', 'already_voted', 'removed', or 'not_voted'
    vote_count: int = None                   # optional, Total count of votes for the tool

class User:
    """User model from backend.models"""
    pass

class Tool:
    """Tool model from backend.models with slug and is_active fields"""
    pass

class ToolVote:
    """ToolVote model from backend.models representing user votes"""
    pass

class AsyncSession:
    """SQLAlchemy async database session"""
    pass

async def vote_useful(
    slug: str,
    user: User,
    db: AsyncSession,
) -> dict[str, str | int]:
    """
    Records a user's vote for a tool identified by slug. Returns existing vote status if already voted, otherwise creates new vote and returns updated count. Only active tools can be voted on.

    Preconditions:
      - user must be authenticated (enforced by get_current_user dependency)
      - db session must be valid and connected

    Postconditions:
      - If tool not found: HTTPException raised with 404 status
      - If user already voted: returns {'status': 'already_voted'} without modifying database
      - If vote successful: ToolVote record created, database committed, returns {'status': 'voted', 'vote_count': <int>}

    Errors:
      - tool_not_found (HTTPException): Tool with given slug not found OR tool.is_active != True
          status_code: 404
          detail: Tool not found

    Side effects: Reads from Tool table (filtered by slug and is_active=True), Reads from ToolVote table (filtered by tool_id and user_id), Writes new ToolVote record to database if vote doesn't exist, Commits database transaction on successful vote
    Idempotent: no
    """
    ...

async def remove_vote(
    slug: str,
    user: User,
    db: AsyncSession,
) -> dict[str, str | int]:
    """
    Removes a user's vote for a tool identified by slug. Returns not_voted status if vote doesn't exist, otherwise deletes vote and returns updated count. Only active tools can have votes removed.

    Preconditions:
      - user must be authenticated (enforced by get_current_user dependency)
      - db session must be valid and connected

    Postconditions:
      - If tool not found: HTTPException raised with 404 status
      - If vote doesn't exist: returns {'status': 'not_voted'} without modifying database
      - If removal successful: ToolVote record deleted, database committed, returns {'status': 'removed', 'vote_count': <int>}

    Errors:
      - tool_not_found (HTTPException): Tool with given slug not found OR tool.is_active != True
          status_code: 404
          detail: Tool not found

    Side effects: Reads from Tool table (filtered by slug and is_active=True), Reads from ToolVote table (filtered by tool_id and user_id), Deletes ToolVote record from database if vote exists, Commits database transaction on successful removal
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['VoteResponse', 'User', 'Tool', 'ToolVote', 'AsyncSession', 'vote_useful', 'HTTPException', 'remove_vote']
