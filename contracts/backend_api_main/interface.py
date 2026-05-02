# === Backend API Main Application (backend_api_main) v1 ===
#  Dependencies: fastapi, backend.api.auth.router, backend.api.feed.router, backend.api.forum.router, backend.api.notifications.router, backend.api.provenance.router, backend.api.registry.router, backend.api.search.router, backend.api.users.router, backend.api.voting.router, backend.api.auth.dependencies
# FastAPI application entry point for centaur.tools API. Orchestrates router composition for auth, feed, forum, notifications, provenance, registry, search, users, and voting modules. Configures global dependency overrides for cookie-based authentication. Provides health check endpoint.

# Module invariants:
#   - FastAPI app instance is configured with title='centaur.tools API'
#   - FastAPI app version is '1.0.0'
#   - dependency_overrides maps placeholder_get_current_user to real_get_current_user for cookie-based auth
#   - Nine routers are registered: auth, feed, users, registry, search, voting, provenance, forum, notifications (in that order)

class HealthResponse:
    """Response type for health endpoint"""
    status: str                              # required, Health status indicator, always 'ok'

async def health() -> dict[str, str]:
    """
    Health check endpoint that returns a static success status. Always returns {"status": "ok"} with no validation or actual system health checks.

    Postconditions:
      - Returns dictionary with single key 'status' having value 'ok'

    Side effects: none
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['HealthResponse', 'health']
