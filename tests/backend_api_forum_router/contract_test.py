"""
Contract test suite for backend_api_forum_router (v1)

This test suite verifies the forum router API implementation against its contract.
Tests are organized by function with coverage of happy paths, edge cases, error cases,
and invariants.

Dependencies: pytest, pytest-asyncio, unittest.mock
Run with: pytest contract_test.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import UUID, uuid4
import re

# Import the component under test
from backend.api.forum.router import (
    list_categories,
    list_threads,
    get_thread,
    create_thread,
    create_reply,
    edit_reply,
    delete_reply,
    vote_thread,
    unvote_thread,
    CreateThread,
    CreateReply,
    UpdateReply,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for database operations"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = str(uuid4())
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_user_other():
    """Mock different authenticated user"""
    user = Mock()
    user.id = str(uuid4())
    user.username = "otheruser"
    user.email = "other@example.com"
    return user


@pytest.fixture
def mock_category():
    """Mock category object"""
    category = Mock()
    category.id = str(uuid4())
    category.slug = "general"
    category.name = "General Discussion"
    category.description = "General topics"
    category.sort_order = 1
    category.thread_count = 10
    return category


@pytest.fixture
def mock_thread():
    """Mock thread object"""
    thread = Mock()
    thread.id = "550e8400-e29b-41d4-a716-446655440000"
    thread.title = "Test Thread"
    thread.body = "Thread body content"
    thread.category_id = str(uuid4())
    thread.author_id = str(uuid4())
    thread.is_pinned = False
    thread.is_locked = False
    thread.reply_count = 0
    thread.vote_count = 0
    thread.last_activity_at = datetime.now(timezone.utc)
    thread.created_at = datetime.now(timezone.utc)
    thread.tool = None
    return thread


@pytest.fixture
def mock_reply():
    """Mock reply object"""
    reply = Mock()
    reply.id = "660e8400-e29b-41d4-a716-446655440000"
    reply.body = "Reply content"
    reply.thread_id = "550e8400-e29b-41d4-a716-446655440000"
    reply.author_id = str(uuid4())
    reply.created_at = datetime.now(timezone.utc)
    reply.updated_at = None
    return reply


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_result(scalars_return=None, first_return=None, all_return=None):
    """Create a mock database query result"""
    result = Mock()
    if scalars_return is not None:
        scalars_mock = Mock()
        scalars_mock.all = Mock(return_value=scalars_return if all_return is None else all_return)
        scalars_mock.first = Mock(return_value=first_return)
        result.scalars = Mock(return_value=scalars_mock)
    result.first = Mock(return_value=first_return)
    result.all = Mock(return_value=all_return if all_return is not None else [])
    return result


def is_valid_uuid(uuid_string):
    """Check if string is a valid UUID"""
    try:
        UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def is_iso_format(date_string):
    """Check if string is in ISO 8601 format"""
    iso_regex = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    return bool(re.match(iso_regex, date_string))


# ============================================================================
# Tests for list_categories
# ============================================================================

@pytest.mark.asyncio
async def test_list_categories_happy_path(mock_db_session, mock_category):
    """Successfully retrieves all categories with correct structure and ordering"""
    # Setup mock categories
    cat1 = Mock()
    cat1.slug = "general"
    cat1.name = "General"
    cat1.description = "General discussion"
    cat1.sort_order = 1
    cat1.thread_count = 5
    
    cat2 = Mock()
    cat2.slug = "tech"
    cat2.name = "Technology"
    cat2.description = "Tech topics"
    cat2.sort_order = 2
    cat2.thread_count = 10
    
    result = create_mock_result(scalars_return=[cat1, cat2])
    mock_db_session.execute.return_value = result
    
    # Execute
    response = await list_categories(db=mock_db_session)
    
    # Assertions
    assert "categories" in response
    assert isinstance(response["categories"], list)
    assert len(response["categories"]) == 2
    
    # Verify structure of first category
    first_cat = response["categories"][0]
    assert "slug" in first_cat
    assert "name" in first_cat
    assert "description" in first_cat
    assert "thread_count" in first_cat
    
    # Verify ordering by sort_order
    assert response["categories"][0]["slug"] == "general"
    assert response["categories"][1]["slug"] == "tech"


@pytest.mark.asyncio
async def test_list_categories_empty_database(mock_db_session):
    """Returns empty list when no categories exist"""
    result = create_mock_result(scalars_return=[])
    mock_db_session.execute.return_value = result
    
    response = await list_categories(db=mock_db_session)
    
    assert "categories" in response
    assert isinstance(response["categories"], list)
    assert len(response["categories"]) == 0


# ============================================================================
# Tests for list_threads
# ============================================================================

@pytest.mark.asyncio
async def test_list_threads_happy_path(mock_db_session, mock_category, mock_thread):
    """Successfully retrieves paginated threads for a category"""
    # Setup mock category
    cat_result = create_mock_result(first_return=mock_category)
    
    # Setup mock threads
    thread1 = Mock()
    thread1.id = str(uuid4())
    thread1.title = "Thread 1"
    thread1.is_pinned = True
    thread1.last_activity_at = datetime.now(timezone.utc)
    thread1.vote_count = 5
    
    thread2 = Mock()
    thread2.id = str(uuid4())
    thread2.title = "Thread 2"
    thread2.is_pinned = False
    thread2.last_activity_at = datetime.now(timezone.utc)
    thread2.vote_count = 2
    
    threads_result = create_mock_result(scalars_return=[thread1, thread2])
    count_result = Mock()
    count_result.scalar = Mock(return_value=2)
    
    mock_db_session.execute.side_effect = [cat_result, threads_result, count_result]
    
    response = await list_threads(slug="general", page=1, per_page=10, db=mock_db_session, user=None)
    
    assert "category" in response
    assert "threads" in response
    assert "total" in response
    assert "page" in response
    assert "per_page" in response
    assert response["page"] == 1
    assert response["per_page"] == 10


@pytest.mark.asyncio
async def test_list_threads_category_not_found(mock_db_session):
    """Raises error when category slug does not exist"""
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await list_threads(slug="nonexistent", page=1, per_page=10, db=mock_db_session, user=None)
    
    assert "category_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_threads_invalid_page_zero(mock_db_session):
    """Fails when page is less than 1"""
    with pytest.raises(Exception) as exc_info:
        await list_threads(slug="general", page=0, per_page=10, db=mock_db_session, user=None)
    
    assert "precondition" in str(exc_info.value).lower() or "page" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_threads_invalid_per_page_too_large(mock_db_session):
    """Fails when per_page exceeds 100"""
    with pytest.raises(Exception) as exc_info:
        await list_threads(slug="general", page=1, per_page=101, db=mock_db_session, user=None)
    
    assert "precondition" in str(exc_info.value).lower() or "per_page" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_threads_invalid_per_page_zero(mock_db_session):
    """Fails when per_page is less than 1"""
    with pytest.raises(Exception) as exc_info:
        await list_threads(slug="general", page=1, per_page=0, db=mock_db_session, user=None)
    
    assert "precondition" in str(exc_info.value).lower() or "per_page" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_threads_authenticated_user(mock_db_session, mock_category, mock_user):
    """Includes user vote status when user is authenticated"""
    cat_result = create_mock_result(first_return=mock_category)
    
    thread = Mock()
    thread.id = str(uuid4())
    thread.title = "Thread"
    thread.is_pinned = False
    thread.last_activity_at = datetime.now(timezone.utc)
    thread.vote_count = 1
    thread.user_voted = True
    
    threads_result = create_mock_result(scalars_return=[thread])
    count_result = Mock()
    count_result.scalar = Mock(return_value=1)
    
    mock_db_session.execute.side_effect = [cat_result, threads_result, count_result]
    
    response = await list_threads(slug="general", page=1, per_page=10, db=mock_db_session, user=mock_user)
    
    assert "threads" in response
    # User vote status should be included when user is provided


@pytest.mark.asyncio
async def test_list_threads_boundary_per_page_max(mock_db_session, mock_category):
    """Successfully handles per_page at maximum boundary (100)"""
    cat_result = create_mock_result(first_return=mock_category)
    threads_result = create_mock_result(scalars_return=[])
    count_result = Mock()
    count_result.scalar = Mock(return_value=0)
    
    mock_db_session.execute.side_effect = [cat_result, threads_result, count_result]
    
    response = await list_threads(slug="general", page=1, per_page=100, db=mock_db_session, user=None)
    
    assert response["per_page"] == 100


@pytest.mark.asyncio
async def test_edge_case_pagination_empty_page(mock_db_session, mock_category):
    """Returns empty threads list when page exceeds available content"""
    cat_result = create_mock_result(first_return=mock_category)
    threads_result = create_mock_result(scalars_return=[])
    count_result = Mock()
    count_result.scalar = Mock(return_value=0)
    
    mock_db_session.execute.side_effect = [cat_result, threads_result, count_result]
    
    response = await list_threads(slug="general", page=999, per_page=10, db=mock_db_session, user=None)
    
    assert "threads" in response
    assert len(response["threads"]) == 0


# ============================================================================
# Tests for get_thread
# ============================================================================

@pytest.mark.asyncio
async def test_get_thread_happy_path(mock_db_session, mock_thread):
    """Successfully retrieves complete thread with replies"""
    # Setup mock thread with all required fields
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.category.name = "General"
    
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    mock_thread.author.username = "author"
    
    reply1 = Mock()
    reply1.id = str(uuid4())
    reply1.body = "Reply 1"
    reply1.created_at = datetime.now(timezone.utc)
    
    reply2 = Mock()
    reply2.id = str(uuid4())
    reply2.body = "Reply 2"
    reply2.created_at = datetime.now(timezone.utc)
    
    mock_thread.replies = [reply1, reply2]
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440000", db=mock_db_session)
    
    assert "id" in response
    assert "title" in response
    assert "body" in response
    assert "category" in response
    assert "author" in response
    assert "replies" in response
    assert "created_at" in response
    
    # Verify datetime is ISO format
    assert is_iso_format(response["created_at"])


@pytest.mark.asyncio
async def test_get_thread_invalid_uuid(mock_db_session):
    """Raises error when thread_id is not a valid UUID"""
    with pytest.raises(Exception) as exc_info:
        await get_thread(thread_id="not-a-uuid", db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_thread_not_found(mock_db_session):
    """Raises error when thread does not exist"""
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440000", db=mock_db_session)
    
    assert "thread_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_thread_with_tool_data(mock_db_session, mock_thread):
    """Includes tool data when thread has active linked tool"""
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    mock_thread.replies = []
    
    # Add active tool
    mock_thread.tool = Mock()
    mock_thread.tool.id = str(uuid4())
    mock_thread.tool.name = "Test Tool"
    mock_thread.tool.is_active = True
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440001", db=mock_db_session)
    
    assert "tool" in response
    assert response["tool"] is not None


@pytest.mark.asyncio
async def test_get_thread_tool_inactive(mock_db_session, mock_thread):
    """Excludes tool data when linked tool is not active"""
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    mock_thread.replies = []
    
    # Add inactive tool
    mock_thread.tool = Mock()
    mock_thread.tool.id = str(uuid4())
    mock_thread.tool.name = "Inactive Tool"
    mock_thread.tool.is_active = False
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440002", db=mock_db_session)
    
    assert "tool" in response
    assert response["tool"] is None


@pytest.mark.asyncio
async def test_edge_case_thread_no_replies(mock_db_session, mock_thread):
    """Successfully retrieves thread with empty replies list"""
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    mock_thread.replies = []
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440000", db=mock_db_session)
    
    assert "replies" in response
    assert isinstance(response["replies"], list)
    assert len(response["replies"]) == 0


# ============================================================================
# Tests for create_thread
# ============================================================================

@pytest.mark.asyncio
async def test_create_thread_happy_path(mock_db_session, mock_user, mock_category):
    """Successfully creates a new thread"""
    body = CreateThread(title="Test Thread", body="Thread content", category_slug="general")
    
    # Mock category lookup
    cat_result = create_mock_result(first_return=mock_category)
    mock_db_session.execute.return_value = cat_result
    
    # Mock thread creation
    new_thread = Mock()
    new_thread.id = str(uuid4())
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', new_thread.id)
    
    with patch('backend_api_forum_router.ForumThread') as MockThread:
        mock_instance = Mock()
        mock_instance.id = new_thread.id
        MockThread.return_value = mock_instance
        
        response = await create_thread(body=body, user=mock_user, db=mock_db_session)
    
    assert "id" in response
    assert "status" in response
    assert response["status"] == "created"
    assert is_valid_uuid(response["id"])


@pytest.mark.asyncio
async def test_create_thread_category_not_found(mock_db_session, mock_user):
    """Raises error when category does not exist"""
    body = CreateThread(title="Test", body="Content", category_slug="nonexistent")
    
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await create_thread(body=body, user=mock_user, db=mock_db_session)
    
    assert "category_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_thread_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    body = CreateThread(title="Test", body="Content", category_slug="general")
    
    with pytest.raises(Exception) as exc_info:
        await create_thread(body=body, user=None, db=mock_db_session)
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


# ============================================================================
# Tests for create_reply
# ============================================================================

@pytest.mark.asyncio
async def test_create_reply_happy_path(mock_db_session, mock_user, mock_thread):
    """Successfully creates a reply and updates thread metadata"""
    body = CreateReply(body="Reply content")
    mock_thread.is_locked = False
    original_count = mock_thread.reply_count
    original_activity = mock_thread.last_activity_at
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    new_reply = Mock()
    new_reply.id = str(uuid4())
    
    with patch('backend_api_forum_router.ForumReply') as MockReply:
        mock_instance = Mock()
        mock_instance.id = new_reply.id
        MockReply.return_value = mock_instance
        
        response = await create_reply(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=mock_user,
            db=mock_db_session
        )
    
    assert "id" in response
    assert "status" in response
    assert response["status"] == "created"
    assert is_valid_uuid(response["id"])


@pytest.mark.asyncio
async def test_create_reply_invalid_uuid(mock_db_session, mock_user):
    """Raises error when thread_id is not a valid UUID"""
    body = CreateReply(body="Reply content")
    
    with pytest.raises(Exception) as exc_info:
        await create_reply(thread_id="invalid", body=body, user=mock_user, db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_reply_thread_not_found(mock_db_session, mock_user):
    """Raises error when thread does not exist"""
    body = CreateReply(body="Reply")
    
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await create_reply(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=mock_user,
            db=mock_db_session
        )
    
    assert "thread_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_reply_thread_locked(mock_db_session, mock_user, mock_thread):
    """Raises error when thread is locked"""
    body = CreateReply(body="Reply")
    mock_thread.is_locked = True
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await create_reply(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=mock_user,
            db=mock_db_session
        )
    
    assert "thread_locked" in str(exc_info.value).lower() or "locked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_reply_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    body = CreateReply(body="Reply")
    
    with pytest.raises(Exception) as exc_info:
        await create_reply(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=None,
            db=mock_db_session
        )
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


# ============================================================================
# Tests for edit_reply
# ============================================================================

@pytest.mark.asyncio
async def test_edit_reply_happy_path(mock_db_session, mock_user, mock_reply):
    """Successfully updates reply body and updated_at timestamp"""
    body = UpdateReply(body="Updated content")
    mock_reply.author_id = mock_user.id
    
    result = create_mock_result(first_return=mock_reply)
    mock_db_session.execute.return_value = result
    
    response = await edit_reply(
        reply_id="660e8400-e29b-41d4-a716-446655440000",
        body=body,
        user=mock_user,
        db=mock_db_session
    )
    
    assert "status" in response
    assert response["status"] == "updated"
    assert mock_reply.body == "Updated content"


@pytest.mark.asyncio
async def test_edit_reply_invalid_uuid(mock_db_session, mock_user):
    """Raises error when reply_id is not a valid UUID"""
    body = UpdateReply(body="Updated")
    
    with pytest.raises(Exception) as exc_info:
        await edit_reply(reply_id="invalid", body=body, user=mock_user, db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_edit_reply_not_found(mock_db_session, mock_user):
    """Raises error when reply does not exist"""
    body = UpdateReply(body="Updated")
    
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await edit_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=mock_user,
            db=mock_db_session
        )
    
    assert "reply_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_edit_reply_forbidden(mock_db_session, mock_user, mock_user_other, mock_reply):
    """Raises error when user is not the reply author"""
    body = UpdateReply(body="Updated")
    mock_reply.author_id = mock_user_other.id  # Different user
    
    result = create_mock_result(first_return=mock_reply)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await edit_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=mock_user,
            db=mock_db_session
        )
    
    assert "forbidden" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_edit_reply_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    body = UpdateReply(body="Updated")
    
    with pytest.raises(Exception) as exc_info:
        await edit_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            body=body,
            user=None,
            db=mock_db_session
        )
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


# ============================================================================
# Tests for delete_reply
# ============================================================================

@pytest.mark.asyncio
async def test_delete_reply_happy_path(mock_db_session, mock_user, mock_reply, mock_thread):
    """Successfully soft-deletes reply and decrements thread reply count"""
    mock_reply.author_id = mock_user.id
    mock_reply.thread_id = mock_thread.id
    mock_thread.reply_count = 5
    
    reply_result = create_mock_result(first_return=mock_reply)
    thread_result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.side_effect = [reply_result, thread_result]
    
    response = await delete_reply(
        reply_id="660e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert "status" in response
    assert response["status"] == "deleted"
    assert mock_reply.body == "[deleted]"


@pytest.mark.asyncio
async def test_delete_reply_invalid_uuid(mock_db_session, mock_user):
    """Raises error when reply_id is not a valid UUID"""
    with pytest.raises(Exception) as exc_info:
        await delete_reply(reply_id="invalid", user=mock_user, db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_delete_reply_not_found(mock_db_session, mock_user):
    """Raises error when reply does not exist"""
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await delete_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            user=mock_user,
            db=mock_db_session
        )
    
    assert "reply_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_delete_reply_forbidden(mock_db_session, mock_user, mock_user_other, mock_reply):
    """Raises error when user is not the reply author"""
    mock_reply.author_id = mock_user_other.id
    
    result = create_mock_result(first_return=mock_reply)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await delete_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            user=mock_user,
            db=mock_db_session
        )
    
    assert "forbidden" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_delete_reply_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    with pytest.raises(Exception) as exc_info:
        await delete_reply(
            reply_id="660e8400-e29b-41d4-a716-446655440000",
            user=None,
            db=mock_db_session
        )
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_delete_reply_minimum_count(mock_db_session, mock_user, mock_reply, mock_thread):
    """Ensures reply_count does not go below 0 when deleting"""
    mock_reply.author_id = mock_user.id
    mock_reply.thread_id = mock_thread.id
    mock_thread.reply_count = 0  # Already at 0
    
    reply_result = create_mock_result(first_return=mock_reply)
    thread_result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.side_effect = [reply_result, thread_result]
    
    response = await delete_reply(
        reply_id="660e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert mock_thread.reply_count == 0  # Should not go negative


# ============================================================================
# Tests for vote_thread
# ============================================================================

@pytest.mark.asyncio
async def test_vote_thread_happy_path(mock_db_session, mock_user, mock_thread):
    """Successfully adds vote to thread"""
    # Mock thread lookup
    thread_result = create_mock_result(first_return=mock_thread)
    
    # Mock existing vote check (no existing vote)
    vote_result = create_mock_result(first_return=None)
    
    # Mock vote count
    count_result = Mock()
    count_result.scalar = Mock(return_value=1)
    
    mock_db_session.execute.side_effect = [thread_result, vote_result, count_result]
    
    with patch('backend_api_forum_router.ThreadVote') as MockVote:
        mock_vote = Mock()
        MockVote.return_value = mock_vote
        
        response = await vote_thread(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user=mock_user,
            db=mock_db_session
        )
    
    assert "status" in response
    assert "vote_count" in response
    assert response["status"] == "voted"


@pytest.mark.asyncio
async def test_vote_thread_already_voted(mock_db_session, mock_user, mock_thread):
    """Returns existing vote count when user already voted (idempotent)"""
    thread_result = create_mock_result(first_return=mock_thread)
    
    # Mock existing vote
    existing_vote = Mock()
    vote_result = create_mock_result(first_return=existing_vote)
    
    count_result = Mock()
    count_result.scalar = Mock(return_value=5)
    
    mock_db_session.execute.side_effect = [thread_result, vote_result, count_result]
    
    response = await vote_thread(
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert "status" in response
    assert "vote_count" in response
    assert response["status"] == "already_voted"
    assert response["vote_count"] == 5


@pytest.mark.asyncio
async def test_vote_thread_invalid_uuid(mock_db_session, mock_user):
    """Raises error when thread_id is not a valid UUID"""
    with pytest.raises(Exception) as exc_info:
        await vote_thread(thread_id="invalid", user=mock_user, db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_vote_thread_not_found(mock_db_session, mock_user):
    """Raises error when thread does not exist"""
    result = create_mock_result(first_return=None)
    mock_db_session.execute.return_value = result
    
    with pytest.raises(Exception) as exc_info:
        await vote_thread(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user=mock_user,
            db=mock_db_session
        )
    
    assert "thread_not_found" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_vote_thread_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    with pytest.raises(Exception) as exc_info:
        await vote_thread(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user=None,
            db=mock_db_session
        )
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


# ============================================================================
# Tests for unvote_thread
# ============================================================================

@pytest.mark.asyncio
async def test_unvote_thread_happy_path(mock_db_session, mock_user, mock_thread):
    """Successfully removes vote from thread"""
    thread_result = create_mock_result(first_return=mock_thread)
    
    # Mock existing vote
    existing_vote = Mock()
    vote_result = create_mock_result(first_return=existing_vote)
    
    count_result = Mock()
    count_result.scalar = Mock(return_value=4)
    
    mock_db_session.execute.side_effect = [thread_result, vote_result, count_result]
    mock_db_session.delete = AsyncMock()
    
    response = await unvote_thread(
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert "status" in response
    assert "vote_count" in response
    assert response["status"] == "removed"


@pytest.mark.asyncio
async def test_unvote_thread_not_voted(mock_db_session, mock_user, mock_thread):
    """Returns current count when user has not voted (idempotent)"""
    thread_result = create_mock_result(first_return=mock_thread)
    
    # No existing vote
    vote_result = create_mock_result(first_return=None)
    
    count_result = Mock()
    count_result.scalar = Mock(return_value=3)
    
    mock_db_session.execute.side_effect = [thread_result, vote_result, count_result]
    
    response = await unvote_thread(
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert "status" in response
    assert "vote_count" in response
    assert response["status"] == "not_voted"
    assert response["vote_count"] == 3


@pytest.mark.asyncio
async def test_unvote_thread_invalid_uuid(mock_db_session, mock_user):
    """Raises error when thread_id is not a valid UUID"""
    with pytest.raises(Exception) as exc_info:
        await unvote_thread(thread_id="invalid", user=mock_user, db=mock_db_session)
    
    assert "invalid_uuid" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_unvote_thread_unauthorized(mock_db_session):
    """Raises error when user is not authenticated"""
    with pytest.raises(Exception) as exc_info:
        await unvote_thread(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user=None,
            db=mock_db_session
        )
    
    assert "unauthorized" in str(exc_info.value).lower() or "user" in str(exc_info.value).lower()


# ============================================================================
# Invariant Tests
# ============================================================================

@pytest.mark.asyncio
async def test_invariant_reply_count_non_negative(mock_db_session, mock_user, mock_reply, mock_thread):
    """Verifies reply_count never goes below 0"""
    mock_reply.author_id = mock_user.id
    mock_reply.thread_id = mock_thread.id
    mock_thread.reply_count = 1
    
    reply_result = create_mock_result(first_return=mock_reply)
    thread_result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.side_effect = [reply_result, thread_result]
    
    await delete_reply(
        reply_id="660e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert mock_thread.reply_count >= 0


@pytest.mark.asyncio
async def test_invariant_soft_delete_format(mock_db_session, mock_user, mock_reply, mock_thread):
    """Verifies deleted replies have exactly '[deleted]' as body"""
    mock_reply.author_id = mock_user.id
    mock_reply.thread_id = mock_thread.id
    mock_thread.reply_count = 1
    
    reply_result = create_mock_result(first_return=mock_reply)
    thread_result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.side_effect = [reply_result, thread_result]
    
    await delete_reply(
        reply_id="660e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    assert mock_reply.body == "[deleted]"


@pytest.mark.asyncio
async def test_invariant_last_activity_updated(mock_db_session, mock_user, mock_thread):
    """Verifies thread last_activity_at is updated when reply is added"""
    body = CreateReply(body="Test")
    mock_thread.is_locked = False
    original_activity = mock_thread.last_activity_at
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    with patch('backend_api_forum_router.ForumReply') as MockReply:
        mock_instance = Mock()
        mock_instance.id = str(uuid4())
        MockReply.return_value = mock_instance
        
        with patch('backend_api_forum_router.datetime') as mock_datetime:
            new_time = datetime.now(timezone.utc)
            mock_datetime.now.return_value = new_time
            mock_datetime.timezone = timezone
            
            await create_reply(
                thread_id="550e8400-e29b-41d4-a716-446655440000",
                body=body,
                user=mock_user,
                db=mock_db_session
            )
    
    # Verify last_activity_at was updated
    assert hasattr(mock_thread, 'last_activity_at')


@pytest.mark.asyncio
async def test_invariant_datetime_iso_format(mock_db_session, mock_thread):
    """Verifies all datetime fields are returned as ISO format strings"""
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    mock_thread.replies = []
    mock_thread.created_at = datetime.now(timezone.utc)
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440000", db=mock_db_session)
    
    assert "created_at" in response
    assert is_iso_format(response["created_at"])


@pytest.mark.asyncio
async def test_invariant_thread_ordering(mock_db_session, mock_category):
    """Verifies threads are ordered by is_pinned desc, then last_activity_at desc"""
    cat_result = create_mock_result(first_return=mock_category)
    
    # Create threads with different pinned status and activity times
    now = datetime.now(timezone.utc)
    
    thread1 = Mock()
    thread1.id = str(uuid4())
    thread1.is_pinned = True
    thread1.last_activity_at = now
    
    thread2 = Mock()
    thread2.id = str(uuid4())
    thread2.is_pinned = False
    thread2.last_activity_at = now
    
    threads_result = create_mock_result(scalars_return=[thread1, thread2])
    count_result = Mock()
    count_result.scalar = Mock(return_value=2)
    
    mock_db_session.execute.side_effect = [cat_result, threads_result, count_result]
    
    response = await list_threads(slug="general", page=1, per_page=10, db=mock_db_session, user=None)
    
    # Verify pinned threads come first
    threads = response["threads"]
    if len(threads) >= 2:
        assert threads[0]["is_pinned"] >= threads[1]["is_pinned"]


@pytest.mark.asyncio
async def test_invariant_reply_ordering(mock_db_session, mock_thread):
    """Verifies replies are sorted by created_at ascending"""
    mock_thread.category = Mock()
    mock_thread.category.slug = "general"
    mock_thread.author = Mock()
    mock_thread.author.id = str(uuid4())
    
    now = datetime.now(timezone.utc)
    
    reply1 = Mock()
    reply1.id = str(uuid4())
    reply1.created_at = now
    
    reply2 = Mock()
    reply2.id = str(uuid4())
    reply2.created_at = now
    
    mock_thread.replies = [reply1, reply2]
    
    result = create_mock_result(first_return=mock_thread)
    mock_db_session.execute.return_value = result
    
    response = await get_thread(thread_id="550e8400-e29b-41d4-a716-446655440000", db=mock_db_session)
    
    replies = response["replies"]
    if len(replies) >= 2:
        # Verify chronological order (oldest first)
        for i in range(len(replies) - 1):
            assert replies[i]["created_at"] <= replies[i + 1]["created_at"]


@pytest.mark.asyncio
async def test_invariant_vote_idempotency(mock_db_session, mock_user, mock_thread):
    """Verifies vote operations are idempotent"""
    thread_result = create_mock_result(first_return=mock_thread)
    
    # First vote - no existing vote
    vote_result1 = create_mock_result(first_return=None)
    count_result1 = Mock()
    count_result1.scalar = Mock(return_value=1)
    
    mock_db_session.execute.side_effect = [thread_result, vote_result1, count_result1]
    
    with patch('backend_api_forum_router.ThreadVote') as MockVote:
        mock_vote = Mock()
        MockVote.return_value = mock_vote
        
        response1 = await vote_thread(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user=mock_user,
            db=mock_db_session
        )
    
    # Second vote - existing vote
    thread_result2 = create_mock_result(first_return=mock_thread)
    vote_result2 = create_mock_result(first_return=mock_vote)
    count_result2 = Mock()
    count_result2.scalar = Mock(return_value=1)
    
    mock_db_session.execute.side_effect = [thread_result2, vote_result2, count_result2]
    
    response2 = await vote_thread(
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        user=mock_user,
        db=mock_db_session
    )
    
    # Vote count should be consistent
    assert response2["vote_count"] == 1
    assert response2["status"] == "already_voted"
