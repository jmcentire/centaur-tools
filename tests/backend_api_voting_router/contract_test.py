"""
Contract-based test suite for backend_api_voting_router

This test suite verifies the voting router implementation against its contract.
Tests cover happy paths, edge cases, error cases, and invariants using mocked
dependencies.

Test Categories:
- Happy Path: Standard successful operations
- Edge Cases: Boundary conditions, special inputs, concurrent access
- Error Cases: Tool not found, inactive tools, database errors
- Invariants: Vote count consistency, user isolation, idempotency
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Any, Dict
import asyncio

# Import the component under test
from backend.api.voting.router import vote_useful, remove_vote


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    user = Mock()
    user.id = 1
    user.username = "test_user"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_user_2():
    """Create a second mock user for isolation tests"""
    user = Mock()
    user.id = 2
    user.username = "test_user_2"
    user.email = "test2@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_tool():
    """Create a mock active tool"""
    tool = Mock()
    tool.id = 1
    tool.slug = "test-tool"
    tool.name = "Test Tool"
    tool.is_active = True
    return tool


@pytest.fixture
def mock_inactive_tool():
    """Create a mock inactive tool"""
    tool = Mock()
    tool.id = 2
    tool.slug = "inactive-tool"
    tool.name = "Inactive Tool"
    tool.is_active = False
    return tool


@pytest.fixture
def mock_db_session():
    """Create a mock AsyncSession"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    return session


@pytest.fixture
def mock_tool_vote():
    """Create a mock ToolVote record"""
    vote = Mock()
    vote.id = 1
    vote.user_id = 1
    vote.tool_id = 1
    return vote


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_query_result(result=None, scalar_result=None):
    """Create a mock query result"""
    mock_result = AsyncMock()
    if scalar_result is not None:
        mock_result.scalar_one_or_none = AsyncMock(return_value=scalar_result)
        mock_result.scalar = AsyncMock(return_value=scalar_result)
    if result is not None:
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=result)))
    return mock_result


def setup_execute_mock(session, *results):
    """Setup session.execute to return multiple results in sequence"""
    session.execute = AsyncMock(side_effect=results)


class ToolNotFoundError(Exception):
    """Custom exception for tool not found"""
    pass


# ============================================================================
# Happy Path Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_happy_path(mock_db_session, mock_user, mock_tool):
    """
    Test: Successfully cast a vote for an active tool when user has not voted before
    Expected: Returns {'status': 'voted', 'vote_count': <count>} where vote_count >= 1
    """
    # Setup: Tool exists, no existing vote, vote count after is 1
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    vote_count_result = create_mock_query_result(scalar_result=1)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["status"] == "voted"
    assert "vote_count" in result
    assert result["vote_count"] >= 1
    assert result["vote_count"] == 1
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_remove_vote_happy_path(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: Successfully remove an existing vote
    Expected: Returns {'status': 'removed', 'vote_count': <count>} where vote_count >= 0
    """
    # Setup: Tool exists, vote exists, vote count after is 0
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    vote_count_result = create_mock_query_result(scalar_result=0)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["status"] == "removed"
    assert "vote_count" in result
    assert result["vote_count"] >= 0
    assert result["vote_count"] == 0
    assert mock_db_session.delete.called
    assert mock_db_session.commit.called


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_already_voted(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: User attempts to vote for a tool they have already voted for
    Expected: Returns {'status': 'already_voted'} without modifying database
    """
    # Setup: Tool exists, vote already exists
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result
    )
    
    # Execute
    result = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["status"] == "already_voted"
    assert "vote_count" not in result or result.get("vote_count") is None
    assert not mock_db_session.add.called
    assert not mock_db_session.commit.called


@pytest.mark.asyncio
async def test_remove_vote_not_voted(mock_db_session, mock_user, mock_tool):
    """
    Test: User attempts to remove a vote they never cast
    Expected: Returns {'status': 'not_voted'} without modifying database
    """
    # Setup: Tool exists, no vote exists
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result
    )
    
    # Execute
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["status"] == "not_voted"
    assert "vote_count" not in result or result.get("vote_count") is None
    assert not mock_db_session.delete.called
    assert not mock_db_session.commit.called


@pytest.mark.asyncio
async def test_vote_useful_empty_slug(mock_db_session, mock_user):
    """
    Test: Attempt to vote with empty string slug
    Expected: Raises tool_not_found error or handles gracefully
    """
    # Setup: Empty slug results in no tool found
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found or similar
        await vote_useful(slug="", user=mock_user, db=mock_db_session)


@pytest.mark.asyncio
async def test_remove_vote_empty_slug(mock_db_session, mock_user):
    """
    Test: Attempt to remove vote with empty string slug
    Expected: Raises tool_not_found error or handles gracefully
    """
    # Setup: Empty slug results in no tool found
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found or similar
        await remove_vote(slug="", user=mock_user, db=mock_db_session)


@pytest.mark.asyncio
async def test_vote_useful_special_characters_slug(mock_db_session, mock_user):
    """
    Test: Handle slugs with special characters
    Expected: Processes slug correctly if tool exists
    """
    # Setup: Tool with special characters in slug
    special_tool = Mock()
    special_tool.id = 1
    special_tool.slug = "test-tool_123-abc"
    special_tool.is_active = True
    
    tool_query_result = create_mock_query_result(scalar_result=special_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    vote_count_result = create_mock_query_result(scalar_result=1)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await vote_useful(slug="test-tool_123-abc", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["status"] == "voted"
    assert result["vote_count"] == 1


@pytest.mark.asyncio
async def test_vote_useful_concurrent_votes(mock_db_session, mock_user, mock_tool):
    """
    Test: Multiple concurrent vote attempts by same user
    Expected: Only one vote is recorded, others return already_voted
    """
    # Setup: First call succeeds, subsequent calls find existing vote
    tool_query_result_1 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_1 = create_mock_query_result(scalar_result=None)
    vote_count_result_1 = create_mock_query_result(scalar_result=1)
    
    tool_query_result_2 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_2 = create_mock_query_result(scalar_result=Mock())
    
    mock_db_session.execute = AsyncMock(side_effect=[
        tool_query_result_1,
        existing_vote_result_1,
        vote_count_result_1,
        tool_query_result_2,
        existing_vote_result_2,
    ])
    
    # Execute concurrently
    results = await asyncio.gather(
        vote_useful(slug="test-tool", user=mock_user, db=mock_db_session),
        vote_useful(slug="test-tool", user=mock_user, db=mock_db_session),
    )
    
    # Assert
    statuses = [r["status"] for r in results]
    assert "voted" in statuses
    assert "already_voted" in statuses or statuses.count("voted") == 1


@pytest.mark.asyncio
async def test_vote_removal_idempotency(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: Removing vote multiple times is idempotent
    Expected: First removal succeeds, second returns not_voted
    """
    # Setup: First removal finds vote, second removal finds no vote
    tool_query_result_1 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_1 = create_mock_query_result(scalar_result=mock_tool_vote)
    vote_count_result_1 = create_mock_query_result(scalar_result=0)
    
    tool_query_result_2 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_2 = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result_1,
        existing_vote_result_1,
        vote_count_result_1,
        tool_query_result_2,
        existing_vote_result_2
    )
    
    # Execute
    result1 = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    result2 = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result1["status"] == "removed"
    assert result2["status"] == "not_voted"


# ============================================================================
# Error Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_tool_not_found(mock_db_session, mock_user):
    """
    Test: Attempt to vote for a non-existent tool slug
    Expected: Raises tool_not_found error
    """
    # Setup: No tool found
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found
        await vote_useful(slug="nonexistent-tool", user=mock_user, db=mock_db_session)
    
    assert not mock_db_session.add.called


@pytest.mark.asyncio
async def test_vote_useful_inactive_tool(mock_db_session, mock_user, mock_inactive_tool):
    """
    Test: Attempt to vote for a tool where is_active is False
    Expected: Raises tool_not_found error
    """
    # Setup: Tool exists but is inactive (treated as not found)
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found
        await vote_useful(slug="inactive-tool", user=mock_user, db=mock_db_session)
    
    assert not mock_db_session.add.called


@pytest.mark.asyncio
async def test_remove_vote_tool_not_found(mock_db_session, mock_user):
    """
    Test: Attempt to remove vote for non-existent tool
    Expected: Raises tool_not_found error
    """
    # Setup: No tool found
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found
        await remove_vote(slug="nonexistent-tool", user=mock_user, db=mock_db_session)
    
    assert not mock_db_session.delete.called


@pytest.mark.asyncio
async def test_remove_vote_inactive_tool(mock_db_session, mock_user, mock_inactive_tool):
    """
    Test: Attempt to remove vote for inactive tool
    Expected: Raises tool_not_found error
    """
    # Setup: Tool exists but is inactive (treated as not found)
    tool_query_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(mock_db_session, tool_query_result)
    
    # Execute & Assert
    with pytest.raises(Exception):  # Should raise tool_not_found
        await remove_vote(slug="inactive-tool", user=mock_user, db=mock_db_session)
    
    assert not mock_db_session.delete.called


@pytest.mark.asyncio
async def test_vote_useful_database_error(mock_db_session, mock_user, mock_tool):
    """
    Test: Handle database connection errors during voting
    Expected: Exception is raised or handled, no partial state committed
    """
    # Setup: Database raises exception
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    
    mock_db_session.execute = AsyncMock(side_effect=[
        tool_query_result,
        existing_vote_result,
        Exception("Database connection error")
    ])
    
    mock_db_session.commit = AsyncMock(side_effect=Exception("Database connection error"))
    
    # Execute & Assert
    with pytest.raises(Exception):
        await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)


@pytest.mark.asyncio
async def test_remove_vote_database_error(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: Handle database connection errors during vote removal
    Expected: Exception is raised or handled, no partial state committed
    """
    # Setup: Database raises exception
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    
    mock_db_session.execute = AsyncMock(side_effect=[
        tool_query_result,
        existing_vote_result,
        Exception("Database connection error")
    ])
    
    mock_db_session.commit = AsyncMock(side_effect=Exception("Database connection error"))
    
    # Execute & Assert
    with pytest.raises(Exception):
        await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)


# ============================================================================
# Invariant Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_useful_vote_count_consistency(mock_db_session, mock_user, mock_tool):
    """
    Test: Vote count reflects accurate total after voting
    Expected: vote_count matches actual database count
    """
    # Setup: Tool has 5 existing votes, adding one makes 6
    initial_count = 5
    expected_count = 6
    
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    vote_count_result = create_mock_query_result(scalar_result=expected_count)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["vote_count"] == expected_count
    assert result["vote_count"] > initial_count


@pytest.mark.asyncio
async def test_remove_vote_count_consistency(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: Vote count reflects accurate total after removal
    Expected: vote_count matches actual database count after removal
    """
    # Setup: Tool has 3 votes, removing one makes 2
    expected_count = 2
    
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    vote_count_result = create_mock_query_result(scalar_result=expected_count)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["vote_count"] == expected_count


@pytest.mark.asyncio
async def test_vote_useful_user_isolation(mock_db_session, mock_user, mock_user_2, mock_tool):
    """
    Test: Voting by one user does not affect another user's vote status
    Expected: Both users can vote independently
    """
    # Setup: User 1 votes
    tool_query_result_1 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_1 = create_mock_query_result(scalar_result=None)
    vote_count_result_1 = create_mock_query_result(scalar_result=1)
    
    # User 2 votes
    tool_query_result_2 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_2 = create_mock_query_result(scalar_result=None)
    vote_count_result_2 = create_mock_query_result(scalar_result=2)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result_1,
        existing_vote_result_1,
        vote_count_result_1,
        tool_query_result_2,
        existing_vote_result_2,
        vote_count_result_2
    )
    
    # Execute
    result1 = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    result2 = await vote_useful(slug="test-tool", user=mock_user_2, db=mock_db_session)
    
    # Assert
    assert result1["status"] == "voted"
    assert result2["status"] == "voted"
    assert result2["vote_count"] == 2
    assert mock_db_session.add.call_count == 2


@pytest.mark.asyncio
async def test_remove_vote_user_isolation(mock_db_session, mock_user, mock_user_2, mock_tool):
    """
    Test: Removing vote by one user does not affect another user's vote
    Expected: Only User A's vote is removed
    """
    # Setup: User 1 removes vote (exists), count goes from 2 to 1
    mock_tool_vote_1 = Mock()
    mock_tool_vote_1.id = 1
    mock_tool_vote_1.user_id = mock_user.id
    mock_tool_vote_1.tool_id = mock_tool.id
    
    tool_query_result_1 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_1 = create_mock_query_result(scalar_result=mock_tool_vote_1)
    vote_count_result_1 = create_mock_query_result(scalar_result=1)
    
    # User 2's vote still exists (checking they still have a vote)
    mock_tool_vote_2 = Mock()
    mock_tool_vote_2.id = 2
    mock_tool_vote_2.user_id = mock_user_2.id
    mock_tool_vote_2.tool_id = mock_tool.id
    
    tool_query_result_2 = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result_2 = create_mock_query_result(scalar_result=mock_tool_vote_2)
    vote_count_result_2 = create_mock_query_result(scalar_result=0)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result_1,
        existing_vote_result_1,
        vote_count_result_1,
        tool_query_result_2,
        existing_vote_result_2,
        vote_count_result_2
    )
    
    # Execute
    result1 = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    result2 = await remove_vote(slug="test-tool", user=mock_user_2, db=mock_db_session)
    
    # Assert
    assert result1["status"] == "removed"
    assert result1["vote_count"] == 1
    assert result2["status"] == "removed"
    assert mock_db_session.delete.call_count == 2


@pytest.mark.asyncio
async def test_vote_count_never_negative(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: Vote count never goes below zero
    Expected: vote_count returns 0, not negative
    """
    # Setup: Remove last vote, count becomes 0
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    vote_count_result = create_mock_query_result(scalar_result=0)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    # Execute
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    # Assert
    assert result["vote_count"] >= 0
    assert result["vote_count"] == 0


# ============================================================================
# Response Type Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vote_response_structure(mock_db_session, mock_user, mock_tool):
    """
    Test: VoteResponse has correct structure
    Expected: Returns dict with 'status' and 'vote_count' keys
    """
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    vote_count_result = create_mock_query_result(scalar_result=1)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    result = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    
    assert isinstance(result, dict)
    assert "status" in result
    assert "vote_count" in result
    assert isinstance(result["status"], str)
    assert isinstance(result["vote_count"], int)


@pytest.mark.asyncio
async def test_already_voted_response_structure(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: AlreadyVotedResponse has correct structure
    Expected: Returns dict with 'status' key
    """
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result
    )
    
    result = await vote_useful(slug="test-tool", user=mock_user, db=mock_db_session)
    
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "already_voted"
    assert isinstance(result["status"], str)


@pytest.mark.asyncio
async def test_removed_vote_response_structure(mock_db_session, mock_user, mock_tool, mock_tool_vote):
    """
    Test: RemovedVoteResponse has correct structure
    Expected: Returns dict with 'status' and 'vote_count' keys
    """
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=mock_tool_vote)
    vote_count_result = create_mock_query_result(scalar_result=0)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result,
        vote_count_result
    )
    
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    assert isinstance(result, dict)
    assert "status" in result
    assert "vote_count" in result
    assert isinstance(result["status"], str)
    assert isinstance(result["vote_count"], int)


@pytest.mark.asyncio
async def test_not_voted_response_structure(mock_db_session, mock_user, mock_tool):
    """
    Test: NotVotedResponse has correct structure
    Expected: Returns dict with 'status' key
    """
    tool_query_result = create_mock_query_result(scalar_result=mock_tool)
    existing_vote_result = create_mock_query_result(scalar_result=None)
    
    setup_execute_mock(
        mock_db_session,
        tool_query_result,
        existing_vote_result
    )
    
    result = await remove_vote(slug="test-tool", user=mock_user, db=mock_db_session)
    
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "not_voted"
    assert isinstance(result["status"], str)
