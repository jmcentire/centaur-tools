# === Forum Router API (backend_api_forum_router) v1 ===
#  Dependencies: fastapi, pydantic, sqlalchemy, sqlalchemy.ext.asyncio, sqlalchemy.orm, datetime, uuid, backend.auth.dependencies, backend.database, backend.models
# FastAPI router module providing REST endpoints for forum functionality including categories, threads, replies, and voting. Handles CRUD operations for forum content with authentication, pagination, and vote tracking.

# Module invariants:
#   - Thread reply_count must be >= 0
#   - Soft-deleted replies have body='[deleted]'
#   - Thread.last_activity_at updated when reply added
#   - Pagination: page >= 1, per_page between 1 and 100
#   - Thread IDs and reply IDs are UUIDs
#   - All datetime fields stored as UTC and returned as ISO format strings
#   - Threads ordered by is_pinned (desc), then last_activity_at (desc) in listings
#   - Replies sorted by created_at (asc) in thread details
#   - Vote operations are idempotent

class CreateThread:
    """Request payload for creating a new forum thread"""
    title: str                               # required, Thread title
    body: str                                # required, Thread body content
    category_slug: str                       # required, Slug identifier of the target category

class CreateReply:
    """Request payload for creating a reply to a thread"""
    body: str                                # required, Reply body content

class UpdateReply:
    """Request payload for updating an existing reply"""
    body: str                                # required, Updated reply body content

class CategoryListResponse:
    """Response containing list of forum categories"""
    categories: list[CategoryItem]           # required, List of category objects

class CategoryItem:
    """Individual category in list response"""
    slug: str                                # required
    name: str                                # required
    description: str                         # required
    thread_count: int                        # required

class ThreadListResponse:
    """Paginated response containing threads for a category"""
    category: CategoryInfo                   # required
    threads: list[ThreadItem]                # required
    total: int                               # required
    page: int                                # required
    per_page: int                            # required

class ThreadDetailResponse:
    """Full thread details including replies"""
    id: str                                  # required
    title: str                               # required
    body: str                                # required
    category: CategoryInfo                   # required
    author: AuthorInfo                       # required
    is_pinned: bool                          # required
    is_locked: bool                          # required
    tool: ToolInfo | None                    # required
    replies: list[ReplyItem]                 # required
    created_at: str                          # required, ISO format timestamp

class CreateResponse:
    """Generic creation success response"""
    id: str                                  # required
    status: str                              # required

class VoteResponse:
    """Response from vote/unvote operations"""
    status: str                              # required
    vote_count: int                          # required

class StatusResponse:
    """Simple status response"""
    status: str                              # required

async def list_categories(
    db: AsyncSession,
) -> dict:
    """
    Retrieves all forum categories ordered by sort_order with thread counts

    Postconditions:
      - Returns dictionary with 'categories' key containing list of category objects
      - Each category includes slug, name, description, and thread_count
      - Categories ordered by sort_order ascending

    Side effects: Reads from ForumCategory and ForumThread tables
    Idempotent: no
    """
    ...

async def list_threads(
    slug: str,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession,
    user: User | None = None,
) -> dict:
    """
    Lists paginated threads for a specific category with vote counts and user vote status

    Preconditions:
      - page >= 1
      - per_page >= 1 and per_page <= 100

    Postconditions:
      - Returns category info, paginated threads list, total count, page, per_page
      - Threads ordered by is_pinned desc, last_activity_at desc
      - Vote counts aggregated for all threads
      - User vote status included if user authenticated

    Errors:
      - category_not_found (HTTPException): Category with given slug does not exist
          status_code: 404
          detail: Category not found

    Side effects: Reads from ForumCategory, ForumThread, ThreadVote, User tables
    Idempotent: no
    """
    ...

async def get_thread(
    thread_id: str,
    db: AsyncSession,
) -> dict:
    """
    Retrieves full thread details including all replies, author info, and linked tool data if present

    Preconditions:
      - thread_id must be valid UUID string

    Postconditions:
      - Returns complete thread with author, category, replies, and optional tool data
      - Replies sorted by created_at ascending
      - Tool data included only if thread.tool exists and is_active=True
      - All datetime fields returned as ISO format strings

    Errors:
      - invalid_uuid (ValueError): thread_id is not a valid UUID string
      - thread_not_found (HTTPException): Thread with given ID does not exist
          status_code: 404
          detail: Thread not found

    Side effects: Reads from ForumThread, ForumReply, ForumCategory, User, Tool, ToolVote tables
    Idempotent: no
    """
    ...

async def create_thread(
    body: CreateThread,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Creates a new forum thread in the specified category

    Preconditions:
      - User must be authenticated
      - Category with body.category_slug must exist

    Postconditions:
      - New ForumThread record created in database
      - Returns id (UUID string) and status='created'
      - Thread.author_id set to user.id
      - Thread.category_id set to matching category

    Errors:
      - category_not_found (HTTPException): Category with body.category_slug does not exist
          status_code: 404
          detail: Category not found
      - unauthorized (HTTPException): User is not authenticated (dependency fails)
          status_code: 401

    Side effects: Writes to ForumThread table, Reads from ForumCategory table
    Idempotent: no
    """
    ...

async def create_reply(
    thread_id: str,
    body: CreateReply,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Creates a reply to an existing thread and updates thread metadata

    Preconditions:
      - User must be authenticated
      - thread_id must be valid UUID string
      - Thread must exist
      - Thread must not be locked (is_locked=False)

    Postconditions:
      - New ForumReply record created
      - Thread.reply_count incremented by 1
      - Thread.last_activity_at updated to current UTC time
      - Returns reply id (UUID string) and status='created'

    Errors:
      - invalid_uuid (ValueError): thread_id is not a valid UUID string
      - thread_not_found (HTTPException): Thread with given ID does not exist
          status_code: 404
          detail: Thread not found
      - thread_locked (HTTPException): Thread.is_locked is True
          status_code: 403
          detail: Thread is locked
      - unauthorized (HTTPException): User is not authenticated
          status_code: 401

    Side effects: Writes to ForumReply and ForumThread tables
    Idempotent: no
    """
    ...

async def edit_reply(
    reply_id: str,
    body: UpdateReply,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Updates the body of an existing reply (author-only)

    Preconditions:
      - User must be authenticated
      - reply_id must be valid UUID string
      - Reply must exist
      - User must be the reply author (reply.author_id == user.id)

    Postconditions:
      - Reply.body updated to body.body
      - Reply.updated_at set to current UTC time
      - Returns status='updated'

    Errors:
      - invalid_uuid (ValueError): reply_id is not a valid UUID string
      - reply_not_found (HTTPException): Reply with given ID does not exist
          status_code: 404
          detail: Reply not found
      - forbidden (HTTPException): User is not the reply author
          status_code: 403
          detail: Not the author
      - unauthorized (HTTPException): User is not authenticated
          status_code: 401

    Side effects: Writes to ForumReply table
    Idempotent: no
    """
    ...

async def delete_reply(
    reply_id: str,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Soft-deletes a reply by setting body to '[deleted]' and decrements thread reply count

    Preconditions:
      - User must be authenticated
      - reply_id must be valid UUID string
      - Reply must exist
      - User must be the reply author

    Postconditions:
      - Reply.body set to '[deleted]'
      - Reply.updated_at set to current UTC time
      - Thread.reply_count decremented by 1 (minimum 0)
      - Returns status='deleted'

    Errors:
      - invalid_uuid (ValueError): reply_id is not a valid UUID string
      - reply_not_found (HTTPException): Reply with given ID does not exist
          status_code: 404
          detail: Reply not found
      - forbidden (HTTPException): User is not the reply author
          status_code: 403
          detail: Not the author
      - unauthorized (HTTPException): User is not authenticated
          status_code: 401

    Side effects: Writes to ForumReply and ForumThread tables
    Idempotent: no
    """
    ...

async def vote_thread(
    thread_id: str,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Adds user vote to a thread (idempotent - returns existing vote count if already voted)

    Preconditions:
      - User must be authenticated
      - thread_id must be valid UUID string
      - Thread must exist

    Postconditions:
      - If not already voted: creates new ThreadVote record
      - Returns status ('voted' or 'already_voted') and current vote_count
      - Vote count reflects total votes for thread

    Errors:
      - invalid_uuid (ValueError): thread_id is not a valid UUID string
      - thread_not_found (HTTPException): Thread with given ID does not exist
          status_code: 404
          detail: Thread not found
      - unauthorized (HTTPException): User is not authenticated
          status_code: 401

    Side effects: May write to ThreadVote table, Reads from ForumThread and ThreadVote tables
    Idempotent: yes
    """
    ...

async def unvote_thread(
    thread_id: str,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Removes user vote from a thread (idempotent - returns current count if not voted)

    Preconditions:
      - User must be authenticated
      - thread_id must be valid UUID string

    Postconditions:
      - If vote exists: deletes ThreadVote record
      - Returns status ('removed' or 'not_voted') and current vote_count
      - Vote count reflects total votes for thread after removal

    Errors:
      - invalid_uuid (ValueError): thread_id is not a valid UUID string
      - unauthorized (HTTPException): User is not authenticated
          status_code: 401

    Side effects: May delete from ThreadVote table, Reads from ThreadVote table
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['CreateThread', 'CreateReply', 'UpdateReply', 'CategoryListResponse', 'CategoryItem', 'ThreadListResponse', 'ThreadDetailResponse', 'CreateResponse', 'VoteResponse', 'StatusResponse', 'list_categories', 'list_threads', 'HTTPException', 'get_thread', 'create_thread', 'create_reply', 'edit_reply', 'delete_reply', 'vote_thread', 'unvote_thread']
