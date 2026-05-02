# === Tool Registry API Router (backend_api_registry_router) v1 ===
#  Dependencies: re, uuid, fastapi, pydantic, sqlalchemy, sqlalchemy.ext.asyncio, sqlalchemy.orm, httpx, logging, ..auth.dependencies, ..database, ..models, ..proximity.service
# FastAPI router for the centaur.tools registry. Handles tool submission, retrieval, updates, and deactivation with MIT license enforcement, GitHub repo verification, fork tracking, proximity linking, voting, and forum thread creation.

# Module invariants:
#   - MIT license is the only acceptable license for tool submissions
#   - Tool slugs are unique (collision handled with 6-char uuid suffix)
#   - Tags are limited to 20 per tool, lowercased and stripped
#   - Only active tools (is_active == True) are visible in list/get endpoints
#   - Only tool authors can update or deactivate their tools
#   - Forum threads auto-created in 'show-and-tell' category on tool submission
#   - Proximity scan is best-effort (errors logged but don't fail operations)

class ToolSubmission:
    """Pydantic model for submitting a new tool to the registry. Enforces MIT license via validator."""
    name: str                                # required, Tool name
    description: str                         # required, Tool description
    problem_statement: str                   # required, Problem the tool solves
    repo_url: str                            # required, Repository URL (must be owned by submitter)
    license: str = MIT                       # optional, custom(must_be_mit), License (must be MIT, validated)
    language: str | None = None              # optional, Programming language
    tags: list[str] = []                     # optional, List of tags (max 20 used)
    fork_parent_slug: str | None = None      # optional, Slug of parent tool if this is a fork

class ToolUpdate:
    """Pydantic model for updating an existing tool. All fields optional."""
    description: str | None = None           # optional, Updated description
    problem_statement: str | None = None     # optional, Updated problem statement
    repo_url: str | None = None              # optional, Updated repository URL
    language: str | None = None              # optional, Updated language
    tags: list[str] | None = None            # optional, Updated tags (replaces all existing)

def slugify(
    name: str,
) -> str:
    """
    Converts a tool name to a URL-safe slug by lowercasing, replacing non-alphanumeric characters with hyphens, and stripping leading/trailing hyphens.

    Postconditions:
      - Returns lowercase string with only alphanumerics and hyphens
      - No leading or trailing hyphens

    Side effects: none
    Idempotent: no
    """
    ...

def must_be_mit(
    cls: type,
    v: str,
) -> str:
    """
    Pydantic field validator for ToolSubmission.license. Enforces MIT license requirement by raising ValueError if license is not 'MIT' (case-insensitive).

    Postconditions:
      - Returns 'MIT' if validation passes

    Errors:
      - non_mit_license (ValueError): v.upper() != 'MIT'
          message: centaur.tools requires MIT license. The social contract is: everything forkable, stealable, buildable-upon. Cite your parents. MIT is the only license that guarantees this.

    Side effects: none
    Idempotent: no
    """
    ...

async def list_tools(
    tag: str | None = None,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession,
    user: User | None = None,
) -> dict:
    """
    Async FastAPI endpoint to list active tools with pagination, optional tag filtering, vote counts, and user vote status. Returns paginated tool list with author info.

    Preconditions:
      - page >= 1
      - 1 <= per_page <= 100

    Postconditions:
      - Returns dict with 'tools' (list), 'total' (int), 'page' (int), 'per_page' (int)
      - Each tool includes slug, name, description, problem_statement, language, tags, author, vote_count, user_voted, created_at
      - Only active tools (is_active == True) returned
      - Tools ordered by created_at descending

    Side effects: Reads from Tool, ToolTag, ToolVote tables
    Idempotent: no
    """
    ...

async def get_tool(
    slug: str,
    db: AsyncSession,
    user: User | None = None,
) -> dict:
    """
    Async FastAPI endpoint to retrieve a single tool by slug with full details: vote count, user vote status, proximity neighbors, fork lineage (parents/children), and discussion thread with replies.

    Postconditions:
      - Returns dict with tool details: slug, name, description, problem_statement, repo_url, license, language, tags, author (username, display_name, avatar_url), vote_count, user_voted, neighbors (top 10 by similarity), forks (parents, children), discussion (thread_id, reply_count, replies), created_at, updated_at
      - Neighbors sorted by similarity descending, limited to 10
      - Discussion replies sorted by created_at ascending

    Errors:
      - tool_not_found (HTTPException): Tool with slug not found or is_active == False
          status_code: 404
          detail: Tool not found

    Side effects: Reads from Tool, ToolTag, ToolVote, ProximityLink, ForkLink, ForumThread, ForumReply tables
    Idempotent: no
    """
    ...

async def verify_repo_ownership(
    repo_url: str,
    username: str,
) -> bool:
    """
    Async helper function to verify GitHub repo ownership or collaborator access. Checks if repo owner matches username or if user is a collaborator via GitHub API. Returns True for non-GitHub repos.

    Postconditions:
      - Returns True if non-GitHub URL
      - Returns True if repo owner matches username (case-insensitive)
      - Returns True if user is collaborator on organization repo (GitHub API check)
      - Returns False otherwise or on API error

    Side effects: Makes HTTP GET requests to GitHub API
    Idempotent: no
    """
    ...

async def submit_tool(
    body: ToolSubmission,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Async FastAPI POST endpoint to submit a new tool. Verifies GitHub repo ownership, creates tool with unique slug, adds tags (max 20), creates fork link if parent specified, sends notification to parent author, auto-creates forum thread in 'show-and-tell' category, and triggers proximity scan.

    Preconditions:
      - User must be authenticated
      - body.license must be 'MIT' (validated by Pydantic)

    Postconditions:
      - Returns dict with 'slug' (str) and 'status' ('created')
      - Tool created in database with unique slug
      - Tags created (up to 20, lowercased, stripped)
      - ForkLink created if fork_parent_slug exists and is active
      - Notification sent to parent author if fork
      - ForumThread created in 'show-and-tell' category if exists
      - Proximity scan triggered (best-effort, errors logged)

    Errors:
      - repo_ownership_failed (HTTPException): verify_repo_ownership returns False
          status_code: 403
          detail: The repository {body.repo_url} does not appear to belong to your GitHub account ({user.username}). You can only register tools from repositories you own or have collaborator access to.

    Side effects: Writes to Tool, ToolTag, ForkLink, Notification, ForumThread tables, Calls verify_repo_ownership, Calls scan_proximity
    Idempotent: no
    """
    ...

async def update_tool(
    slug: str,
    body: ToolUpdate,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Async FastAPI PATCH endpoint to update an existing tool. Only tool author can update. Updates fields if provided, replaces all tags if tags provided, triggers proximity re-scan if problem_statement changed.

    Preconditions:
      - User must be authenticated
      - Tool must exist and be active
      - User must be tool author

    Postconditions:
      - Returns dict with 'slug' (str) and 'status' ('updated')
      - Tool fields updated if provided in body
      - All tags replaced if body.tags provided (max 20, lowercased, stripped)
      - Proximity re-scan triggered if problem_statement updated (best-effort, errors logged)

    Errors:
      - tool_not_found (HTTPException): Tool with slug not found or is_active == False
          status_code: 404
          detail: Tool not found
      - not_owner (HTTPException): tool.author_id != user.id
          status_code: 403
          detail: Not the owner

    Side effects: Writes to Tool, ToolTag tables, Calls scan_proximity if problem_statement changed
    Idempotent: yes
    """
    ...

async def deactivate_tool(
    slug: str,
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Async FastAPI DELETE endpoint to deactivate a tool (soft delete). Only tool author can deactivate. Sets is_active to False.

    Preconditions:
      - User must be authenticated
      - Tool must exist
      - User must be tool author

    Postconditions:
      - Returns dict with 'status' ('deactivated')
      - Tool.is_active set to False

    Errors:
      - tool_not_found (HTTPException): Tool with slug not found
          status_code: 404
          detail: Tool not found
      - not_owner (HTTPException): tool.author_id != user.id
          status_code: 403
          detail: Not the owner

    Side effects: Writes to Tool table
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['ToolSubmission', 'ToolUpdate', 'slugify', 'must_be_mit', 'list_tools', 'get_tool', 'HTTPException', 'verify_repo_ownership', 'submit_tool', 'update_tool', 'deactivate_tool']
