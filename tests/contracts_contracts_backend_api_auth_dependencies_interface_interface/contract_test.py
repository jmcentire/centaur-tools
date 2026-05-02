"""
Contract test suite for Backend API Auth Dependencies Interface.

Tests verify authentication dependency functions get_current_user and 
get_optional_user against their behavioral contracts.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
from fastapi import HTTPException

# Import the component under test
from contracts.contracts_backend_api_auth_dependencies_interface.interface import (
    get_current_user,
    get_optional_user,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_user_id():
    """Factory fixture for valid UUID user IDs."""
    return uuid.uuid4()


@pytest.fixture
def valid_user(valid_user_id):
    """Factory fixture for valid User objects."""
    user_mock = MagicMock()
    user_mock.id = valid_user_id
    user_mock.email = "test@example.com"
    user_mock.name = "Test User"
    return user_mock


@pytest.fixture
def mock_db_session():
    """Fixture for mocked AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def valid_jwt_payload(valid_user_id):
    """Factory fixture for valid JWT payload."""
    return {"sub": str(valid_user_id), "exp": 9999999999}


@pytest.fixture
def valid_session_token():
    """Factory fixture for valid session JWT string."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


@pytest.fixture
def invalid_session_token():
    """Factory fixture for invalid JWT string."""
    return "invalid.jwt.token"


# ============================================================================
# Test Class: get_current_user
# ============================================================================

class TestGetCurrentUser:
    """Test suite for get_current_user function - strict authentication."""

    @pytest.mark.asyncio
    async def test_get_current_user_happy_path(
        self, mock_db_session, valid_user, valid_user_id, valid_jwt_payload
    ):
        """Verify get_current_user returns User object when all preconditions met."""
        # Arrange
        session_token = "valid.jwt.token"
        
        # Mock database query to return user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = valid_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act
            result = await get_current_user(mock_db_session, session_token)
            
            # Assert
            assert result is not None, "Result should not be None"
            assert result.id == valid_user_id, "User.id should match JWT sub claim"
            mock_decode.assert_called_once_with(session_token)
            mock_db_session.execute.assert_called_once()
            assert result == valid_user, "Should return the User object from database"

    @pytest.mark.asyncio
    async def test_get_current_user_missing_session(self, mock_db_session):
        """Verify get_current_user raises HTTPException(401) when session cookie is None."""
        # Arrange
        session_token = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db_session, session_token)
        
        assert exc_info.value.status_code == 401, "Should raise 401 for missing session"
        mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_jwt(self, mock_db_session):
        """Verify get_current_user raises HTTPException(401) when JWT decode fails."""
        # Arrange
        session_token = "malformed.jwt.token"
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("JWT decode error")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for invalid JWT"
            mock_decode.assert_called_once_with(session_token)
            mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid(self, mock_db_session):
        """Verify get_current_user raises HTTPException(401) when sub claim is not valid UUID."""
        # Arrange
        session_token = "valid.jwt.token"
        invalid_payload = {"sub": "not-a-uuid", "exp": 9999999999}
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = invalid_payload
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for invalid UUID"
            mock_decode.assert_called_once()
            mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(
        self, mock_db_session, valid_user_id, valid_jwt_payload
    ):
        """Verify get_current_user raises HTTPException(401) when user does not exist in database."""
        # Arrange
        session_token = "valid.jwt.token"
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 when user not found"
            mock_db_session.execute.assert_called_once()
            assert mock_result.scalar_one_or_none.called, "Query should have been executed"

    @pytest.mark.asyncio
    async def test_get_current_user_edge_empty_string(self, mock_db_session):
        """Verify get_current_user handles empty string session appropriately."""
        # Arrange
        session_token = ""
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Empty token")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for empty string"

    @pytest.mark.asyncio
    async def test_get_current_user_edge_whitespace(self, mock_db_session):
        """Verify get_current_user rejects whitespace-only session."""
        # Arrange
        session_token = "   \t\n  "
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Whitespace token")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for whitespace"

    @pytest.mark.asyncio
    async def test_get_current_user_edge_long_token(self, mock_db_session):
        """Verify get_current_user handles very long token strings."""
        # Arrange
        session_token = "a" * 10000
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Token too long")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for long token"

    @pytest.mark.asyncio
    async def test_get_current_user_edge_special_chars(self, mock_db_session):
        """Verify get_current_user handles tokens with special characters."""
        # Arrange
        session_token = "🔐🚀特殊字符!@#$%^&*()"
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Special chars in token")
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            
            assert exc_info.value.status_code == 401, "Should raise 401 for special chars"

    @pytest.mark.asyncio
    async def test_get_current_user_invariant_never_none(
        self, mock_db_session, valid_user, valid_jwt_payload
    ):
        """Verify get_current_user never returns None (always User or raises)."""
        # Test valid case - should return User
        session_token = "valid.token"
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = valid_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            result = await get_current_user(mock_db_session, session_token)
            assert result is not None, "Valid case should return User, not None"
            assert hasattr(result, 'id'), "Result should be User object"
        
        # Test invalid case - should raise, not return None
        with pytest.raises(HTTPException):
            await get_current_user(mock_db_session, None)


# ============================================================================
# Test Class: get_optional_user
# ============================================================================

class TestGetOptionalUser:
    """Test suite for get_optional_user function - permissive authentication."""

    @pytest.mark.asyncio
    async def test_get_optional_user_happy_path(
        self, mock_db_session, valid_user, valid_user_id, valid_jwt_payload
    ):
        """Verify get_optional_user returns User when session valid and user exists."""
        # Arrange
        session_token = "valid.jwt.token"
        
        # Mock database query to return user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = valid_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is not None, "Result should not be None for valid session"
            assert result.id == valid_user_id, "User.id should match JWT sub claim"
            mock_decode.assert_called_once_with(session_token)
            mock_db_session.execute.assert_called_once()
            assert result == valid_user, "Should return the User object from database"

    @pytest.mark.asyncio
    async def test_get_optional_user_missing_session(self, mock_db_session):
        """Verify get_optional_user returns None when session is None."""
        # Arrange
        session_token = None
        
        # Act
        result = await get_optional_user(mock_db_session, session_token)
        
        # Assert
        assert result is None, "Should return None for missing session"
        mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_jwt(self, mock_db_session):
        """Verify get_optional_user returns None when JWT decode fails."""
        # Arrange
        session_token = "malformed.jwt.token"
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("JWT decode error")
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for invalid JWT"
            mock_decode.assert_called_once_with(session_token)

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_uuid(self, mock_db_session):
        """Verify get_optional_user returns None when sub claim is not valid UUID."""
        # Arrange
        session_token = "valid.jwt.token"
        invalid_payload = {"sub": "not-a-uuid", "exp": 9999999999}
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = invalid_payload
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for invalid UUID"
            mock_decode.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_optional_user_user_not_found(
        self, mock_db_session, valid_jwt_payload
    ):
        """Verify get_optional_user returns None when user does not exist in database."""
        # Arrange
        session_token = "valid.jwt.token"
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None when user not found"
            mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_optional_user_edge_empty_string(self, mock_db_session):
        """Verify get_optional_user returns None for empty string session."""
        # Arrange
        session_token = ""
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Empty token")
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for empty string"

    @pytest.mark.asyncio
    async def test_get_optional_user_edge_whitespace(self, mock_db_session):
        """Verify get_optional_user returns None for whitespace-only session."""
        # Arrange
        session_token = "   \t\n  "
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Whitespace token")
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for whitespace"

    @pytest.mark.asyncio
    async def test_get_optional_user_edge_long_token(self, mock_db_session):
        """Verify get_optional_user handles very long token strings."""
        # Arrange
        session_token = "a" * 10000
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Token too long")
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for long token"

    @pytest.mark.asyncio
    async def test_get_optional_user_edge_special_chars(self, mock_db_session):
        """Verify get_optional_user handles tokens with special characters."""
        # Arrange
        session_token = "🔐🚀特殊字符!@#$%^&*()"
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Special chars in token")
            
            # Act
            result = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result is None, "Should return None for special chars"

    @pytest.mark.asyncio
    async def test_get_optional_user_invariant_no_exceptions(self, mock_db_session):
        """Verify get_optional_user never raises exceptions regardless of input."""
        # Test various inputs that would cause get_current_user to raise
        test_cases = [
            None,
            "",
            "invalid",
            "🔐🚀",
            "a" * 10000,
        ]
        
        for session_token in test_cases:
            with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
                mock_decode.side_effect = Exception("Simulated error")
                
                # Act - should not raise
                result = await get_optional_user(mock_db_session, session_token)
                
                # Assert
                assert result is None or hasattr(result, 'id'), "Result must be User or None"


# ============================================================================
# Test Class: Invariants
# ============================================================================

class TestInvariants:
    """Test suite for cross-function invariants."""

    @pytest.mark.asyncio
    async def test_invariant_user_id_extraction(
        self, mock_db_session, valid_user, valid_user_id, valid_jwt_payload
    ):
        """Verify both functions extract user_id from JWT sub claim as UUID consistently."""
        # Arrange
        session_token = "valid.jwt.token"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = valid_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act - call both functions
            result1 = await get_current_user(mock_db_session, session_token)
            
            # Reset mocks
            mock_db_session.reset_mock()
            mock_decode.reset_mock()
            mock_result.reset_mock()
            mock_result.scalar_one_or_none.return_value = valid_user
            mock_db_session.execute.return_value = mock_result
            
            mock_decode.return_value = valid_jwt_payload
            result2 = await get_optional_user(mock_db_session, session_token)
            
            # Assert
            assert result1.id == result2.id, "Both functions should extract same user_id"
            assert result1.id == valid_user_id, "Extracted ID should match JWT sub claim"

    @pytest.mark.asyncio
    async def test_invariant_idempotency(
        self, mock_db_session, valid_user, valid_jwt_payload
    ):
        """Verify calling functions multiple times with same token returns same user."""
        # Arrange
        session_token = "valid.jwt.token"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = valid_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act - call multiple times
            result1 = await get_current_user(mock_db_session, session_token)
            
            mock_db_session.reset_mock()
            mock_result.reset_mock()
            mock_result.scalar_one_or_none.return_value = valid_user
            mock_db_session.execute.return_value = mock_result
            
            result2 = await get_current_user(mock_db_session, session_token)
            
            mock_db_session.reset_mock()
            mock_result.reset_mock()
            mock_result.scalar_one_or_none.return_value = valid_user
            mock_db_session.execute.return_value = mock_result
            
            result3 = await get_current_user(mock_db_session, session_token)
            
            # Assert
            assert result1.id == result2.id == result3.id, "All calls should return same user ID"
            assert result1.id == valid_user.id, "User state should be unchanged"

    @pytest.mark.asyncio
    async def test_invariant_behavioral_difference(
        self, mock_db_session, valid_jwt_payload
    ):
        """Verify behavioral difference: get_current_user raises, get_optional_user returns None."""
        # Arrange - user not found scenario
        session_token = "valid.jwt.token"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch('contracts_contracts_backend_api_auth_dependencies_interface_interface.decode_jwt') as mock_decode:
            mock_decode.return_value = valid_jwt_payload
            
            # Act & Assert - get_current_user should raise
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_db_session, session_token)
            assert exc_info.value.status_code == 401
            
            # Reset mocks
            mock_db_session.reset_mock()
            mock_result.reset_mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result
            mock_decode.reset_mock()
            mock_decode.return_value = valid_jwt_payload
            
            # Act & Assert - get_optional_user should return None
            result = await get_optional_user(mock_db_session, session_token)
            assert result is None, "get_optional_user should return None, not raise"
