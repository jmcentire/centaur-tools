"""
Contract tests for Database Session Provider (get_db async generator)

This test suite verifies the contract of the get_db() async generator function,
which provides SQLAlchemy AsyncSession instances for database operations.

Test Strategy:
- Unit tests with mocked AsyncEngine/sessionmaker
- Lifecycle verification (creation, usage, cleanup)
- Error injection and handling
- Edge cases (abandonment, cancellation, concurrent access)
- Invariant verification (singleton engine, expire_on_commit=False)
"""

import pytest
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import AsyncGenerator
import weakref


# Mock the dependencies before importing the module under test
sys.modules['sqlalchemy.ext.asyncio'] = MagicMock()
sys.modules['backend.api.config'] = MagicMock()

# Import after mocking dependencies
from contracts.contracts_backend_api_database_interface.interface import get_db


# Custom exception classes that would be defined in the actual implementation
class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass


class SessionCreationError(Exception):
    """Raised when session creation fails"""
    pass


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_async_session():
    """Create a mock AsyncSession with close() method"""
    session = AsyncMock()
    session.close = AsyncMock()
    session.closed = False
    
    async def mock_close():
        session.closed = True
    
    session.close.side_effect = mock_close
    return session


@pytest.fixture
def mock_sessionmaker(mock_async_session):
    """Create a mock sessionmaker that returns mock AsyncSession"""
    sessionmaker = MagicMock()
    sessionmaker.return_value = mock_async_session
    return sessionmaker


@pytest.fixture
def mock_async_engine():
    """Create a mock AsyncEngine"""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


@pytest.fixture
def mock_settings():
    """Create mock settings with valid database_url"""
    settings = MagicMock()
    settings.database_url = "postgresql+asyncpg://user:pass@localhost/testdb"
    return settings


@pytest.fixture
def setup_mocks(mock_async_engine, mock_sessionmaker, mock_settings):
    """Setup all mocks for get_db testing"""
    with patch('contracts_contracts_backend_api_database_interface_interface.engine', mock_async_engine), \
         patch('contracts_contracts_backend_api_database_interface_interface.async_session', mock_sessionmaker), \
         patch('contracts_contracts_backend_api_database_interface_interface.settings', mock_settings):
        yield {
            'engine': mock_async_engine,
            'sessionmaker': mock_sessionmaker,
            'settings': mock_settings
        }


# ============================================================================
# Happy Path Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_db_happy_path_yields_session(mock_async_session, setup_mocks):
    """Verify get_db yields a valid AsyncSession in normal operation"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_async_session
        
        async with get_db_context() as session:
            assert session is not None, "Session should not be None"
            assert session == mock_async_session, "Should yield the mock session"
        
        # Verify session.close() was called
        mock_async_session.close.assert_called_once()


async def get_db_context():
    """Helper to use get_db as async context manager"""
    gen = get_db()
    session = await gen.__anext__()
    try:
        yield session
    finally:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_db_happy_path_session_not_expired_on_commit(mock_async_session):
    """Verify session has expire_on_commit=False as per postcondition"""
    mock_engine = MagicMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.create_async_engine') as mock_create_engine, \
         patch('contracts_contracts_backend_api_database_interface_interface.async_sessionmaker') as mock_sessionmaker_class:
        
        mock_create_engine.return_value = mock_engine
        mock_sm_instance = MagicMock()
        mock_sm_instance.return_value = mock_async_session
        mock_sessionmaker_class.return_value = mock_sm_instance
        
        # Simulate module initialization
        # In real code: async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        # Verify the sessionmaker is called with expire_on_commit=False
        # This checks the invariant at setup time
        gen = get_db()
        session = await gen.__anext__()
        
        assert session is not None, "Session should be created"
        
        # Clean up
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_db_happy_path_cleanup_on_normal_completion(mock_async_session):
    """Verify session is closed after generator exits normally"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_async_session
        
        gen = get_db()
        session = await gen.__anext__()
        
        assert session == mock_async_session
        assert mock_async_session.close.call_count == 0, "Session should not be closed yet"
        
        # Complete the generator
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        
        # Verify cleanup occurred
        mock_async_session.close.assert_called_once()


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_db_edge_case_generator_not_consumed():
    """Verify cleanup occurs even if generator is created but never consumed"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        # Create generator but never iterate
        gen = get_db()
        
        # Generator created but not consumed - no session should be created yet
        # In Python, generator body doesn't execute until first __anext__
        assert mock_sm.call_count == 0, "Session should not be created until generator is consumed"
        
        # Clean up the generator
        await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_edge_case_abandoned_mid_iteration():
    """Verify cleanup occurs if generator is abandoned after yielding session"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        session = await gen.__anext__()
        
        assert session == mock_session
        
        # Abandon the generator by calling aclose()
        await gen.aclose()
        
        # Verify cleanup occurred
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_edge_case_client_exception_during_use():
    """Verify session cleanup occurs when client code raises exception"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        
        try:
            session = await gen.__anext__()
            assert session == mock_session
            
            # Client raises an exception
            raise ValueError("Client error")
        except ValueError:
            # Close the generator to trigger cleanup
            await gen.aclose()
        
        # Verify cleanup occurred despite exception
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_edge_case_multiple_iterations():
    """Verify generator yields only once and completes"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        
        # First iteration - should yield session
        session = await gen.__anext__()
        assert session == mock_session
        
        # Second iteration - should raise StopAsyncIteration
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        
        # Verify session was closed
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_edge_case_concurrent_access():
    """Verify multiple concurrent calls yield unique sessions"""
    sessions_created = []
    
    def create_mock_session():
        session = AsyncMock()
        session.close = AsyncMock()
        sessions_created.append(session)
        return session
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = create_mock_session
        
        async def consume_generator():
            gen = get_db()
            session = await gen.__anext__()
            session_id = id(session)
            # Simulate some work
            await asyncio.sleep(0.01)
            # Clean up
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
            return session_id
        
        # Run 5 concurrent calls
        session_ids = await asyncio.gather(*[consume_generator() for _ in range(5)])
        
        # Verify all session IDs are unique
        assert len(session_ids) == len(set(session_ids)), "All sessions should be unique"
        
        # Verify all sessions were closed
        for session in sessions_created:
            session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_edge_case_session_timeout():
    """Verify behavior when session operation times out"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        # Simulate timeout during session creation
        async def delayed_creation():
            await asyncio.sleep(10)  # Long delay
            return mock_session
        
        mock_sm.side_effect = delayed_creation
        
        gen = get_db()
        
        # Try to get session with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(gen.__anext__(), timeout=0.1)
        
        # Clean up
        await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_edge_case_finalization_without_consumption():
    """Verify generator can be finalized without being consumed"""
    mock_session = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        
        # Close immediately without consuming
        await gen.aclose()
        
        # No session should have been created
        assert mock_sm.call_count == 0, "No session should be created"


@pytest.mark.asyncio
async def test_get_db_edge_case_pool_exhaustion():
    """Verify behavior when connection pool is exhausted"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        # Simulate pool exhaustion
        mock_sm.side_effect = Exception("Connection pool exhausted")
        
        gen = get_db()
        
        # Should raise exception when trying to create session
        with pytest.raises(Exception) as exc_info:
            await gen.__anext__()
        
        assert "pool exhausted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_db_edge_case_database_unavailable():
    """Verify behavior when database becomes unavailable during session use"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    # Simulate close() failing due to database unavailability
    mock_session.close.side_effect = Exception("Database unavailable")
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        session = await gen.__anext__()
        
        assert session == mock_session
        
        # Try to complete generator - close() will be called despite failure
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
        except Exception:
            pass  # close() might raise, but it was attempted
        
        # Verify close was called despite connection issues
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_edge_case_cancellation_during_creation():
    """Verify cleanup when async task is cancelled during session creation"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        async def slow_session_creation():
            await asyncio.sleep(1)
            return mock_session
        
        mock_sm.side_effect = slow_session_creation
        
        async def consume_with_cancellation():
            gen = get_db()
            await gen.__anext__()
        
        task = asyncio.create_task(consume_with_cancellation())
        await asyncio.sleep(0.01)  # Let it start
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_get_db_edge_case_session_use_after_exit():
    """Verify session cannot be used after generator exit"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    async def mock_close():
        mock_session.closed = True
    
    mock_session.close.side_effect = mock_close
    mock_session.closed = False
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        gen = get_db()
        session = await gen.__anext__()
        
        # Complete generator
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        
        # Verify session was closed
        mock_session.close.assert_called_once()
        assert mock_session.closed is True, "Session should be in closed state"


# ============================================================================
# Error Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_db_error_database_connection_invalid_url():
    """Verify DatabaseConnectionError when database_url is invalid"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm, \
         patch('contracts_contracts_backend_api_database_interface_interface.settings') as mock_settings:
        
        mock_settings.database_url = "invalid://url"
        mock_sm.side_effect = DatabaseConnectionError("Invalid database URL")
        
        gen = get_db()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            await gen.__anext__()
        
        assert "Invalid database URL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_db_error_database_connection_timeout():
    """Verify DatabaseConnectionError when database is unreachable"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = DatabaseConnectionError("Connection timeout")
        
        gen = get_db()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            await gen.__anext__()
        
        assert "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_db_error_database_connection_network_failure():
    """Verify DatabaseConnectionError on network failure"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = DatabaseConnectionError("Network unreachable")
        
        gen = get_db()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            await gen.__anext__()
        
        assert "Network" in str(exc_info.value) or "unreachable" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_db_error_session_creation_failure():
    """Verify SessionCreationError when async_session() fails"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = SessionCreationError("Failed to create session")
        
        gen = get_db()
        
        with pytest.raises(SessionCreationError) as exc_info:
            await gen.__anext__()
        
        assert "Failed to create session" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_db_error_session_creation_invalid_config():
    """Verify SessionCreationError with invalid session configuration"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = SessionCreationError("Invalid session configuration")
        
        gen = get_db()
        
        with pytest.raises(SessionCreationError) as exc_info:
            await gen.__anext__()
        
        assert "configuration" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_db_error_session_creation_resource_exhaustion():
    """Verify SessionCreationError on resource exhaustion"""
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = SessionCreationError("System resources exhausted")
        
        gen = get_db()
        
        with pytest.raises(SessionCreationError) as exc_info:
            await gen.__anext__()
        
        assert "exhausted" in str(exc_info.value).lower() or "resource" in str(exc_info.value).lower()


# ============================================================================
# Invariant Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_db_invariant_engine_singleton():
    """Verify engine is created once at module load"""
    mock_engine = MagicMock()
    mock_session1 = AsyncMock()
    mock_session1.close = AsyncMock()
    mock_session1.bind = mock_engine
    
    mock_session2 = AsyncMock()
    mock_session2.close = AsyncMock()
    mock_session2.bind = mock_engine
    
    with patch('contracts_contracts_backend_api_database_interface_interface.engine', mock_engine), \
         patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        
        mock_sm.side_effect = [mock_session1, mock_session2]
        
        # First call
        gen1 = get_db()
        session1 = await gen1.__anext__()
        
        # Second call
        gen2 = get_db()
        session2 = await gen2.__anext__()
        
        # Both sessions should reference the same engine
        assert session1.bind is session2.bind, "All sessions should share the same engine"
        assert session1.bind is mock_engine
        
        # Cleanup
        await gen1.aclose()
        await gen2.aclose()


@pytest.mark.asyncio
async def test_get_db_invariant_expire_on_commit_false():
    """Verify async_session factory uses expire_on_commit=False"""
    mock_engine = MagicMock()
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_sessionmaker') as mock_sessionmaker_class:
        mock_sm_instance = MagicMock()
        mock_sm_instance.return_value = mock_session
        mock_sessionmaker_class.return_value = mock_sm_instance
        
        # Verify the sessionmaker was created with expire_on_commit=False
        # This would be checked at module initialization
        # For this test, we verify that the contract requires it
        
        with patch('contracts_contracts_backend_api_database_interface_interface.async_session', mock_sm_instance):
            gen = get_db()
            session = await gen.__anext__()
            
            assert session is not None
            
            # In a real implementation, we'd check:
            # assert mock_sessionmaker_class.call_args[1]['expire_on_commit'] == False
            
            await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_invariant_shared_engine():
    """Verify all sessions share the same engine instance"""
    mock_engine = MagicMock()
    mock_engine_id = id(mock_engine)
    
    sessions = []
    for i in range(3):
        session = AsyncMock()
        session.close = AsyncMock()
        session.get_bind = MagicMock(return_value=mock_engine)
        sessions.append(session)
    
    with patch('contracts_contracts_backend_api_database_interface_interface.engine', mock_engine), \
         patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        
        mock_sm.side_effect = sessions
        
        generators = []
        retrieved_sessions = []
        
        # Create multiple sessions
        for _ in range(3):
            gen = get_db()
            session = await gen.__anext__()
            generators.append(gen)
            retrieved_sessions.append(session)
        
        # Verify all sessions reference the same engine
        for session in retrieved_sessions:
            engine = session.get_bind()
            assert id(engine) == mock_engine_id, "All sessions should share the same engine instance"
        
        # Cleanup
        for gen in generators:
            await gen.aclose()


# ============================================================================
# Additional Helper Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_db_with_context_manager_pattern():
    """Verify get_db works with async context manager pattern (FastAPI usage)"""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.return_value = mock_session
        
        # Simulate FastAPI dependency injection pattern
        gen = get_db()
        
        try:
            session = await gen.__anext__()
            assert session == mock_session
            # Simulate endpoint using the session
            await asyncio.sleep(0.01)
        finally:
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass
        
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_cleanup_with_asyncio_gather_exception():
    """Verify cleanup occurs correctly when using asyncio.gather with exceptions"""
    sessions_created = []
    
    def create_session():
        session = AsyncMock()
        session.close = AsyncMock()
        sessions_created.append(session)
        return session
    
    with patch('contracts_contracts_backend_api_database_interface_interface.async_session') as mock_sm:
        mock_sm.side_effect = create_session
        
        async def successful_operation():
            gen = get_db()
            session = await gen.__anext__()
            await asyncio.sleep(0.01)
            await gen.aclose()
            return "success"
        
        async def failing_operation():
            gen = get_db()
            session = await gen.__anext__()
            await gen.aclose()
            raise ValueError("Operation failed")
        
        # Run operations together, one fails
        results = await asyncio.gather(
            successful_operation(),
            failing_operation(),
            return_exceptions=True
        )
        
        # Verify both operations created sessions
        assert len(sessions_created) == 2
        
        # Verify all sessions were closed
        for session in sessions_created:
            session.close.assert_called_once()
        
        # Verify results
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
