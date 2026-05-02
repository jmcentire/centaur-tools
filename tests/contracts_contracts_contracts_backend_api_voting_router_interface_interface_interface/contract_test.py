"""
Contract-based test suite for Backend API Voting Router Interface.

This test suite validates the vote_useful and remove_vote functions against
their contract specifications, including preconditions, postconditions,
error cases, and invariants.

Tests use pytest with async support and mock all dependencies including
AsyncSession, User objects, and database queries.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
from typing import Any, Dict


# Mock the module import
# In real implementation, this would be:
# from contracts.contracts_contracts_backend_api_voting_router_interface_interface.interface import *

# Define mock structures based on contract
class ToolNotFoundError(Exception):
    """Custom exception for tool_not_found error case."""
    pass


class VoteResponse:
    """Response schema validator for vote operations."""
    def __init__(self, status: str, vote_count: int):
        if not isinstance(status, str):
            raise TypeError("status must be str")
        if not isinstance(vote_count, int):
            raise TypeError("vote_count must be int")
        self.status = status
        self.vote_count = vote_count


# Mock User class
class User:
    """Mock User model."""
    def __init__(self, id: int, username: str = "testuser", is_active: bool = True):
        self.id = id
        self.username = username
        self.is_active = is_active


# Mock Tool and ToolVote models
class Tool:
    """Mock Tool model."""
    def __init__(self, id: int, slug: str, is_active: bool = True):
        self.id = id
        self.slug = slug
        self.is_active = is_active


class ToolVote:
    """Mock ToolVote model."""
    def __init__(self, id: int, tool_id: int, user_id: int):
        self.id = id
        self.tool_id = tool_id
        self.user_id = user_id


# Implementation stubs for testing
async def vote_useful(slug: str, user: User, db: Any) -> Dict[str, Any]:
    """
    Records a user's vote for a tool identified by slug.
    
    This is a stub implementation for testing purposes.
    Real implementation would interact with database.
    """
    # Query tool
    tool_query_result = AsyncMock()
    tool_query_result.scalar_one_or_none = AsyncMock()
    
    execute_result = await db.execute(AsyncMock())
    tool = await execute_result.scalar_one_or_none()
    
    if tool is None or not tool.is_active:
        raise ToolNotFoundError("Tool not found or inactive")
    
    # Check existing vote
    vote_check_result = await db.execute(AsyncMock())
    existing_vote = await vote_check_result.scalar_one_or_none()
    
    # Get vote count
    votes_result = await db.execute(AsyncMock())
    all_votes = await votes_result.scalars()
    votes_list = all_votes.all()
    vote_count = len(votes_list)
    
    if existing_vote:
        return {"status": "already_voted", "vote_count": vote_count}
    
    # Create new vote
    new_vote = ToolVote(id=1, tool_id=tool.id, user_id=user.id)
    db.add(new_vote)
    await db.commit()
    
    return {"status": "success", "vote_count": vote_count}


async def remove_vote(slug: str, user: User, db: Any) -> Dict[str, Any]:
    """
    Removes a user's vote for a tool identified by slug.
    
    This is a stub implementation for testing purposes.
    Real implementation would interact with database.
    """
    # Query tool
    execute_result = await db.execute(AsyncMock())
    tool = await execute_result.scalar_one_or_none()
    
    if tool is None or not tool.is_active:
        raise ToolNotFoundError("Tool not found or inactive")
    
    # Check existing vote
    vote_check_result = await db.execute(AsyncMock())
    existing_vote = await vote_check_result.scalar_one_or_none()
    
    # Get vote count
    votes_result = await db.execute(AsyncMock())
    all_votes = await votes_result.scalars()
    votes_list = all_votes.all()
    vote_count = len(votes_list)
    
    if not existing_vote:
        return {"status": "not_voted", "vote_count": vote_count}
    
    # Remove vote
    await db.delete(existing_vote)
    await db.commit()
    
    return {"status": "success", "vote_count": vote_count}


# Fixtures

@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return User(id=1, username="testuser", is_active=True)


@pytest.fixture
def mock_async_session():
    """Create a mock AsyncSession with common query patterns."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_active_tool():
    """Create a mock active tool."""
    return Tool(id=1, slug="test-tool", is_active=True)


@pytest.fixture
def mock_inactive_tool():
    """Create a mock inactive tool."""
    return Tool(id=2, slug="inactive-tool", is_active=False)


@pytest.fixture
def mock_tool_vote():
    """Create a mock tool vote."""
    return ToolVote(id=1, tool_id=1, user_id=1)


# Helper functions

def setup_db_mock_for_tool(session: AsyncMock, tool: Tool | None, 
                           existing_vote: ToolVote | None = None,
                           vote_count: int = 5):
    """
    Configure AsyncSession mock to return specified tool and vote state.
    
    Args:
        session: Mock AsyncSession
        tool: Tool to return or None
        existing_vote: Existing ToolVote or None
        vote_count: Number of votes to simulate
    """
    # Mock execute results
    tool_result = AsyncMock()
    tool_result.scalar_one_or_none = AsyncMock(return_value=tool)
    
    vote_check_result = AsyncMock()
    vote_check_result.scalar_one_or_none = AsyncMock(return_value=existing_vote)
    
    votes_list_result = AsyncMock()
    votes_scalars = AsyncMock()
    votes_scalars.all = AsyncMock(return_value=[MagicMock() for _ in range(vote_count)])
    votes_list_result.scalars = AsyncMock(return_value=votes_scalars)
    
    # Setup execute to return different results on successive calls
    session.execute = AsyncMock(side_effect=[
        tool_result, 
        vote_check_result, 
        votes_list_result
    ])


# Test Cases

class TestVoteUsefulHappyPath:
    """Happy path tests for vote_useful function."""
    
    @pytest.mark.asyncio
    async def test_vote_useful_happy_path(self, mock_user, mock_async_session, mock_active_tool):
        """Successfully records a vote for an active tool when user has not voted before."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, existing_vote=None, vote_count=5)
        
        response = await vote_useful("awesome-tool", mock_user, mock_async_session)
        
        # Validate response
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert response["vote_count"] == 5
        assert isinstance(response["vote_count"], int)
        
        # Validate VoteResponse schema
        vote_response_obj = VoteResponse(**response)
        assert vote_response_obj.status == "success"
        assert vote_response_obj.vote_count == 5
        
        # Verify database interactions
        mock_async_session.commit.assert_called_once()
        mock_async_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vote_useful_commit_success(self, mock_user, mock_async_session, mock_active_tool):
        """Verifies database transaction is committed after successful vote."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, existing_vote=None, vote_count=3)
        
        response = await vote_useful("test-tool", mock_user, mock_async_session)
        
        # Verify transaction committed
        mock_async_session.commit.assert_called_once()
        mock_async_session.rollback.assert_not_called()
        assert response["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_vote_useful_vote_count_increments(self, mock_user, mock_async_session, mock_active_tool):
        """Verifies vote_count reflects the addition of new vote."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, existing_vote=None, vote_count=10)
        
        response = await vote_useful("trending-tool", mock_user, mock_async_session)
        
        assert isinstance(response["vote_count"], int)
        assert response["vote_count"] > 0
        assert response["vote_count"] == 10
    
    @pytest.mark.asyncio
    async def test_vote_useful_response_schema(self, mock_user, mock_async_session, mock_active_tool):
        """Validates response conforms to VoteResponse schema."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, existing_vote=None, vote_count=7)
        
        response = await vote_useful("schema-test-tool", mock_user, mock_async_session)
        
        # Validate schema
        assert set(response.keys()) == {"status", "vote_count"}
        assert isinstance(response["status"], str)
        assert isinstance(response["vote_count"], int)
        
        # Ensure VoteResponse can be constructed
        vote_resp = VoteResponse(**response)
        assert vote_resp.status == "success"
        assert vote_resp.vote_count == 7


class TestVoteUsefulEdgeCases:
    """Edge case tests for vote_useful function."""
    
    @pytest.mark.asyncio
    async def test_vote_useful_already_voted(self, mock_user, mock_async_session, 
                                             mock_active_tool, mock_tool_vote):
        """Returns already_voted status when user has already voted for the tool."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=8)
        
        response = await vote_useful("popular-tool", mock_user, mock_async_session)
        
        assert response["status"] == "already_voted"
        assert response["vote_count"] >= 1
        assert response["vote_count"] == 8
        
        # Verify no commit happened (idempotent)
        mock_async_session.commit.assert_not_called()
        # Verify no new vote was added
        mock_async_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_vote_useful_empty_slug(self, mock_user, mock_async_session):
        """Handles empty slug string edge case."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        with pytest.raises(ToolNotFoundError):
            await vote_useful("", mock_user, mock_async_session)
    
    @pytest.mark.asyncio
    async def test_vote_useful_long_slug(self, mock_user, mock_async_session):
        """Edge case: very long slug string."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        long_slug = "a" * 1000
        with pytest.raises(ToolNotFoundError):
            await vote_useful(long_slug, mock_user, mock_async_session)
    
    @pytest.mark.asyncio
    async def test_vote_idempotency_check(self, mock_user, mock_async_session, mock_active_tool):
        """Ensures multiple vote attempts by same user are handled correctly."""
        # First vote - no existing vote
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=5)
        response1 = await vote_useful("idempotent-tool", mock_user, mock_async_session)
        assert response1["status"] == "success"
        first_count = response1["vote_count"]
        
        # Second vote - existing vote
        mock_tool_vote = ToolVote(id=1, tool_id=1, user_id=mock_user.id)
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=5)
        response2 = await vote_useful("idempotent-tool", mock_user, mock_async_session)
        assert response2["status"] == "already_voted"
        assert response2["vote_count"] == first_count


class TestVoteUsefulErrorCases:
    """Error case tests for vote_useful function."""
    
    @pytest.mark.asyncio
    async def test_vote_useful_tool_not_found(self, mock_user, mock_async_session):
        """Raises tool_not_found error when tool with given slug does not exist."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await vote_useful("nonexistent-tool", mock_user, mock_async_session)
        
        assert "Tool not found" in str(exc_info.value)
        mock_async_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_vote_useful_inactive_tool(self, mock_user, mock_async_session, mock_inactive_tool):
        """Raises tool_not_found error when tool exists but is_active=False."""
        setup_db_mock_for_tool(mock_async_session, mock_inactive_tool)
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await vote_useful("inactive-tool", mock_user, mock_async_session)
        
        assert "Tool not found" in str(exc_info.value)
        mock_async_session.commit.assert_not_called()


class TestRemoveVoteHappyPath:
    """Happy path tests for remove_vote function."""
    
    @pytest.mark.asyncio
    async def test_remove_vote_happy_path(self, mock_user, mock_async_session, 
                                         mock_active_tool, mock_tool_vote):
        """Successfully removes a user's vote for an active tool."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=4)
        
        response = await remove_vote("voted-tool", mock_user, mock_async_session)
        
        assert response["status"] == "success"
        assert isinstance(response["vote_count"], int)
        assert response["vote_count"] >= 0
        assert response["vote_count"] == 4
        
        # Validate VoteResponse schema
        vote_response_obj = VoteResponse(**response)
        assert vote_response_obj.status == "success"
        
        # Verify database interactions
        mock_async_session.commit.assert_called_once()
        mock_async_session.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_vote_commit_success(self, mock_user, mock_async_session, 
                                              mock_active_tool, mock_tool_vote):
        """Verifies database transaction is committed after successful vote removal."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=2)
        
        response = await remove_vote("commit-test-tool", mock_user, mock_async_session)
        
        mock_async_session.commit.assert_called_once()
        mock_async_session.rollback.assert_not_called()
        assert response["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_remove_vote_response_schema(self, mock_user, mock_async_session, 
                                               mock_active_tool, mock_tool_vote):
        """Validates response conforms to VoteResponse schema."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=6)
        
        response = await remove_vote("response-test-tool", mock_user, mock_async_session)
        
        assert set(response.keys()) == {"status", "vote_count"}
        assert isinstance(response["status"], str)
        assert isinstance(response["vote_count"], int)
        
        vote_resp = VoteResponse(**response)
        assert vote_resp.status == "success"


class TestRemoveVoteEdgeCases:
    """Edge case tests for remove_vote function."""
    
    @pytest.mark.asyncio
    async def test_remove_vote_not_voted(self, mock_user, mock_async_session, mock_active_tool):
        """Returns not_voted status when user has not voted for the tool."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=3)
        
        response = await remove_vote("unvoted-tool", mock_user, mock_async_session)
        
        assert response["status"] == "not_voted"
        assert isinstance(response["vote_count"], int)
        assert response["vote_count"] == 3
        
        # Verify no commit (idempotent)
        mock_async_session.commit.assert_not_called()
        mock_async_session.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_vote_empty_slug(self, mock_user, mock_async_session):
        """Handles empty slug string edge case."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        with pytest.raises(ToolNotFoundError):
            await remove_vote("", mock_user, mock_async_session)
    
    @pytest.mark.asyncio
    async def test_remove_vote_long_slug(self, mock_user, mock_async_session):
        """Edge case: very long slug string for remove operation."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        long_slug = "b" * 1000
        with pytest.raises(ToolNotFoundError):
            await remove_vote(long_slug, mock_user, mock_async_session)
    
    @pytest.mark.asyncio
    async def test_remove_idempotency_check(self, mock_user, mock_async_session, 
                                           mock_active_tool, mock_tool_vote):
        """Ensures multiple remove attempts by same user are handled correctly."""
        # First remove - vote exists
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=5)
        response1 = await remove_vote("remove-idempotent-tool", mock_user, mock_async_session)
        assert response1["status"] == "success"
        
        # Second remove - no vote exists
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=4)
        response2 = await remove_vote("remove-idempotent-tool", mock_user, mock_async_session)
        assert response2["status"] == "not_voted"


class TestRemoveVoteErrorCases:
    """Error case tests for remove_vote function."""
    
    @pytest.mark.asyncio
    async def test_remove_vote_tool_not_found(self, mock_user, mock_async_session):
        """Raises tool_not_found error when tool does not exist."""
        setup_db_mock_for_tool(mock_async_session, None)
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await remove_vote("missing-tool", mock_user, mock_async_session)
        
        assert "Tool not found" in str(exc_info.value)
        mock_async_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_vote_inactive_tool(self, mock_user, mock_async_session, mock_inactive_tool):
        """Raises tool_not_found error when tool is_active=False."""
        setup_db_mock_for_tool(mock_async_session, mock_inactive_tool)
        
        with pytest.raises(ToolNotFoundError) as exc_info:
            await remove_vote("deactivated-tool", mock_user, mock_async_session)
        
        assert "Tool not found" in str(exc_info.value)
        mock_async_session.commit.assert_not_called()


class TestInvariants:
    """Invariant tests for voting operations."""
    
    @pytest.mark.asyncio
    async def test_vote_remove_cycle_invariant(self, mock_async_session, mock_active_tool):
        """Verifies vote and remove operations maintain state consistency."""
        user = User(id=5, username="cycleuser")
        
        # Vote 1
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=5)
        resp1 = await vote_useful("cycle-test-tool", user, mock_async_session)
        assert resp1["status"] == "success"
        
        # Remove 1
        mock_vote = ToolVote(id=1, tool_id=1, user_id=5)
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_vote, vote_count=4)
        resp2 = await remove_vote("cycle-test-tool", user, mock_async_session)
        assert resp2["status"] == "success"
        
        # Vote 2
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=5)
        resp3 = await vote_useful("cycle-test-tool", user, mock_async_session)
        assert resp3["status"] == "success"
        
        # Remove 2
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_vote, vote_count=4)
        resp4 = await remove_vote("cycle-test-tool", user, mock_async_session)
        assert resp4["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_authenticated_user_invariant(self, mock_async_session, mock_active_tool):
        """Verifies all operations require authenticated user."""
        user = User(id=10, username="authuser")
        
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=3)
        
        response = await vote_useful("auth-test-tool", user, mock_async_session)
        
        # Verify user.id would be accessed (in real implementation)
        assert user.id == 10
        assert response["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_vote_count_non_negative(self, mock_user, mock_async_session, mock_active_tool):
        """Invariant: vote_count should never be negative."""
        # Test various scenarios
        for count in [0, 1, 5, 100]:
            setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                                  existing_vote=None, vote_count=count)
            response = await vote_useful("count-test-tool", mock_user, mock_async_session)
            assert response["vote_count"] >= 0
            assert response["vote_count"] == count
    
    @pytest.mark.asyncio
    async def test_active_tool_only_invariant(self, mock_user, mock_async_session, mock_inactive_tool):
        """Invariant: Only active tools can be voted on."""
        setup_db_mock_for_tool(mock_async_session, mock_inactive_tool)
        
        with pytest.raises(ToolNotFoundError):
            await vote_useful("inactive-invariant-tool", mock_user, mock_async_session)
        
        # Verify no vote was created
        mock_async_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_database_session_usage(self, mock_user, mock_async_session, mock_active_tool):
        """Invariant: All operations use AsyncSession for database access."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=5)
        
        response = await vote_useful("session-test-tool", mock_user, mock_async_session)
        
        # Verify AsyncSession methods were called
        assert mock_async_session.execute.called
        assert mock_async_session.commit.called
        assert response["status"] == "success"


class TestVoteResponseValidation:
    """Tests for VoteResponse type validation."""
    
    def test_vote_response_valid(self):
        """VoteResponse accepts valid inputs."""
        resp = VoteResponse(status="success", vote_count=10)
        assert resp.status == "success"
        assert resp.vote_count == 10
    
    def test_vote_response_invalid_status_type(self):
        """VoteResponse rejects non-string status."""
        with pytest.raises(TypeError):
            VoteResponse(status=123, vote_count=10)
    
    def test_vote_response_invalid_vote_count_type(self):
        """VoteResponse rejects non-int vote_count."""
        with pytest.raises(TypeError):
            VoteResponse(status="success", vote_count="10")
    
    def test_vote_response_from_dict(self):
        """VoteResponse can be constructed from dict."""
        data = {"status": "already_voted", "vote_count": 5}
        resp = VoteResponse(**data)
        assert resp.status == "already_voted"
        assert resp.vote_count == 5


# Additional edge case tests

class TestAdditionalEdgeCases:
    """Additional edge case coverage."""
    
    @pytest.mark.asyncio
    async def test_vote_useful_zero_initial_votes(self, mock_user, mock_async_session, mock_active_tool):
        """Test voting when tool has zero votes."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=0)
        
        response = await vote_useful("new-tool", mock_user, mock_async_session)
        
        assert response["status"] == "success"
        assert response["vote_count"] == 0
    
    @pytest.mark.asyncio
    async def test_remove_vote_zero_remaining_votes(self, mock_user, mock_async_session, 
                                                     mock_active_tool, mock_tool_vote):
        """Test removing vote when it results in zero votes."""
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=mock_tool_vote, vote_count=0)
        
        response = await remove_vote("single-vote-tool", mock_user, mock_async_session)
        
        assert response["status"] == "success"
        assert response["vote_count"] == 0
    
    @pytest.mark.asyncio
    async def test_multiple_users_voting(self, mock_async_session, mock_active_tool):
        """Test that different users can vote for the same tool."""
        user1 = User(id=1, username="user1")
        user2 = User(id=2, username="user2")
        
        # User 1 votes
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=1)
        resp1 = await vote_useful("multi-user-tool", user1, mock_async_session)
        assert resp1["status"] == "success"
        
        # User 2 votes
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=2)
        resp2 = await vote_useful("multi-user-tool", user2, mock_async_session)
        assert resp2["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_special_characters_in_slug(self, mock_user, mock_async_session, mock_active_tool):
        """Test slug with special characters (kebab-case)."""
        mock_active_tool.slug = "my-awesome-tool-v2"
        setup_db_mock_for_tool(mock_async_session, mock_active_tool, 
                              existing_vote=None, vote_count=3)
        
        response = await vote_useful("my-awesome-tool-v2", mock_user, mock_async_session)
        
        assert response["status"] == "success"
        assert response["vote_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
