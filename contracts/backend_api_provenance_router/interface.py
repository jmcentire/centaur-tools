# === Prior Art Provenance Router (backend_api_provenance_router) v1 ===
#  Dependencies: datetime, fastapi, pydantic, sqlalchemy, sqlalchemy.ext.asyncio, sqlalchemy.orm, uuid, backend.auth.dependencies, backend.config, backend.database, backend.models
# FastAPI router implementing community-driven prior art nomination and voting for AI tools. Manages nominations claiming tools as prior art for platform features, with vote-based confirmation thresholds and author notifications.

# Module invariants:
#   - Router prefix is '/api/prior-art'
#   - Router tag is 'provenance'
#   - Nomination confirmation requires vote_count >= settings.prior_art_vote_threshold
#   - Users cannot vote multiple times on the same nomination
#   - Confirmed nominations cannot receive additional votes (early return with 'already_confirmed' status)
#   - Tool authors receive notifications when their tool is nominated (unless they are the nominator)
#   - Tool authors receive notifications when nomination is confirmed
#   - Nomination IDs are UUIDs stored/returned as strings
#   - All datetime values returned as ISO format strings
#   - confirmed_at is set to UTC time when nomination reaches threshold

class NominationRequest:
    """Request body for nominating a tool as prior art"""
    tool_slug: str                           # required, Unique slug identifier for the tool
    platform: str                            # required, Platform name that implemented the feature
    platform_feature: str                    # required, Specific feature that the tool predates
    evidence: str                            # required, Evidence supporting the prior art claim

class PriorArtListResponse:
    """Response containing list of confirmed prior art nominations"""
    prior_art: list[PriorArtItem]            # required, Array of confirmed prior art nominations

class PriorArtItem:
    """Individual prior art nomination item"""
    id: str                                  # required, UUID of the nomination as string
    tool: ToolInfo                           # required, Tool information
    platform: str                            # required
    platform_feature: str                    # required
    evidence: str                            # required
    nominated_by: str                        # required, Username of nominator
    confirmed_at: str | None                 # required, ISO format timestamp or None
    vote_count: int                          # required

class ToolInfo:
    """Embedded tool information"""
    slug: str                                # required
    name: str                                # required

class PendingListResponse:
    """Response containing list of pending nominations"""
    pending: list[PendingItem]               # required, Array of pending nominations

class PendingItem:
    """Individual pending nomination item"""
    id: str                                  # required
    tool: ToolInfo                           # required
    platform: str                            # required
    platform_feature: str                    # required
    evidence: str                            # required
    nominated_by: str                        # required
    vote_count: int                          # required
    threshold: int                           # required, Vote threshold from settings
    created_at: str                          # required, ISO format timestamp

class NominationResponse:
    """Response after creating a nomination"""
    id: str                                  # required, UUID of created nomination
    status: str                              # required, Always 'nominated'

class VoteResponse:
    """Response after voting on a nomination"""
    status: str                              # required, 'voted', 'already_confirmed', or 'already_voted'
    vote_count: int = None                   # optional, Present when status is 'voted'
    confirmed: bool = None                   # optional, Present when status is 'voted'

async def list_prior_art(
    db: AsyncSession,
) -> PriorArtListResponse:
    """
    Retrieves all confirmed prior art nominations with tool, nominator, and vote information, ordered by confirmation date descending

    Preconditions:
      - Database session is active and connected

    Postconditions:
      - Returns dictionary with 'prior_art' key containing list of confirmed nominations
      - Each nomination includes tool (slug, name), platform, platform_feature, evidence, nominator username, confirmed_at ISO timestamp, and vote count
      - Results ordered by confirmed_at descending

    Side effects: Executes SELECT query on PriorArtNomination table with WHERE confirmed == True, Eager loads related tool and nominator entities via selectinload
    Idempotent: yes
    """
    ...

async def list_pending(
    db: AsyncSession,
) -> PendingListResponse:
    """
    Retrieves all unconfirmed prior art nominations with tool, nominator, votes, and threshold information, ordered by creation date descending

    Preconditions:
      - Database session is active and connected
      - settings.prior_art_vote_threshold is configured

    Postconditions:
      - Returns dictionary with 'pending' key containing list of unconfirmed nominations
      - Each nomination includes tool, platform, platform_feature, evidence, nominator username, vote count, threshold from settings, and created_at ISO timestamp
      - Results ordered by created_at descending

    Side effects: Executes SELECT query on PriorArtNomination table with WHERE confirmed == False, Eager loads related tool, nominator, and votes entities via selectinload
    Idempotent: yes
    """
    ...

async def nominate(
    body: NominationRequest,
    user: User,
    db: AsyncSession,
) -> NominationResponse:
    """
    Creates a new prior art nomination for a tool and optionally notifies the tool author if they are not the nominator

    Preconditions:
      - User is authenticated
      - Database session is active and connected
      - Tool with given slug exists and is_active == True

    Postconditions:
      - PriorArtNomination record created in database with confirmed=False (default)
      - If tool.author_id != user.id, Notification created for tool author with type='prior_art_nomination'
      - Returns dictionary with nomination UUID as string and status='nominated'
      - All changes committed to database

    Errors:
      - tool_not_found (HTTPException): Tool with given slug not found or is_active == False
          status_code: 404
          detail: Tool not found

    Side effects: Inserts PriorArtNomination record, Conditionally inserts Notification record if author is not nominator, Commits database transaction
    Idempotent: no
    """
    ...

async def vote_on_nomination(
    nomination_id: str,
    user: User,
    db: AsyncSession,
) -> VoteResponse:
    """
    Casts a vote for a prior art nomination, checks vote threshold, confirms nomination if threshold reached, and notifies tool author on confirmation

    Preconditions:
      - User is authenticated
      - Database session is active and connected
      - nomination_id is a valid UUID string
      - Nomination exists in database
      - settings.prior_art_vote_threshold is configured

    Postconditions:
      - If nomination already confirmed: returns {'status': 'already_confirmed'} without side effects
      - If user already voted: returns {'status': 'already_voted'} without side effects
      - Otherwise: PriorArtVote record created, returns {'status': 'voted', 'vote_count': int, 'confirmed': bool}
      - If vote_count >= threshold after vote: nomination.confirmed set to True, nomination.confirmed_at set to current UTC time, Notification created for tool author
      - All changes committed to database

    Errors:
      - invalid_uuid (ValueError): nomination_id cannot be parsed as valid UUID
      - nomination_not_found (HTTPException): No nomination exists with given UUID
          status_code: 404
          detail: Nomination not found

    Side effects: Converts nomination_id string to UUID, Reads nomination and related votes/tool from database, Checks for existing vote by user, Inserts PriorArtVote record (on new vote), Flushes to get vote reflected in count query, Executes COUNT query on PriorArtVote, Conditionally updates nomination confirmed/confirmed_at fields and inserts Notification (if threshold reached), Commits database transaction
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['NominationRequest', 'PriorArtListResponse', 'PriorArtItem', 'ToolInfo', 'PendingListResponse', 'PendingItem', 'NominationResponse', 'VoteResponse', 'list_prior_art', 'list_pending', 'nominate', 'HTTPException', 'vote_on_nomination']
