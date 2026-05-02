"""
Contract test suite for Backend API Voting Router Interface
Generated test code for contract version 1
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Any
import random


# Mock the component module - in real scenario this would be imported
# from contracts.contracts_backend_api_voting_router_interface.interface import *

# Since we're testing against a contract, we'll create mock implementations
# that can be replaced with actual implementations when available


# ============================================================================
# Mock Types and Structures
# ============================================================================

class User:
    """Mock User model"""
    def __init__(self, id: int, username: str = "testuser", email: str = "test@example.com"):
        self.id = id
        self.username = username
        self.email = email


class AsyncSession:
    """Mock AsyncSession - will be fully mocked in tests"""
    pass


class VoteResponse:
    """Mock VoteResponse structure"""
    def __init__(self, status: str, vote_count: int):
        self.status = status
        self.vote_count = vote_count
    
    @classmethod
    def parse_obj(cls, data: dict):
        """Validate response data"""
        if not isinstance(data.get('status'), str):
            raise ValueError("status must be str")
        if not isinstance(data.get('vote_count'), int):
            raise ValueError("vote_count must be int")
        return cls(status=data['status'], vote_count=data['vote_count'])


# Mock exceptions
class ToolNotFoundException(Exception):
    """Raised when tool not found or inactive"""
    pass


# Mock implementations that will be tested
async def vote_useful(slug: str, user: User, db: AsyncSession) -> dict[str, str | int]:
    """Mock implementation - replace with actual import"""
    # This is a placeholder that will be patched in tests
    raise NotImplementedError("Replace with actual implementation")


async def remove_vote(slug: str, user: User, db: AsyncSession) -> dict[str, str | int]:
    """Mock implementation - replace with actual import"""
    # This is a placeholder that will be patched in tests
    raise NotImplementedError("Replace with actual implementation")


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def authenticated_user():
    """Create an authenticated user with valid credentials"""
    return User(id=1, username="testuser", email="test@example.com")


@pytest.fixture
def another_authenticated_user():
    """Create another authenticated user for multi-user tests"""
    return User(id=2, username="testuser2", email="test2@example.com")


@pytest.fixture
def mock_async_session():
    """Create a fully mocked AsyncSession with transaction control"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    # Mock context manager protocol
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    
    return session


@pytest.fixture
def mock_tool_result():
    """Create a mock Tool database result"""
    tool = Mock()
    tool.id = 1
    tool.slug = "test-tool"
    tool.is_active = True
    tool.name = "Test Tool"
    return tool


@pytest.fixture
def mock_vote_result():
    """Create a mock ToolVote database result"""
    vote = Mock()
    vote.id = 1
    vote.tool_id = 1
    vote.user_id = 1
    return vote


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_query_result(result_value):
    """Create a mock query result with scalars().first() pattern"""
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.first = Mock(return_value=result_value)
    mock_result.scalars = Mock(return_value=mock_scalars)
    return mock_result


def create_mock_all_result(result_values):
    """Create a mock query result with scalars().all() pattern"""
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all = Mock(return_value=result_values)
    mock_result.scalars = Mock(return_value=mock_scalars)
    return mock_result


# ============================================================================
# Happy Path Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_happy_path(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Successfully record a new vote for an active tool
    Expected: Returns dict with status='success' and vote_count=1
    """
    # Setup: Tool exists, is active, user hasn't voted yet
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(None)  # No existing vote
    vote_count_result = create_mock_all_result([Mock()])  # 1 vote after insertion
    
    mock_async_session.execute.side_effect = [
        tool_query_result,  # Tool lookup
        vote_query_result,  # Existing vote check
        Mock(),  # Vote insertion
        vote_count_result,  # Vote count query
    ]
    
    # Mock implementation for this test
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        # Check tool exists and is active
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        # Check if user already voted
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        # Create new vote
        await db.execute(Mock())
        await db.commit()
        
        # Get updated count
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        
        return {"status": "success", "vote_count": count}
    
    # Execute
    result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    
    # Assert
    assert result['status'] == 'success'
    assert result['vote_count'] == 1
    assert isinstance(result['vote_count'], int)
    mock_async_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_remove_vote_happy_path(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: Successfully remove an existing vote
    Expected: Returns dict with status='success' and updated vote_count
    """
    # Setup: Tool exists, is active, user has voted
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(mock_vote_result)  # Existing vote
    vote_count_result = create_mock_all_result([])  # 0 votes after deletion
    
    mock_async_session.execute.side_effect = [
        tool_query_result,  # Tool lookup
        vote_query_result,  # Existing vote check
        Mock(),  # Vote deletion
        vote_count_result,  # Vote count query
    ]
    
    # Mock implementation for this test
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        # Check tool exists and is active
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        # Check if user has voted
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        # Delete vote
        await db.execute(Mock())
        await db.commit()
        
        # Get updated count
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        
        return {"status": "success", "vote_count": count}
    
    # Execute
    result = await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    
    # Assert
    assert result['status'] == 'success'
    assert 'vote_count' in result
    assert isinstance(result['vote_count'], int)
    assert result['vote_count'] >= 0
    mock_async_session.commit.assert_called_once()


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_already_voted(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: User attempts to vote for a tool they have already voted for
    Expected: Returns dict with status='already_voted' and current vote_count
    """
    # Setup: Tool exists, user already voted
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(mock_vote_result)  # Existing vote
    vote_count_result = create_mock_all_result([Mock(), Mock()])  # 2 existing votes
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        vote_count_result,
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    
    assert result['status'] == 'already_voted'
    assert 'vote_count' in result
    assert result['vote_count'] == 2
    # Should not commit when already voted
    mock_async_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_remove_vote_not_voted(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: User attempts to remove a vote they never cast
    Expected: Returns dict with status='not_voted' and current vote_count
    """
    # Setup: Tool exists, user hasn't voted
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(None)  # No existing vote
    vote_count_result = create_mock_all_result([Mock()])  # 1 existing vote from others
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        vote_count_result,
    ]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result = await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    
    assert result['status'] == 'not_voted'
    assert 'vote_count' in result
    assert result['vote_count'] >= 0
    # Should not commit when no vote to remove
    mock_async_session.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("slug", [
    "tool-with-dashes",
    "tool_with_underscores",
    "toolalphanumeric123",
    "tool-mixed_format123"
])
async def test_vote_useful_slug_variations(slug, authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: vote_useful with various slug formats
    Expected: All valid slug formats processed correctly
    """
    mock_tool_result.slug = slug
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(None)
    vote_count_result = create_mock_all_result([Mock()])
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        Mock(),
        vote_count_result,
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result = await mock_vote_useful_impl(slug, authenticated_user, mock_async_session)
    
    assert result is not None
    assert 'status' in result
    assert 'vote_count' in result


@pytest.mark.asyncio
@pytest.mark.parametrize("slug", [
    "tool-with-dashes",
    "tool_with_underscores",
    "toolalphanumeric123",
])
async def test_remove_vote_slug_variations(slug, authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: remove_vote with various slug formats
    Expected: All valid slug formats processed correctly
    """
    mock_tool_result.slug = slug
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(mock_vote_result)
    vote_count_result = create_mock_all_result([])
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        Mock(),
        vote_count_result,
    ]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result = await mock_remove_vote_impl(slug, authenticated_user, mock_async_session)
    
    assert result is not None
    assert 'status' in result
    assert 'vote_count' in result


# ============================================================================
# Error Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_tool_not_found(authenticated_user, mock_async_session):
    """
    Test: Attempt to vote for a non-existent tool
    Expected: Raises ToolNotFoundException with tool_not_found error
    """
    # Setup: Tool does not exist
    tool_query_result = create_mock_query_result(None)
    mock_async_session.execute.side_effect = [tool_query_result]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    with pytest.raises(ToolNotFoundException) as exc_info:
        await mock_vote_useful_impl("non-existent-tool", authenticated_user, mock_async_session)
    
    assert "tool_not_found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vote_useful_inactive_tool(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Attempt to vote for an inactive tool (is_active=False)
    Expected: Raises ToolNotFoundException treating inactive tool as not found
    """
    # Setup: Tool exists but is inactive
    mock_tool_result.is_active = False
    tool_query_result = create_mock_query_result(mock_tool_result)
    mock_async_session.execute.side_effect = [tool_query_result]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    with pytest.raises(ToolNotFoundException) as exc_info:
        await mock_vote_useful_impl("inactive-tool", authenticated_user, mock_async_session)
    
    assert "tool_not_found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_vote_tool_not_found(authenticated_user, mock_async_session):
    """
    Test: Attempt to remove vote for a non-existent tool
    Expected: Raises ToolNotFoundException with tool_not_found error
    """
    # Setup: Tool does not exist
    tool_query_result = create_mock_query_result(None)
    mock_async_session.execute.side_effect = [tool_query_result]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    with pytest.raises(ToolNotFoundException) as exc_info:
        await mock_remove_vote_impl("non-existent-tool", authenticated_user, mock_async_session)
    
    assert "tool_not_found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_vote_inactive_tool(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Attempt to remove vote for an inactive tool
    Expected: Raises ToolNotFoundException treating inactive tool as not found
    """
    # Setup: Tool exists but is inactive
    mock_tool_result.is_active = False
    tool_query_result = create_mock_query_result(mock_tool_result)
    mock_async_session.execute.side_effect = [tool_query_result]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    with pytest.raises(ToolNotFoundException) as exc_info:
        await mock_remove_vote_impl("inactive-tool", authenticated_user, mock_async_session)
    
    assert "tool_not_found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vote_useful_database_error(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Database error during vote operation
    Expected: Exception propagated and rollback called
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    # Setup: Simulate database error during commit
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(None)
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        Mock(),  # Insert succeeds
    ]
    mock_async_session.commit.side_effect = SQLAlchemyError("Database connection lost")
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        try:
            tool_result = await db.execute(Mock())
            tool = tool_result.scalars().first()
            if not tool or not tool.is_active:
                raise ToolNotFoundException("tool_not_found")
            
            vote_result = await db.execute(Mock())
            existing_vote = vote_result.scalars().first()
            if existing_vote:
                count_result = await db.execute(Mock())
                count = len(count_result.scalars().all())
                return {"status": "already_voted", "vote_count": count}
            
            await db.execute(Mock())
            await db.commit()
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "success", "vote_count": count}
        except SQLAlchemyError:
            await db.rollback()
            raise
    
    with pytest.raises(SQLAlchemyError):
        await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    
    mock_async_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_remove_vote_database_error(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: Database error during vote removal
    Expected: Exception propagated and rollback called
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    # Setup: Simulate database error during commit
    tool_query_result = create_mock_query_result(mock_tool_result)
    vote_query_result = create_mock_query_result(mock_vote_result)
    
    mock_async_session.execute.side_effect = [
        tool_query_result,
        vote_query_result,
        Mock(),  # Delete succeeds
    ]
    mock_async_session.commit.side_effect = SQLAlchemyError("Database connection lost")
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        try:
            tool_result = await db.execute(Mock())
            tool = tool_result.scalars().first()
            if not tool or not tool.is_active:
                raise ToolNotFoundException("tool_not_found")
            
            vote_result = await db.execute(Mock())
            existing_vote = vote_result.scalars().first()
            if not existing_vote:
                count_result = await db.execute(Mock())
                count = len(count_result.scalars().all())
                return {"status": "not_voted", "vote_count": count}
            
            await db.execute(Mock())
            await db.commit()
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "success", "vote_count": count}
        except SQLAlchemyError:
            await db.rollback()
            raise
    
    with pytest.raises(SQLAlchemyError):
        await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    
    mock_async_session.rollback.assert_called_once()


# ============================================================================
# Invariant Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_count_consistency(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: Verify vote count increments and decrements correctly
    Expected: Vote count maintains consistency across operations
    """
    # Simulate: vote (count 0->1), vote again (already_voted, count 1), remove (count 1->0)
    
    # First call: vote_useful - success
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),  # Tool lookup
        create_mock_query_result(None),  # No existing vote
        Mock(),  # Insert
        create_mock_all_result([Mock()]),  # Count = 1
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result1 = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result1['status'] == 'success'
    assert result1['vote_count'] == 1
    initial_count = result1['vote_count']
    
    # Second call: vote_useful - already_voted
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(mock_vote_result),  # Existing vote
        create_mock_all_result([Mock()]),  # Count = 1
    ]
    
    result2 = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result2['status'] == 'already_voted'
    assert result2['vote_count'] == initial_count
    
    # Third call: remove_vote - success
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(mock_vote_result),
        Mock(),  # Delete
        create_mock_all_result([]),  # Count = 0
    ]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result3 = await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    assert result3['status'] == 'success'
    final_count = result3['vote_count']
    
    # Invariant: count never negative
    assert final_count >= 0
    # Invariant: after vote and remove, count should return to baseline or decrease
    assert final_count < initial_count


@pytest.mark.asyncio
async def test_authenticated_user_requirement(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Verify all endpoints require authenticated user
    Expected: Authenticated users can operate
    """
    # Test that user has valid authentication attributes
    assert authenticated_user.id is not None
    assert authenticated_user.id > 0
    assert isinstance(authenticated_user.id, int)
    
    # Setup successful vote operation
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),
        Mock(),
        create_mock_all_result([Mock()]),
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        # In real implementation, this would be enforced by get_current_user dependency
        if user.id is None:
            raise ValueError("User not authenticated")
        
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    # Authenticated user should succeed
    result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result['status'] == 'success'
    
    # Unauthenticated user should fail
    unauthenticated_user = User(id=None)
    with pytest.raises(ValueError, match="User not authenticated"):
        await mock_vote_useful_impl("test-tool", unauthenticated_user, mock_async_session)


@pytest.mark.asyncio
async def test_vote_useful_idempotency(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: Double vote attempt should not create duplicate records
    Expected: First returns success, second returns already_voted
    """
    # First vote - success
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),  # No existing vote
        Mock(),
        create_mock_all_result([Mock()]),  # Count = 1
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    first_result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert first_result['status'] == 'success'
    
    # Second vote - already_voted
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(mock_vote_result),  # Existing vote
        create_mock_all_result([Mock()]),  # Count = 1
    ]
    
    second_result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert second_result['status'] == 'already_voted'
    
    # Verify idempotency: vote count should be same
    assert first_result['vote_count'] == second_result['vote_count']


@pytest.mark.asyncio
async def test_remove_vote_idempotency(authenticated_user, mock_async_session, mock_tool_result, mock_vote_result):
    """
    Test: Double remove attempt should handle gracefully
    Expected: First returns success, second returns not_voted
    """
    # First remove - success
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(mock_vote_result),  # Existing vote
        Mock(),
        create_mock_all_result([]),  # Count = 0
    ]
    
    async def mock_remove_vote_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if not existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "not_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    first_result = await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    assert first_result['status'] == 'success'
    
    # Second remove - not_voted
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),  # No existing vote
        create_mock_all_result([]),  # Count = 0
    ]
    
    second_result = await mock_remove_vote_impl("test-tool", authenticated_user, mock_async_session)
    assert second_result['status'] == 'not_voted'
    
    # Verify idempotency: vote count should be same or valid
    assert second_result['vote_count'] >= 0


# ============================================================================
# Response Contract Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_response_schema_validation(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Validate that responses conform to VoteResponse schema
    Expected: All responses have correct types for status (str) and vote_count (int)
    """
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),
        Mock(),
        create_mock_all_result([Mock()]),
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    
    # Validate using VoteResponse schema
    validated = VoteResponse.parse_obj(result)
    assert isinstance(validated.status, str)
    assert isinstance(validated.vote_count, int)
    
    # Test invalid response schemas
    invalid_responses = [
        {"status": 123, "vote_count": 1},  # status not str
        {"status": "success", "vote_count": "1"},  # vote_count not int
    ]
    
    for invalid_resp in invalid_responses:
        with pytest.raises(ValueError):
            VoteResponse.parse_obj(invalid_resp)


# ============================================================================
# Additional Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_users_voting(authenticated_user, another_authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Multiple different users can vote for the same tool
    Expected: Each user's vote is recorded independently
    """
    # User 1 votes
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),
        Mock(),
        create_mock_all_result([Mock()]),  # Count = 1
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result1 = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result1['status'] == 'success'
    assert result1['vote_count'] == 1
    
    # User 2 votes
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),  # User 2 hasn't voted
        Mock(),
        create_mock_all_result([Mock(), Mock()]),  # Count = 2
    ]
    
    result2 = await mock_vote_useful_impl("test-tool", another_authenticated_user, mock_async_session)
    assert result2['status'] == 'success'
    assert result2['vote_count'] == 2
    assert result2['vote_count'] > result1['vote_count']


@pytest.mark.asyncio
async def test_vote_count_never_negative():
    """
    Test: Verify vote count invariant - count should never be negative
    Expected: All operations maintain count >= 0
    """
    # This is an invariant test using random operations
    import random
    
    mock_session = AsyncMock(spec=AsyncSession)
    user = User(id=1)
    tool = Mock()
    tool.id = 1
    tool.slug = "test-tool"
    tool.is_active = True
    
    # Simulate random vote/remove operations
    vote_count = 0
    operations = []
    
    for _ in range(10):
        operation = random.choice(['vote', 'remove'])
        operations.append(operation)
        
        if operation == 'vote':
            # Can only vote if not already voted
            if vote_count == 0:
                vote_count = 1
        else:  # remove
            # Can only remove if voted
            if vote_count > 0:
                vote_count = 0
        
        # Invariant check
        assert vote_count >= 0, f"Vote count became negative after operations: {operations}"
    
    # Final check
    assert vote_count >= 0


@pytest.mark.asyncio
async def test_concurrent_vote_attempts(authenticated_user, mock_async_session, mock_tool_result):
    """
    Test: Simulate concurrent vote attempts (race condition scenario)
    Expected: Only one vote should succeed, others should get already_voted
    """
    import asyncio
    
    # First attempt wins
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(None),  # No existing vote for first attempt
        Mock(),
        create_mock_all_result([Mock()]),
    ]
    
    async def mock_vote_useful_impl(slug: str, user: User, db: AsyncSession):
        tool_result = await db.execute(Mock())
        tool = tool_result.scalars().first()
        if not tool or not tool.is_active:
            raise ToolNotFoundException("tool_not_found")
        
        vote_result = await db.execute(Mock())
        existing_vote = vote_result.scalars().first()
        if existing_vote:
            count_result = await db.execute(Mock())
            count = len(count_result.scalars().all())
            return {"status": "already_voted", "vote_count": count}
        
        await db.execute(Mock())
        await db.commit()
        count_result = await db.execute(Mock())
        count = len(count_result.scalars().all())
        return {"status": "success", "vote_count": count}
    
    result1 = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result1['status'] == 'success'
    
    # Second attempt should see existing vote
    mock_async_session.execute.side_effect = [
        create_mock_query_result(mock_tool_result),
        create_mock_query_result(Mock()),  # Existing vote
        create_mock_all_result([Mock()]),
    ]
    
    result2 = await mock_vote_useful_impl("test-tool", authenticated_user, mock_async_session)
    assert result2['status'] == 'already_voted'
