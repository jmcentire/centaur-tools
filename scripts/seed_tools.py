#!/usr/bin/env python3
"""Seed webprobe, advocate, and transmogrifier into centaur.tools.

Connects directly to PostgreSQL (no running API needed).
Idempotent: skips tools whose slug already exists.

Usage:
    # Uses default local database (postgresql+asyncpg://postgres:postgres@localhost:5432/centaur)
    python scripts/seed_tools.py

    # Override with env var
    CENTAUR_DATABASE_URL=postgresql+asyncpg://... python scripts/seed_tools.py
"""

import asyncio
import os
import re
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Adjust path so we can import the backend models
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from api.models import Tool, ToolTag, User  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "CENTAUR_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/centaur",
)

# GitHub ID for jmcentire (public, from api.github.com/users/jmcentire)
AUTHOR_GITHUB_ID = 519490
AUTHOR_USERNAME = "jmcentire"
AUTHOR_DISPLAY_NAME = "Jeremy McEntire"

TOOLS = [
    {
        "name": "Webprobe",
        "slug": "webprobe",
        "description": "Generic site state-graph auditor with LLM-driven exploration",
        "problem_statement": (
            "Websites need comprehensive automated testing that covers security headers, "
            "accessibility, visual defects, and behavioral issues -- beyond what unit tests "
            "or simple crawlers catch."
        ),
        "repo_url": "https://github.com/jmcentire/webprobe",
        "license": "MIT",
        "language": "Python",
        "tags": [
            "web-testing",
            "security",
            "accessibility",
            "browser-automation",
            "llm",
            "playwright",
        ],
    },
    {
        "name": "Advocate",
        "slug": "advocate",
        "description": "Six-persona adversarial review engine",
        "problem_statement": (
            "Code review is bottlenecked by individual perspective. A security engineer, "
            "UX designer, and on-call responder each see different issues. No single reviewer "
            "covers all angles."
        ),
        "repo_url": "https://github.com/jmcentire/advocate",
        "license": "MIT",
        "language": "Python",
        "tags": ["code-review", "adversarial", "security", "design", "llm"],
    },
    {
        "name": "Transmogrifier",
        "slug": "transmogrifier",
        "description": "Register-aware prompt translation for optimal LLM output",
        "problem_statement": (
            "LLM output quality varies dramatically by linguistic register "
            "(casual vs technical vs academic). The same question phrased differently "
            "can cause 18-56 percentage point accuracy swings."
        ),
        "repo_url": "https://github.com/jmcentire/transmogrifier",
        "license": "MIT",
        "language": "Python",
        "tags": ["llm", "prompt-engineering", "nlp", "middleware"],
    },
]


def slugify(name: str) -> str:
    """Match the slugify logic in registry/router.py."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def ensure_author(session: AsyncSession) -> uuid.UUID:
    """Upsert the jmcentire user, return their id."""
    result = await session.execute(
        select(User).where(User.github_id == AUTHOR_GITHUB_ID)
    )
    user = result.scalar_one_or_none()

    if user:
        print(f"  author '{user.username}' already exists (id={user.id})")
        return user.id

    user = User(
        github_id=AUTHOR_GITHUB_ID,
        username=AUTHOR_USERNAME,
        display_name=AUTHOR_DISPLAY_NAME,
    )
    session.add(user)
    await session.flush()
    print(f"  created author '{AUTHOR_USERNAME}' (id={user.id})")
    return user.id


async def seed_tool(session: AsyncSession, author_id: uuid.UUID, spec: dict) -> None:
    """Insert a single tool if its slug doesn't already exist."""
    slug = spec["slug"]

    existing = await session.execute(select(Tool).where(Tool.slug == slug))
    if existing.scalar_one_or_none():
        print(f"  SKIP {slug} (already exists)")
        return

    tool = Tool(
        slug=slug,
        name=spec["name"],
        description=spec["description"],
        problem_statement=spec["problem_statement"],
        repo_url=spec["repo_url"],
        license=spec["license"],
        language=spec["language"],
        author_id=author_id,
    )
    session.add(tool)
    await session.flush()

    for tag_name in spec["tags"]:
        session.add(ToolTag(tool_id=tool.id, tag=tag_name.lower().strip()))

    print(f"  ADD  {slug} ({len(spec['tags'])} tags)")


async def main() -> None:
    print(f"Connecting to: {DATABASE_URL.split('@')[-1]}")  # hide credentials
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            # Quick connectivity check
            await session.execute(text("SELECT 1"))
            print("Connected.\n")

            author_id = await ensure_author(session)
            print()

            for spec in TOOLS:
                await seed_tool(session, author_id, spec)

        # commit happens automatically when the `begin()` block exits cleanly

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
