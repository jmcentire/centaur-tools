# === Backend API Main Interface (contracts_backend_api_main_interface) v1 ===
#  Dependencies: fastapi, backend.api.auth.router, backend.api.feed.router, backend.api.forum.router, backend.api.notifications.router, backend.api.provenance.router, backend.api.registry.router, backend.api.search.router, backend.api.users.router, backend.api.voting.router, backend.api.auth.dependencies
# FastAPI application entry point for centaur.tools API - a community-governed registry for AI tools with provenance tracking. Configures and assembles the application by registering route modules (auth, feed, forum, notifications, provenance, registry, search, users, voting) and overriding authentication dependency to use cookie-based auth.

# Module invariants:
#   - FastAPI app title: 'centaur.tools API'
#   - FastAPI app version: '1.0.0'
#   - Auth dependency override: placeholder_get_current_user -> real_get_current_user
#   - Health endpoint path: '/api/health'
#   - Nine routers registered: auth, feed, users, registry, search, voting, provenance, forum, notifications

class HealthResponse:
    """Response structure for health check endpoint"""
    status: str                              # required, Status indicator, always 'ok'

async def health() -> dict[str, str]:
    """
    Health check endpoint that returns the operational status of the API. Always returns a successful status indicator.

    Postconditions:
      - Returns dictionary with 'status' key set to 'ok'

    Side effects: none
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['HealthResponse', 'health']
