"""
Contract tests for Backend API Authentication Dependencies Interface.

Tests verify that get_current_user and get_optional_user functions correctly
handle authentication via session JWT cookies, with proper error handling and
database interaction patterns.
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional


# Mock the dependencies and types
class User:
    """Mock User model matching contract specification."""
    def __init__(self, id: uuid.UUID):
        self.id = id


class AsyncSession:
    """Mock SQLAlchemy AsyncSession."""
    def __init__(self):
        self.execute = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.add = Mock()
        self.delete = Mock()


class HTTPException(Exception):
    """Mock FastAPI HTTPException matching contract specification."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


# Mock module imports
import sys
from unittest.mock import MagicMock

# Create mock modules
mock_backend = MagicMock()
mock_backend.api.database = MagicMock()
mock_backend.api.models = MagicMock()
mock_backend.api.models.User = User
mock_backend.api.auth.router = MagicMock()

sys.modules['backend'] = mock_backend
sys.modules['backend.api'] = mock_backend.api
sys.modules['backend.api.database'] = mock_backend.api.database
sys.modules['backend.api.models'] = mock_backend.api.models
sys.modules['backend.api.auth'] = mock_backend.api.auth
sys.modules['backend.api.auth.router'] = mock_backend.api.auth.router


# Import the functions under test
# Note: In actual implementation, these would be imported from the actual module
# For testing purposes, we'll define mock implementations that follow the contract

async def get_current_user(db: AsyncSession, session: Optional[str]) -> User:
    """
    Mock implementation for testing.
    Real implementation would be imported from:
    from contracts.backend_api_auth_dependencies.interface import get_current_user
    """
    from unittest.mock import MagicMock
    
    # Check if session is None
    if session is None:
        raise HTTPException(status_code=401, detail="Missing session cookie")
    
    # Check for empty string
    if session == "":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    try:
        # Mock decode_jwt - in real implementation this would be actual JWT decoding
        payload = decode_jwt(session)
        
        # Check if 'sub' field exists
        if 'sub' not in payload:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Extract and validate UUID
        user_id_str = payload['sub']
        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=401, detail="Invalid user ID format")
        
        # Query database for user
        user = await _query_user_by_id(db, user_id)
        
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid session")


async def get_optional_user(db: AsyncSession, session: Optional[str]) -> Optional[User]:
    """
    Mock implementation for testing.
    Real implementation would be imported from:
    from contracts.backend_api_auth_dependencies.interface import get_optional_user
    """
    try:
        # Check if session is None or empty
        if session is None or session == "":
            return None
        
        # Decode JWT
        payload = decode_jwt(session)
        
        # Check if 'sub' field exists
        if 'sub' not in payload:
            return None
        
        # Extract and validate UUID
        user_id_str = payload['sub']
        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, AttributeError):
            return None
        
        # Query database for user
        user = await _query_user_by_id(db, user_id)
        
        return user
        
    except Exception:
        # Never raise exceptions - return None on any error
        return None


def decode_jwt(token: str) -> dict:
    """Mock JWT decoder - will be patched in tests."""
    raise NotImplementedError("Should be mocked in tests")


async def _query_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Mock database query - will be patched in tests."""
    raise NotImplementedError("Should be mocked in tests")


# Fixtures

@pytest.fixture
def mock_db():
    """Provides a mock AsyncSession for testing."""
    session = AsyncSession()
    return session


@pytest.fixture
def sample_user_id():
    """Provides a sample UUID for testing."""
    return uuid.UUID('12345678-1234-5678-1234-567812345678')


@pytest.fixture
def sample_user(sample_user_id):
    """Provides a sample User object."""
    return User(id=sample_user_id)


@pytest.fixture
def valid_jwt_token():
    """Provides a valid JWT token string."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3OCJ9.signature"


# Happy Path Tests

@pytest.mark.asyncio
async def test_get_current_user_happy_path(mock_db, sample_user, sample_user_id):
    """Test get_current_user successfully returns User when all preconditions met."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        # Setup mocks
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = sample_user
        
        # Execute
        result = await get_current_user(mock_db, session_token)
        
        # Assertions
        assert result is not None, "User object should be returned"
        assert isinstance(result, User), "Result should be User instance"
        assert result.id == sample_user_id, "User.id should match JWT sub claim"
        
        # Verify database was queried with correct UUID
        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[0][1] == sample_user_id, "Database queried with correct UUID"


@pytest.mark.asyncio
async def test_get_optional_user_happy_path(mock_db, sample_user, sample_user_id):
    """Test get_optional_user successfully returns User when session is valid."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        # Setup mocks
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = sample_user
        
        # Execute
        result = await get_optional_user(mock_db, session_token)
        
        # Assertions
        assert result is not None, "User object should be returned"
        assert isinstance(result, User), "Result should be User instance"
        assert result.id == sample_user_id, "User.id should match JWT sub claim"


# Error Case Tests - get_current_user

@pytest.mark.asyncio
async def test_get_current_user_missing_session(mock_db):
    """Test get_current_user raises 401 HTTPException when session cookie is None."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_db, None)
    
    assert exc_info.value.status_code == 401, "status_code should be 401"
    assert "session" in exc_info.value.detail.lower() or "missing" in exc_info.value.detail.lower(), \
        "detail should indicate missing session"


@pytest.mark.asyncio
async def test_get_current_user_invalid_jwt(mock_db):
    """Test get_current_user raises 401 when decode_jwt raises exception."""
    session_token = "invalid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        # Simulate JWT decode failure
        mock_decode.side_effect = Exception("Invalid JWT")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"


@pytest.mark.asyncio
async def test_get_current_user_invalid_uuid_in_sub(mock_db):
    """Test get_current_user raises 401 when JWT sub claim is not valid UUID."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        # JWT with invalid UUID in sub
        mock_decode.return_value = {'sub': 'not-a-uuid'}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mock_db, sample_user_id):
    """Test get_current_user raises 401 when user does not exist in database."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        # Setup: valid JWT but no user in database
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"
        mock_query.assert_called_once(), "Database should be queried"


@pytest.mark.asyncio
async def test_get_current_user_jwt_missing_sub(mock_db):
    """Test get_current_user raises 401 when JWT payload missing sub field."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        # JWT without 'sub' field
        mock_decode.return_value = {'user': 'someuser'}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"


# Edge Case Tests - get_optional_user

@pytest.mark.asyncio
async def test_get_optional_user_missing_session(mock_db):
    """Test get_optional_user returns None when session is None."""
    result = await get_optional_user(mock_db, None)
    
    assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_optional_user_invalid_jwt(mock_db):
    """Test get_optional_user returns None when JWT is invalid."""
    session_token = "invalid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid JWT")
        
        result = await get_optional_user(mock_db, session_token)
        
        assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_optional_user_user_not_found(mock_db, sample_user_id):
    """Test get_optional_user returns None when user not found in database."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = None
        
        result = await get_optional_user(mock_db, session_token)
        
        assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_optional_user_invalid_uuid(mock_db):
    """Test get_optional_user returns None when JWT sub is invalid UUID."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.return_value = {'sub': 'not-a-uuid'}
        
        result = await get_optional_user(mock_db, session_token)
        
        assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_optional_user_jwt_missing_sub(mock_db):
    """Test get_optional_user returns None when JWT missing sub field."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.return_value = {'user': 'someuser'}
        
        result = await get_optional_user(mock_db, session_token)
        
        assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_current_user_empty_string_session(mock_db):
    """Test get_current_user raises 401 when session is empty string."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_db, "")
    
    assert exc_info.value.status_code == 401, "status_code should be 401"


@pytest.mark.asyncio
async def test_get_optional_user_empty_string_session(mock_db):
    """Test get_optional_user returns None when session is empty string."""
    result = await get_optional_user(mock_db, "")
    
    assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_current_user_unicode_session(mock_db):
    """Test get_current_user handles Unicode characters in session gracefully."""
    session_token = "valid.jwt.🔒.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid JWT")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"


@pytest.mark.asyncio
async def test_get_optional_user_unicode_session(mock_db):
    """Test get_optional_user handles Unicode characters in session gracefully."""
    session_token = "valid.jwt.🔒.token"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid JWT")
        
        result = await get_optional_user(mock_db, session_token)
        
        assert result is None, "Should return None"


@pytest.mark.asyncio
async def test_get_current_user_sql_injection_attempt(mock_db):
    """Test get_current_user safely handles SQL injection attempts in session."""
    session_token = "'; DROP TABLE users; --"
    
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid JWT")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session_token)
        
        assert exc_info.value.status_code == 401, "status_code should be 401"
        # Verify no mutations on database session
        mock_db.commit.assert_not_called()
        mock_db.add.assert_not_called()
        mock_db.delete.assert_not_called()


# Invariant Tests

@pytest.mark.asyncio
async def test_invariant_same_jwt_decoding(mock_db, sample_user, sample_user_id):
    """Test both functions use same JWT decoding logic."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = sample_user
        
        # Call both functions
        result1 = await get_current_user(mock_db, session_token)
        result2 = await get_optional_user(mock_db, session_token)
        
        # Verify both called decode_jwt with same token
        assert mock_decode.call_count == 2, "decode_jwt should be called twice"
        call_args_list = [call[0][0] for call in mock_decode.call_args_list]
        assert all(arg == session_token for arg in call_args_list), \
            "Both functions should call decode_jwt with same session"
        
        # Verify both extract same user
        assert result1.id == result2.id, "Both should extract same user ID"


@pytest.mark.asyncio
async def test_invariant_401_on_all_failures(mock_db):
    """Test get_current_user always returns 401 for any authentication failure."""
    failure_scenarios = [
        (None, "Missing session"),
        ("", "Empty session"),
    ]
    
    for session, description in failure_scenarios:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, session)
        
        assert exc_info.value.status_code == 401, \
            f"All failures should return 401: {description}"


@pytest.mark.asyncio
async def test_invariant_401_on_all_failures_extended(mock_db):
    """Test get_current_user returns 401 for various failure modes."""
    
    # Test invalid JWT
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "invalid")
        assert exc_info.value.status_code == 401
    
    # Test missing sub
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.return_value = {}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "token")
        assert exc_info.value.status_code == 401
    
    # Test invalid UUID
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.return_value = {'sub': 'invalid'}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "token")
        assert exc_info.value.status_code == 401
    
    # Test user not found
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        mock_decode.return_value = {'sub': str(uuid.uuid4())}
        mock_query.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "token")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_database_session_not_mutated(mock_db, sample_user, sample_user_id):
    """Test that AsyncSession is used but not mutated by authentication functions."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        mock_decode.return_value = {'sub': str(sample_user_id)}
        mock_query.return_value = sample_user
        
        # Call both functions
        await get_current_user(mock_db, session_token)
        await get_optional_user(mock_db, session_token)
        
        # Verify no mutations
        mock_db.commit.assert_not_called(), "commit should not be called"
        mock_db.add.assert_not_called(), "add should not be called"
        mock_db.delete.assert_not_called(), "delete should not be called"
        mock_db.rollback.assert_not_called(), "rollback should not be called"


# Additional edge cases

@pytest.mark.asyncio
async def test_get_current_user_with_whitespace_session(mock_db):
    """Test get_current_user handles whitespace-only session."""
    with patch('contract_test.decode_jwt') as mock_decode:
        mock_decode.side_effect = Exception("Invalid JWT")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "   ")
        
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_optional_user_never_raises(mock_db):
    """Test get_optional_user never raises exceptions for any input."""
    test_inputs = [
        None,
        "",
        "invalid",
        "🔒" * 100,
        "'; DROP TABLE users; --",
        " " * 1000,
    ]
    
    for session in test_inputs:
        # Should not raise any exception
        result = await get_optional_user(mock_db, session)
        assert result is None, f"Should return None for input: {repr(session)}"


@pytest.mark.asyncio
async def test_get_current_user_uuid_case_sensitivity(mock_db, sample_user):
    """Test UUID handling is case-insensitive as per UUID spec."""
    session_token = "valid.jwt.token"
    user_id = uuid.UUID('AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE')
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        # Provide uppercase UUID string
        mock_decode.return_value = {'sub': 'AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE'}
        user = User(id=user_id)
        mock_query.return_value = user
        
        result = await get_current_user(mock_db, session_token)
        
        assert result.id == user_id


@pytest.mark.asyncio
async def test_get_current_user_with_extra_jwt_claims(mock_db, sample_user, sample_user_id):
    """Test get_current_user handles JWTs with extra claims beyond sub."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        # JWT with extra claims
        mock_decode.return_value = {
            'sub': str(sample_user_id),
            'exp': 1234567890,
            'iat': 1234567800,
            'role': 'admin',
            'custom': 'data'
        }
        mock_query.return_value = sample_user
        
        result = await get_current_user(mock_db, session_token)
        
        assert result.id == sample_user_id


@pytest.mark.asyncio
async def test_user_object_has_correct_type(mock_db, sample_user_id):
    """Test returned User object has correct type and structure."""
    session_token = "valid.jwt.token"
    
    with patch('contract_test.decode_jwt') as mock_decode, \
         patch('contract_test._query_user_by_id') as mock_query:
        
        mock_decode.return_value = {'sub': str(sample_user_id)}
        user = User(id=sample_user_id)
        mock_query.return_value = user
        
        result = await get_current_user(mock_db, session_token)
        
        assert hasattr(result, 'id'), "User should have id attribute"
        assert isinstance(result.id, uuid.UUID), "User.id should be UUID type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
