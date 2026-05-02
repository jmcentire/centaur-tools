from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import ForumThread, Tool, User

router = APIRouter(tags=["feed"])

ATOM_NS = "http://www.w3.org/2005/Atom"


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _text_el(parent: Element, tag: str, text: str) -> Element:
    el = SubElement(parent, tag)
    el.text = text
    return el


def _build_feed(tools: list, threads: list) -> str:
    feed = Element("feed", xmlns=ATOM_NS)

    _text_el(feed, "title", "centaur.tools")
    _text_el(feed, "subtitle", "Community-governed registry for AI tools")
    _text_el(feed, "id", "urn:centaur:feed")

    link = SubElement(feed, "link", href="https://centaur.tools/api/feed/atom.xml", rel="self")
    link = SubElement(feed, "link", href="https://centaur.tools", rel="alternate")

    author = SubElement(feed, "author")
    _text_el(author, "name", "centaur.tools")

    # Merge and sort entries by date descending
    entries = []
    for tool in tools:
        entries.append({
            "id": f"urn:centaur:tool:{tool.id}",
            "title": f"New tool: {tool.name}",
            "link": f"https://centaur.tools/tools/{tool.slug}",
            "updated": tool.created_at,
            "summary": tool.description[:500] if tool.description else "",
            "author": tool.author.display_name or tool.author.username if tool.author else "unknown",
            "category": "tool",
        })
    for thread in threads:
        entries.append({
            "id": f"urn:centaur:thread:{thread.id}",
            "title": f"Forum: {thread.title}",
            "link": f"https://centaur.tools/forum/thread/{thread.id}",
            "updated": thread.created_at,
            "summary": thread.body[:500] if thread.body else "",
            "author": thread.author.display_name or thread.author.username if thread.author else "unknown",
            "category": "forum",
        })

    entries.sort(key=lambda e: e["updated"], reverse=True)
    entries = entries[:50]

    # Feed updated = most recent entry
    if entries:
        _text_el(feed, "updated", _iso(entries[0]["updated"]))
    else:
        _text_el(feed, "updated", _iso(datetime.now(timezone.utc)))

    for e in entries:
        entry = SubElement(feed, "entry")
        _text_el(entry, "id", e["id"])
        _text_el(entry, "title", e["title"])
        SubElement(entry, "link", href=e["link"], rel="alternate")
        _text_el(entry, "updated", _iso(e["updated"]))
        _text_el(entry, "summary", e["summary"])
        SubElement(entry, "category", term=e["category"])
        author_el = SubElement(entry, "author")
        _text_el(author_el, "name", e["author"])

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(feed, encoding="unicode")


@router.get("/api/feed/atom.xml")
async def atom_feed(db: AsyncSession = Depends(get_db)):
    tools_result = await db.execute(
        select(Tool)
        .where(Tool.is_active == True)
        .options(selectinload(Tool.author))
        .order_by(Tool.created_at.desc())
        .limit(50)
    )
    tools = tools_result.scalars().all()

    threads_result = await db.execute(
        select(ForumThread)
        .options(selectinload(ForumThread.author))
        .order_by(ForumThread.created_at.desc())
        .limit(50)
    )
    threads = threads_result.scalars().all()

    xml = _build_feed(tools, threads)
    return Response(content=xml, media_type="application/atom+xml")
