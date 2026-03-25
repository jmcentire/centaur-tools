from fastapi import FastAPI

from .auth.router import router as auth_router
from .forum.router import router as forum_router
from .notifications.router import router as notifications_router
from .provenance.router import router as provenance_router
from .registry.router import router as registry_router
from .search.router import router as search_router
from .users.router import router as users_router
from .voting.router import router as voting_router

app = FastAPI(
    title="centaur.tools API",
    description="Community-governed registry for AI tools with provenance tracking",
    version="1.0.0",
)

# Override auth dependency to use cookie-based auth
from .auth.dependencies import get_current_user as real_get_current_user
from .auth.router import get_current_user as placeholder_get_current_user

app.dependency_overrides[placeholder_get_current_user] = real_get_current_user

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(registry_router)
app.include_router(search_router)
app.include_router(voting_router)
app.include_router(provenance_router)
app.include_router(forum_router)
app.include_router(notifications_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
