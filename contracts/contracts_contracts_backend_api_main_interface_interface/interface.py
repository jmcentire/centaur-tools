# === Backend API Main Interface (contracts_contracts_backend_api_main_interface_interface) v1 ===
#  Dependencies: fastapi, backend.api.auth.router, backend.api.feed.router, backend.api.forum.router, backend.api.notifications.router, backend.api.provenance.router, backend.api.registry.router, backend.api.search.router, backend.api.users.router, backend.api.voting.router, backend.api.auth.dependencies
# FastAPI application entry point for centaur.tools API - a community-governed registry for AI tools with provenance tracking. Assembles routers for auth, feed, forum, notifications, provenance, registry, search, users, and voting subsystems, configures cookie-based authentication dependency override, and exposes a health check endpoint.

# Module invariants:
#   - FastAPI app instance initialized with title='centaur.tools API', version='1.0.0'
#   - Dependency override maps placeholder_get_current_user to real_get_current_user for cookie-based auth
#   - Nine routers included in fixed order: auth, feed, users, registry, search, voting, provenance, forum, notifications

async def health() -> dict[str, str]:
    """
    Health check endpoint that returns a static success response indicating the API is operational.

    Postconditions:
      - Returns dictionary with 'status' key set to 'ok'
      - HTTP 200 status code

    Side effects: none
    Idempotent: yes
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['health']
