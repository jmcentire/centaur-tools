"""
Contract test suite for backend_api_auth_dependencies
Generated from contract version 1

Tests authentication dependency functions with comprehensive coverage:
- get_current_user: JWT authentication with error handling
- get_optional_user: JWT authentication with graceful failures

Test layers:
1. Parametrized unit tests with AsyncMock for all scenarios
2. Behavioral contract tests comparing both functions
3. Invariant tests for contract guarantees
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import random
import string

# Import component under test
from backend.api.auth.dependencies import get_current_user, get_optional_user


# Test fixtures
@pytest.fixture
def mock_async_session():
    """Mock SQLAlchemy AsyncSession"""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Mock User model"""
    user = MagicMock()
    user.id = UUID("550e8400-e29b-41d4-a716-446655440000")
    return user


@pytest.fixture
def valid_jwt_token():
    """Mock valid JWT token"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAifQ.test"


# ============================================================================
# LAYER 1: PARAMETRIZED UNIT TESTS - get_current_user
# ============================================================================

class TestGetCurrentUserHappyPath:
    """Happy path tests for get_current_user"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_happy_path(self, mock_async_session, mock_user, valid_jwt_token):
        """Valid session cookie with valid JWT and existing user returns User object"""
        # Mock decode_jwt to return valid payload
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            # Mock database query to return user
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            # Execute
            user = await get_current_user(db=mock_async_session, session=valid_jwt_token)
            
            # Assertions
            assert user is not None
            assert user.id == UUID("550e8400-e29b-41d4-a716-446655440000")
            mock_decode.assert_called_once_with(valid_jwt_token)


class TestGetCurrentUserErrorCases:
    """Error case tests for get_current_user - all should raise HTTPException(401)"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_missing_session_none(self, mock_async_session):
        """Session parameter is None raises HTTPException 401"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=mock_async_session, session=None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail is not None
    
    @pytest.mark.asyncio
    async def test_get_current_user_missing_session_empty(self, mock_async_session):
        """Session parameter is empty string raises HTTPException 401"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=mock_async_session, session="")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail is not None
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_jwt(self, mock_async_session):
        """Invalid JWT token raises HTTPException 401"""
        from fastapi import HTTPException
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            # Simulate JWT decode failure
            mock_decode.side_effect = Exception("Invalid JWT")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session="invalid.jwt.token")
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_without_sub(self, mock_async_session):
        """Valid JWT without sub field raises HTTPException 401"""
        from fastapi import HTTPException
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            # Return payload without 'sub' field
            mock_decode.return_value = {"other_field": "value"}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session="jwt_without_sub")
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid_format(self, mock_async_session):
        """JWT with non-UUID sub field raises HTTPException 401"""
        from fastapi import HTTPException
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            # Return invalid UUID string
            mock_decode.return_value = {"sub": "not-a-valid-uuid"}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session="jwt_with_invalid_uuid")
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_async_session, valid_jwt_token):
        """Valid JWT but user not in database raises HTTPException 401"""
        from fastapi import HTTPException
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            # Mock database query to return None (user not found)
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session=valid_jwt_token)
            
            assert exc_info.value.status_code == 401


class TestGetCurrentUserEdgeCases:
    """Edge case tests for get_current_user"""
    
    @pytest.mark.asyncio
    async def test_edge_case_whitespace_session(self, mock_async_session):
        """Session with only whitespace is treated as invalid"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=mock_async_session, session="   ")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_edge_case_very_long_session(self, mock_async_session):
        """Extremely long session string is handled gracefully"""
        from fastapi import HTTPException
        
        long_session = "x" * 10000
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid JWT")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session=long_session)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_edge_case_sql_injection_attempt(self, mock_async_session):
        """Session containing SQL injection patterns is rejected"""
        from fastapi import HTTPException
        
        malicious_session = "'; DROP TABLE users; --"
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid JWT")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_async_session, session=malicious_session)
            
            assert exc_info.value.status_code == 401


# ============================================================================
# LAYER 1: PARAMETRIZED UNIT TESTS - get_optional_user
# ============================================================================

class TestGetOptionalUserHappyPath:
    """Happy path tests for get_optional_user"""
    
    @pytest.mark.asyncio
    async def test_get_optional_user_happy_path(self, mock_async_session, mock_user, valid_jwt_token):
        """Valid session cookie with valid JWT and existing user returns User object"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            # Mock database query to return user
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            # Execute
            user = await get_optional_user(db=mock_async_session, session=valid_jwt_token)
            
            # Assertions
            assert user is not None
            assert user.id == UUID("550e8400-e29b-41d4-a716-446655440000")


class TestGetOptionalUserEdgeCases:
    """Edge case tests for get_optional_user - all should return None gracefully"""
    
    @pytest.mark.asyncio
    async def test_get_optional_user_missing_session_none(self, mock_async_session):
        """Session parameter is None returns None without raising exception"""
        result = await get_optional_user(db=mock_async_session, session=None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_missing_session_empty(self, mock_async_session):
        """Session parameter is empty string returns None without raising exception"""
        result = await get_optional_user(db=mock_async_session, session="")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_jwt(self, mock_async_session):
        """Invalid JWT token returns None without raising exception"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid JWT")
            
            result = await get_optional_user(db=mock_async_session, session="invalid.jwt.token")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_user_not_found(self, mock_async_session, valid_jwt_token):
        """Valid JWT but user not in database returns None without raising exception"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            # Mock database query to return None
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            result = await get_optional_user(db=mock_async_session, session=valid_jwt_token)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_jwt_without_sub(self, mock_async_session):
        """JWT without sub field returns None without raising exception"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"other_field": "value"}
            
            result = await get_optional_user(db=mock_async_session, session="jwt_without_sub")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_uuid_format(self, mock_async_session):
        """JWT with invalid UUID returns None without raising exception"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "not-a-valid-uuid"}
            
            result = await get_optional_user(db=mock_async_session, session="jwt_invalid_uuid")
            assert result is None


# ============================================================================
# LAYER 2: BEHAVIORAL CONTRACT TESTS
# ============================================================================

class TestBehavioralContract:
    """Tests comparing get_current_user vs get_optional_user with identical inputs"""
    
    @pytest.mark.asyncio
    async def test_behavioral_contract_valid_session(self, mock_user, valid_jwt_token):
        """get_current_user and get_optional_user behave consistently with valid session"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            # Setup two separate mock sessions
            mock_session_1 = AsyncMock()
            mock_result_1 = AsyncMock()
            mock_result_1.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_session_1.execute = AsyncMock(return_value=mock_result_1)
            
            mock_session_2 = AsyncMock()
            mock_result_2 = AsyncMock()
            mock_result_2.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_session_2.execute = AsyncMock(return_value=mock_result_2)
            
            # Execute both functions
            user1 = await get_current_user(db=mock_session_1, session=valid_jwt_token)
            user2 = await get_optional_user(db=mock_session_2, session=valid_jwt_token)
            
            # Both should return User with same id
            assert user1 is not None
            assert user2 is not None
            assert user1.id == user2.id
    
    @pytest.mark.asyncio
    async def test_behavioral_contract_invalid_session(self):
        """get_current_user raises 401, get_optional_user returns None for same invalid input"""
        from fastapi import HTTPException
        
        mock_session_1 = AsyncMock()
        mock_session_2 = AsyncMock()
        invalid_session = "invalid.jwt.token"
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid JWT")
            
            # get_current_user should raise
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=mock_session_1, session=invalid_session)
            assert exc_info.value.status_code == 401
            
            # get_optional_user should return None
            result = await get_optional_user(db=mock_session_2, session=invalid_session)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_behavioral_contract_none_session(self):
        """Consistent behavior for None session across both functions"""
        from fastapi import HTTPException
        
        mock_session_1 = AsyncMock()
        mock_session_2 = AsyncMock()
        
        # get_current_user should raise
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=mock_session_1, session=None)
        assert exc_info.value.status_code == 401
        
        # get_optional_user should return None
        result = await get_optional_user(db=mock_session_2, session=None)
        assert result is None


# ============================================================================
# LAYER 3: INVARIANT TESTS
# ============================================================================

class TestInvariants:
    """Tests for contract invariants"""
    
    @pytest.mark.asyncio
    async def test_invariant_get_current_user_always_401(self, mock_async_session):
        """All authentication failures in get_current_user result in HTTPException with status_code=401"""
        from fastapi import HTTPException
        
        test_cases = [
            None,
            "",
            "   ",
            "invalid.jwt.token",
            "x" * 10000,
        ]
        
        for session_value in test_cases:
            with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
                if session_value and session_value.strip():
                    mock_decode.side_effect = Exception("Invalid JWT")
                
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(db=mock_async_session, session=session_value)
                
                # All must have status_code 401
                assert exc_info.value.status_code == 401, f"Failed for session: {session_value}"
    
    @pytest.mark.asyncio
    async def test_invariant_user_id_matches_jwt_sub(self, mock_async_session, mock_user, valid_jwt_token):
        """User.id field matches JWT sub claim when successfully authenticated"""
        expected_uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": str(expected_uuid)}
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            user = await get_current_user(db=mock_async_session, session=valid_jwt_token)
            
            # User.id must match JWT sub
            assert user.id == expected_uuid
    
    @pytest.mark.asyncio
    async def test_invariant_get_optional_user_never_raises(self, mock_async_session):
        """get_optional_user never raises exceptions, always returns User or None"""
        test_cases = [
            None,
            "",
            "invalid.jwt.token",
            "x" * 10000,
            "'; DROP TABLE users; --",
        ]
        
        for session_value in test_cases:
            with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
                mock_decode.side_effect = Exception("Any error")
                
                # Should never raise, only return None
                result = await get_optional_user(db=mock_async_session, session=session_value)
                assert result is None, f"Should return None for session: {session_value}"
    
    @pytest.mark.asyncio
    async def test_invariant_get_optional_user_returns_user_or_none(self, mock_async_session, mock_user, valid_jwt_token):
        """get_optional_user always returns either User or None, never other types"""
        # Test with valid session - should return User
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            result = await get_optional_user(db=mock_async_session, session=valid_jwt_token)
            assert result is not None
            assert hasattr(result, 'id')
        
        # Test with invalid session - should return None
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid")
            
            result = await get_optional_user(db=mock_async_session, session="invalid")
            assert result is None


# ============================================================================
# PARAMETRIZED TESTS WITH MULTIPLE SCENARIOS
# ============================================================================

class TestParametrizedScenarios:
    """Parametrized tests covering multiple scenarios systematically"""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("session,should_raise", [
        (None, True),
        ("", True),
        ("   ", True),
        ("invalid", True),
        ("x" * 10000, True),
    ])
    async def test_get_current_user_error_scenarios(self, mock_async_session, session, should_raise):
        """Parametrized test for various error scenarios in get_current_user"""
        from fastapi import HTTPException
        
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            if session and session.strip():
                mock_decode.side_effect = Exception("Invalid")
            
            if should_raise:
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(db=mock_async_session, session=session)
                assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("session", [
        None,
        "",
        "   ",
        "invalid",
        "x" * 10000,
        "'; DROP TABLE users; --",
    ])
    async def test_get_optional_user_never_raises_parametrized(self, mock_async_session, session):
        """Parametrized test ensuring get_optional_user never raises for any input"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Any error")
            
            # Should never raise
            result = await get_optional_user(db=mock_async_session, session=session)
            assert result is None


# ============================================================================
# RANDOMIZED INPUT TESTS
# ============================================================================

class TestRandomizedInputs:
    """Tests with randomized inputs to catch unexpected edge cases"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_random_invalid_tokens(self, mock_async_session):
        """Test get_current_user with random invalid tokens"""
        from fastapi import HTTPException
        
        # Generate 10 random invalid tokens
        for _ in range(10):
            length = random.randint(1, 1000)
            random_token = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))
            
            with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
                mock_decode.side_effect = Exception("Invalid JWT")
                
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(db=mock_async_session, session=random_token)
                
                assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_optional_user_random_invalid_tokens(self, mock_async_session):
        """Test get_optional_user with random invalid tokens"""
        # Generate 10 random invalid tokens
        for _ in range(10):
            length = random.randint(1, 1000)
            random_token = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            
            with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
                mock_decode.side_effect = Exception("Invalid JWT")
                
                # Should never raise
                result = await get_optional_user(db=mock_async_session, session=random_token)
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_random_uuid_strings(self, mock_async_session):
        """Test get_current_user with random UUID-like but invalid strings"""
        from fastapi import HTTPException
        
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "550e8400-ZZZZ-41d4-a716-446655440000",  # Invalid characters
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
        ]
        
        for invalid_uuid in invalid_uuids:
            with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
                mock_decode.return_value = {"sub": invalid_uuid}
                
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(db=mock_async_session, session="token")
                
                assert exc_info.value.status_code == 401


# ============================================================================
# DATABASE INTERACTION TESTS
# ============================================================================

class TestDatabaseInteraction:
    """Tests focusing on database interaction behavior"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_database_query_called(self, mock_async_session, mock_user, valid_jwt_token):
        """Verify database query is called with correct parameters"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            await get_current_user(db=mock_async_session, session=valid_jwt_token)
            
            # Verify execute was called
            mock_async_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_optional_user_database_query_called(self, mock_async_session, mock_user, valid_jwt_token):
        """Verify database query is called in get_optional_user"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.return_value = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
            mock_async_session.execute = AsyncMock(return_value=mock_result)
            
            await get_optional_user(db=mock_async_session, session=valid_jwt_token)
            
            # Verify execute was called
            mock_async_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_not_queried_for_invalid_session(self, mock_async_session):
        """Database should not be queried if session validation fails early"""
        with patch('backend.api.auth.dependencies.decode_jwt') as mock_decode:
            mock_decode.side_effect = Exception("Invalid JWT")
            
            mock_async_session.execute = AsyncMock()
            
            # Try get_optional_user (won't raise)
            await get_optional_user(db=mock_async_session, session="invalid")
            
            # Database should not be queried
            mock_async_session.execute.assert_not_called()
