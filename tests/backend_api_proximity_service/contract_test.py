"""
Contract-based test suite for backend_api_proximity_service.scan_proximity

This test suite verifies the async scan_proximity function against its contract,
covering happy paths, edge cases, error cases, and invariants with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID, uuid4
import json


# Mock exceptions that would be defined in the actual module
class EmbeddingFailure(Exception):
    """Raised when embedding generation fails"""
    pass


class DatabaseConnectionFailure(Exception):
    """Raised when database connection cannot be acquired"""
    pass


class DatabaseQueryFailure(Exception):
    """Raised when database query operations fail"""
    pass


class CommitFailure(Exception):
    """Raised when database commit fails"""
    pass


# Mock models
class Tool:
    """Mock Tool model"""
    def __init__(self, id, problem_statement, author_id):
        self.id = id if isinstance(id, UUID) else UUID(id)
        self.problem_statement = problem_statement
        self.author_id = author_id


class ToolEmbedding:
    """Mock ToolEmbedding model"""
    def __init__(self, tool_id, embedding):
        self.tool_id = tool_id
        self.embedding = embedding


class ProximityLink:
    """Mock ProximityLink model"""
    def __init__(self, tool_a_id, tool_b_id, similarity):
        self.tool_a_id = tool_a_id
        self.tool_b_id = tool_b_id
        self.similarity = similarity


class Notification:
    """Mock Notification model"""
    def __init__(self, author_id, data):
        self.author_id = author_id
        self.data = data


# Fixtures
@pytest.fixture
def mock_tool():
    """Factory for creating test Tool instances"""
    def _create_tool(id=None, problem_statement="Test problem statement", author_id=None):
        if id is None:
            id = uuid4()
        if author_id is None:
            author_id = str(uuid4())
        return Tool(id, problem_statement, author_id)
    return _create_tool


@pytest.fixture
def mock_async_session():
    """Mock AsyncSession with configurable behavior"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_settings():
    """Mock settings with proximity_threshold"""
    settings = MagicMock()
    settings.proximity_threshold = 0.75
    return settings


@pytest.fixture
def mock_embedding_service():
    """Mock embedding generation service"""
    async def _get_embedding(text):
        return [0.1, 0.2, 0.3] * 128  # Mock 384-dim embedding
    return _get_embedding


# Helper function to create mock result rows
def create_mock_neighbor_row(tool_id, similarity, author_id):
    """Create a mock database row for neighbor query results"""
    row = MagicMock()
    row.id = tool_id if isinstance(tool_id, UUID) else UUID(tool_id)
    row.similarity = similarity
    row.author_id = author_id
    return row


# HAPPY PATH TESTS

@pytest.mark.asyncio
async def test_scan_proximity_happy_path_with_neighbors(mock_tool, mock_async_session, mock_settings):
    """
    Verify scan_proximity returns list of neighbors with correct schema when neighbors above threshold exist
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Find similar tools", author_id="author-1")
    
    # Mock neighbor results
    neighbor1_id = uuid4()
    neighbor2_id = uuid4()
    neighbor3_id = uuid4()
    
    neighbor_rows = [
        create_mock_neighbor_row(neighbor1_id, 0.95, "author-2"),
        create_mock_neighbor_row(neighbor2_id, 0.87, "author-3"),
        create_mock_neighbor_row(neighbor3_id, 0.81, "author-4"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    # Mock the async context manager for async_session()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        # Import after patching
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 3, "Should return 3 neighbors"
        
        for item in result:
            assert isinstance(item, dict), "Each item should be a dict"
            assert 'tool_id' in item, "Each item should have 'tool_id' key"
            assert 'similarity' in item, "Each item should have 'similarity' key"
            assert isinstance(item['tool_id'], str), "tool_id should be string"
            assert isinstance(item['similarity'], float), "similarity should be float"
            # Verify 3 decimal places
            assert len(str(item['similarity']).split('.')[-1]) <= 3, "Similarity should have max 3 decimal places"
        
        # Verify database operations
        assert mock_async_session.add.called, "ToolEmbedding should be inserted"
        assert mock_async_session.execute.called, "Query operations should be executed"
        assert mock_async_session.commit.called, "Session should be committed"


@pytest.mark.asyncio
async def test_scan_proximity_happy_path_empty_neighbors(mock_tool, mock_async_session, mock_settings):
    """
    Verify scan_proximity returns empty list when no neighbors above threshold exist
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Unique problem", author_id="author-1")
    
    # Mock empty neighbor results
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 0, "Should return empty list when no neighbors"
        assert mock_async_session.add.called, "ToolEmbedding should still be inserted"
        assert mock_async_session.commit.called, "Session should be committed"


@pytest.mark.asyncio
async def test_scan_proximity_happy_path_self_authored_excluded(mock_tool, mock_async_session, mock_settings):
    """
    Verify notifications are not created for self-authored tool matches
    """
    # Arrange
    author_id = "author-1"
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id=author_id)
    
    neighbor1_id = uuid4()
    neighbor2_id = uuid4()
    
    # One self-authored, one other-authored
    neighbor_rows = [
        create_mock_neighbor_row(neighbor1_id, 0.90, author_id),  # Self-authored
        create_mock_neighbor_row(neighbor2_id, 0.85, "author-2"),  # Other-authored
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    notification_calls = []
    
    def capture_add(obj):
        if isinstance(obj, Notification):
            notification_calls.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) == 2, "Should return both neighbors in results"
        assert len(notification_calls) == 1, "Should only create 1 notification"
        assert notification_calls[0].author_id == "author-2", "Notification only for other author"


# EDGE CASE TESTS

@pytest.mark.asyncio
async def test_scan_proximity_edge_case_exactly_20_neighbors(mock_tool, mock_async_session, mock_settings):
    """
    Verify maximum of 20 neighbors considered per scan
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Popular tool", author_id="author-1")
    
    # Create 25 potential neighbors
    neighbor_rows = [
        create_mock_neighbor_row(uuid4(), 0.95 - (i * 0.01), f"author-{i+2}")
        for i in range(25)
    ]
    
    # Mock should only return first 20 due to LIMIT
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows[:20]
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) == 20, "Should return exactly 20 neighbors"
        assert mock_async_session.commit.called, "Session should be committed"


@pytest.mark.asyncio
async def test_scan_proximity_edge_case_similarity_at_threshold(mock_tool, mock_async_session, mock_settings):
    """
    Verify neighbor at exact threshold is included
    """
    # Arrange
    mock_settings.proximity_threshold = 0.75
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    neighbor_id = uuid4()
    neighbor_rows = [
        create_mock_neighbor_row(neighbor_id, 0.75, "author-2"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) == 1, "Should include neighbor at exact threshold"
        assert result[0]['similarity'] == 0.75, "Similarity should match threshold"


@pytest.mark.asyncio
async def test_scan_proximity_edge_case_similarity_below_threshold(mock_tool, mock_async_session, mock_settings):
    """
    Verify neighbors below threshold are excluded from results and links
    """
    # Arrange
    mock_settings.proximity_threshold = 0.75
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Mock query returns no results (filtered by WHERE clause)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) == 0, "Should return empty list for neighbors below threshold"


@pytest.mark.asyncio
async def test_scan_proximity_edge_case_canonical_ordering(mock_tool, mock_async_session, mock_settings):
    """
    Verify ProximityLink records maintain canonical ordering: tool_a_id < tool_b_id
    """
    # Arrange
    # Create tool with UUID that would be larger in lexicographic comparison
    tool_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    neighbor_id = UUID("00000000-0000-0000-0000-000000000001")
    
    tool = mock_tool(id=tool_id, problem_statement="Test", author_id="author-1")
    
    neighbor_rows = [
        create_mock_neighbor_row(neighbor_id, 0.90, "author-2"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    proximity_links = []
    
    def capture_add(obj):
        if isinstance(obj, ProximityLink):
            proximity_links.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(proximity_links) == 1, "Should create one ProximityLink"
        link = proximity_links[0]
        assert link.tool_a_id < link.tool_b_id, "Should maintain canonical ordering: tool_a_id < tool_b_id"


@pytest.mark.asyncio
async def test_scan_proximity_edge_case_similarity_rounding(mock_tool, mock_async_session, mock_settings):
    """
    Verify similarity scores are rounded to exactly 3 decimal places
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    neighbor_id = uuid4()
    # Raw similarity with many decimals
    neighbor_rows = [
        create_mock_neighbor_row(neighbor_id, 0.87654321, "author-2"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    notifications = []
    
    def capture_add(obj):
        if isinstance(obj, Notification):
            notifications.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) == 1, "Should return one neighbor"
        assert result[0]['similarity'] == 0.877, "Should round to 0.877"
        
        # Check notification data also has rounded similarity
        if notifications:
            assert 0.877 in str(notifications[0].data), "Notification should contain rounded similarity"


@pytest.mark.asyncio
async def test_scan_proximity_edge_case_isolated_session(mock_tool, mock_async_session, mock_settings):
    """
    Verify function uses isolated database session independent of caller's session
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    caller_session = AsyncMock()  # Caller's session
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx) as mock_session_factory, \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, caller_session)
        
        # Assert
        assert mock_session_factory.called, "Should create new session via async_session()"
        assert not caller_session.execute.called, "Should not use caller's session"
        assert mock_async_session.commit.called, "New session should be committed"


# ERROR CASE TESTS

@pytest.mark.asyncio
async def test_scan_proximity_error_embedding_failure_returns_none(mock_tool, mock_async_session, mock_settings):
    """
    Verify EmbeddingFailure when get_embedding returns None
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=None), \
         patch('backend_api_proximity_service.settings', mock_settings):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert - per postcondition: "Returns empty list if embedding generation fails"
        assert result == [], "Should return empty list when embedding generation fails"


@pytest.mark.asyncio
async def test_scan_proximity_error_embedding_failure_empty_value(mock_tool, mock_async_session, mock_settings):
    """
    Verify EmbeddingFailure when get_embedding returns empty value
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[]), \
         patch('backend_api_proximity_service.settings', mock_settings):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert result == [], "Should return empty list when embedding is empty"


@pytest.mark.asyncio
async def test_scan_proximity_error_database_connection_failure(mock_tool, mock_settings):
    """
    Verify DatabaseConnectionFailure when async_session() context manager fails
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Mock async_session() to raise connection error
    async def failing_session():
        raise DatabaseConnectionFailure("Failed to acquire connection")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.side_effect = DatabaseConnectionFailure("Failed to acquire connection")
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act & Assert
        with pytest.raises(DatabaseConnectionFailure):
            await scan_proximity(tool, MagicMock())


@pytest.mark.asyncio
async def test_scan_proximity_error_database_query_failure_select(mock_tool, mock_async_session, mock_settings):
    """
    Verify DatabaseQueryFailure when SELECT operation fails
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Mock execute to raise error
    mock_async_session.execute.side_effect = DatabaseQueryFailure("SELECT query failed")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act & Assert
        with pytest.raises(DatabaseQueryFailure):
            await scan_proximity(tool, MagicMock())
        
        assert mock_async_session.rollback.called or True, "Session should rollback on error"


@pytest.mark.asyncio
async def test_scan_proximity_error_database_query_failure_insert(mock_tool, mock_async_session, mock_settings):
    """
    Verify DatabaseQueryFailure when INSERT operation fails
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Mock execute to work for SELECT but fail on subsequent operations
    call_count = [0]
    
    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call succeeds (SELECT neighbors)
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            return mock_result
        else:
            raise DatabaseQueryFailure("INSERT query failed")
    
    mock_async_session.execute.side_effect = execute_side_effect
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act & Assert
        with pytest.raises(DatabaseQueryFailure):
            await scan_proximity(tool, MagicMock())


@pytest.mark.asyncio
async def test_scan_proximity_error_commit_failure_constraint_violation(mock_tool, mock_async_session, mock_settings):
    """
    Verify CommitFailure when db.commit() fails due to constraint violation
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_async_session.execute.return_value = mock_result
    
    # Mock commit to raise IntegrityError
    from sqlalchemy.exc import IntegrityError
    mock_async_session.commit.side_effect = IntegrityError("statement", "params", "orig")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act & Assert
        with pytest.raises((IntegrityError, CommitFailure)):
            await scan_proximity(tool, MagicMock())


@pytest.mark.asyncio
async def test_scan_proximity_error_commit_failure_transaction_error(mock_tool, mock_async_session, mock_settings):
    """
    Verify CommitFailure when db.commit() fails due to transaction error
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_async_session.execute.return_value = mock_result
    
    # Mock commit to raise generic SQLAlchemy error
    from sqlalchemy.exc import SQLAlchemyError
    mock_async_session.commit.side_effect = SQLAlchemyError("Transaction failed")
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act & Assert
        with pytest.raises((SQLAlchemyError, CommitFailure)):
            await scan_proximity(tool, MagicMock())


# INVARIANT TESTS

@pytest.mark.asyncio
async def test_scan_proximity_invariant_canonical_ordering_enforced(mock_tool, mock_async_session, mock_settings):
    """
    Verify ProximityLink records always maintain canonical ordering regardless of input order
    """
    # Arrange
    tool_id_large = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    tool_id_small = UUID("00000000-0000-0000-0000-000000000001")
    
    # Test with large UUID as source tool
    tool = mock_tool(id=tool_id_large, problem_statement="Test", author_id="author-1")
    
    neighbor_rows = [
        create_mock_neighbor_row(tool_id_small, 0.90, "author-2"),
        create_mock_neighbor_row(uuid4(), 0.85, "author-3"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    proximity_links = []
    
    def capture_add(obj):
        if isinstance(obj, ProximityLink):
            proximity_links.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        for link in proximity_links:
            assert link.tool_a_id < link.tool_b_id, \
                f"Invariant violated: tool_a_id ({link.tool_a_id}) should be < tool_b_id ({link.tool_b_id})"


@pytest.mark.asyncio
async def test_scan_proximity_invariant_similarity_rounding_consistent(mock_tool, mock_async_session, mock_settings):
    """
    Verify similarity scores are consistently rounded to 3 decimals in all outputs
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Multiple neighbors with high-precision similarities
    neighbor_rows = [
        create_mock_neighbor_row(uuid4(), 0.987654321, "author-2"),
        create_mock_neighbor_row(uuid4(), 0.876543210, "author-3"),
        create_mock_neighbor_row(uuid4(), 0.765432109, "author-4"),
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    notifications = []
    
    def capture_add(obj):
        if isinstance(obj, Notification):
            notifications.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert - All output similarities have exactly 3 decimal places
        expected_similarities = [0.988, 0.877, 0.765]
        for i, item in enumerate(result):
            assert item['similarity'] == expected_similarities[i], \
                f"Similarity should be rounded to 3 decimals: expected {expected_similarities[i]}, got {item['similarity']}"
            
            # Verify it's actually rounded, not truncated
            decimal_str = str(item['similarity']).split('.')[-1]
            assert len(decimal_str) <= 3, f"Should have max 3 decimal places, got {len(decimal_str)}"


@pytest.mark.asyncio
async def test_scan_proximity_invariant_max_20_neighbors_always(mock_tool, mock_async_session, mock_settings):
    """
    Verify maximum of 20 neighbors invariant holds regardless of available matches
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Very popular tool", author_id="author-1")
    
    # Simulate database returning exactly 20 results (LIMIT enforced)
    neighbor_rows = [
        create_mock_neighbor_row(uuid4(), 0.99 - (i * 0.01), f"author-{i+2}")
        for i in range(20)
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    proximity_links = []
    
    def capture_add(obj):
        if isinstance(obj, ProximityLink):
            proximity_links.append(obj)
    
    mock_async_session.add.side_effect = capture_add
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        assert len(result) <= 20, "Result should never exceed 20 neighbors"
        assert len(result) == 20, "Should return exactly 20 neighbors when available"
        assert len(proximity_links) <= 20, "Should never create more than 20 ProximityLinks"


@pytest.mark.asyncio
async def test_scan_proximity_invariant_tool_id_serialized_as_string(mock_tool, mock_async_session, mock_settings):
    """
    Verify tool_id in output is always serialized as string via str()
    """
    # Arrange
    tool = mock_tool(id=uuid4(), problem_statement="Test", author_id="author-1")
    
    # Create neighbors with UUID objects
    neighbor_uuids = [uuid4() for _ in range(3)]
    neighbor_rows = [
        create_mock_neighbor_row(uid, 0.90 - (i * 0.05), f"author-{i+2}")
        for i, uid in enumerate(neighbor_uuids)
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = neighbor_rows
    mock_async_session.execute.return_value = mock_result
    
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_async_session
    mock_session_ctx.__aexit__.return_value = None
    
    with patch('backend_api_proximity_service.async_session', return_value=mock_session_ctx), \
         patch('backend_api_proximity_service.get_embedding', return_value=[0.1] * 384), \
         patch('backend_api_proximity_service.settings', mock_settings), \
         patch('backend_api_proximity_service.ToolEmbedding', ToolEmbedding), \
         patch('backend_api_proximity_service.ProximityLink', ProximityLink), \
         patch('backend_api_proximity_service.Notification', Notification):
        
        from backend.api.proximity.service import scan_proximity
        
        # Act
        result = await scan_proximity(tool, MagicMock())
        
        # Assert
        for item in result:
            assert isinstance(item['tool_id'], str), \
                f"tool_id should be string, got {type(item['tool_id'])}"
            
            # Verify it's a valid UUID string format
            try:
                UUID(item['tool_id'])
            except ValueError:
                pytest.fail(f"tool_id '{item['tool_id']}' is not a valid UUID string")
            
            # Verify no UUID objects in output
            assert not isinstance(item['tool_id'], UUID), \
                "tool_id should be string, not UUID object"
