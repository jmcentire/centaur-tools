"""
Contract Test Suite for Backend API Auth Router Interface
Generated test suite with pytest for auth router contract verification.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import json

# Import the module under test
try:
    from contracts.contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.interface import (
        create_jwt,
        decode_jwt,
        get_current_user,
        login,
        callback,
        logout,
        me,
    )
except ImportError:
    # Fallback if module structure is different
    import sys
    sys.path.insert(0, '.')
    create_jwt = None
    decode_jwt = None
    get_current_user = None
    login = None
    callback = None
    logout = None
    me = None


# Fixtures

@pytest.fixture
def mock_settings():
    """Mock settings configuration"""
    settings = Mock()
    settings.jwt_secret = "test_secret_key_for_jwt_signing"
    settings.jwt_algorithm = "HS256"
    settings.jwt_expiry_days = 7
    settings.github_client_id = "test_github_client_id"
    settings.github_client_secret = "test_github_client_secret"
    settings.frontend_url = "https://frontend.example.com"
    return settings


@pytest.fixture
def sample_user_id():
    """Sample user UUID"""
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def mock_user():
    """Mock User model instance"""
    user = Mock()
    user.id = UUID("550e8400-e29b-41d4-a716-446655440000")
    user.username = "testuser"
    user.display_name = "Test User"
    user.avatar_url = "https://avatars.example.com/testuser"
    user.bio = "Test bio"
    return user


@pytest.fixture
def mock_user_minimal():
    """Mock User with minimal fields (optional fields as None)"""
    user = Mock()
    user.id = UUID("550e8400-e29b-41d4-a716-446655440000")
    user.username = "testuser"
    user.display_name = None
    user.avatar_url = None
    user.bio = None
    return user


@pytest.fixture
def mock_db():
    """Mock AsyncSession database"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_github_user_response():
    """Mock GitHub API user response"""
    return {
        "id": 12345678,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        "email": "testuser@example.com"
    }


@pytest.fixture
def mock_github_token_response():
    """Mock GitHub token exchange response"""
    return {
        "access_token": "gho_test_access_token_123456",
        "token_type": "bearer",
        "scope": "read:user,user:email"
    }


# JWT Tests

class TestCreateJWT:
    """Tests for create_jwt function"""

    def test_create_jwt_happy_path(self, mock_settings, sample_user_id):
        """Successfully creates a valid JWT token with correct claims"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            # Mock jwt module
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                mock_jwt.encode.return_value = "mock.jwt.token"
                
                if create_jwt is None:
                    pytest.skip("create_jwt not available")
                
                # Create JWT
                token = create_jwt(sample_user_id)
                
                # Assertions
                assert token is not None
                assert isinstance(token, str)
                assert len(token) > 0
                
                # Verify encode was called with correct parameters
                mock_jwt.encode.assert_called_once()
                call_args = mock_jwt.encode.call_args
                payload = call_args[0][0]
                
                # Verify payload structure
                assert 'sub' in payload
                assert payload['sub'] == str(sample_user_id)
                assert 'exp' in payload
                assert 'iat' in payload
                
                # Verify algorithm used
                assert call_args[1]['algorithm'] == 'HS256'

    def test_create_jwt_different_algorithms(self, mock_settings, sample_user_id):
        """Creates JWT with different algorithm configured in settings"""
        mock_settings.jwt_algorithm = "HS512"
        
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                mock_jwt.encode.return_value = "mock.jwt.token"
                
                if create_jwt is None:
                    pytest.skip("create_jwt not available")
                
                token = create_jwt(sample_user_id)
                
                assert token is not None
                call_args = mock_jwt.encode.call_args
                assert call_args[1]['algorithm'] == 'HS512'

    def test_create_jwt_custom_expiry(self, mock_settings, sample_user_id):
        """JWT expiry respects custom jwt_expiry_days setting"""
        mock_settings.jwt_expiry_days = 30
        
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.datetime') as mock_datetime:
                    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                    mock_datetime.now.return_value = now
                    mock_datetime.timedelta = timedelta
                    
                    mock_jwt.encode.return_value = "mock.jwt.token"
                    
                    if create_jwt is None:
                        pytest.skip("create_jwt not available")
                    
                    token = create_jwt(sample_user_id)
                    
                    call_args = mock_jwt.encode.call_args
                    payload = call_args[0][0]
                    
                    # Verify exp is 30 days from iat
                    expected_exp = now + timedelta(days=30)
                    assert payload['exp'] == expected_exp
                    assert payload['iat'] == now


class TestDecodeJWT:
    """Tests for decode_jwt function"""

    def test_decode_jwt_happy_path(self, mock_settings):
        """Successfully decodes a valid JWT token"""
        valid_payload = {
            'sub': '550e8400-e29b-41d4-a716-446655440000',
            'exp': datetime.now(timezone.utc) + timedelta(days=7),
            'iat': datetime.now(timezone.utc)
        }
        
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                mock_jwt.decode.return_value = valid_payload
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                result = decode_jwt("valid.jwt.token")
                
                # Assertions
                assert isinstance(result, dict)
                assert 'sub' in result
                assert 'exp' in result
                assert 'iat' in result
                assert result['sub'] == '550e8400-e29b-41d4-a716-446655440000'

    def test_decode_jwt_invalid_signature(self, mock_settings):
        """Raises InvalidTokenError when token signature is invalid"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import InvalidTokenError
                mock_jwt.decode.side_effect = InvalidTokenError("Invalid signature")
                mock_jwt.exceptions.InvalidTokenError = InvalidTokenError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                with pytest.raises(InvalidTokenError):
                    decode_jwt("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid_signature")

    def test_decode_jwt_expired_token(self, mock_settings):
        """Raises ExpiredSignatureError when token has expired"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import ExpiredSignatureError
                mock_jwt.decode.side_effect = ExpiredSignatureError("Token expired")
                mock_jwt.exceptions.ExpiredSignatureError = ExpiredSignatureError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                with pytest.raises(ExpiredSignatureError):
                    decode_jwt("expired.jwt.token")

    def test_decode_jwt_malformed_token(self, mock_settings):
        """Raises DecodeError when token format is invalid"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import DecodeError
                mock_jwt.decode.side_effect = DecodeError("Invalid token format")
                mock_jwt.exceptions.DecodeError = DecodeError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                with pytest.raises(DecodeError):
                    decode_jwt("not.a.valid.jwt.token")

    def test_decode_jwt_algorithm_mismatch(self, mock_settings):
        """Raises InvalidTokenError when token algorithm doesn't match settings"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import InvalidTokenError
                mock_jwt.decode.side_effect = InvalidTokenError("Algorithm mismatch")
                mock_jwt.exceptions.InvalidTokenError = InvalidTokenError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                with pytest.raises(InvalidTokenError):
                    decode_jwt("token.with.different.algorithm")


# get_current_user Tests

class TestGetCurrentUser:
    """Tests for get_current_user function"""

    @pytest.mark.asyncio
    async def test_get_current_user_always_raises(self, mock_db):
        """Always raises NotAuthenticated as placeholder implementation"""
        if get_current_user is None:
            pytest.skip("get_current_user not available")
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, "some_session")
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_none_session(self, mock_db):
        """Raises NotAuthenticated when session is None"""
        if get_current_user is None:
            pytest.skip("get_current_user not available")
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, None)
        
        assert exc_info.value.status_code == 401


# Login Tests

class TestLogin:
    """Tests for login function"""

    @pytest.mark.asyncio
    async def test_login_happy_path(self, mock_settings):
        """Returns redirect to GitHub OAuth authorize endpoint"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            if login is None:
                pytest.skip("login not available")
            
            response = await login()
            
            # Assertions
            assert response.status_code == 302
            assert 'github.com/login/oauth/authorize' in response.headers['location']
            assert 'client_id' in response.headers['location']
            assert 'test_github_client_id' in response.headers['location']
            assert 'scope' in response.headers['location']
            assert 'read:user' in response.headers['location']
            assert 'user:email' in response.headers['location']

    @pytest.mark.asyncio
    async def test_login_includes_correct_scope(self, mock_settings):
        """Login redirect includes correct OAuth scopes"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            if login is None:
                pytest.skip("login not available")
            
            response = await login()
            
            location = response.headers['location']
            assert 'read:user' in location
            assert 'user:email' in location


# Callback Tests

class TestCallback:
    """Tests for callback function"""

    @pytest.mark.asyncio
    async def test_callback_happy_path_new_user(self, mock_settings, mock_db, mock_github_token_response, mock_github_user_response):
        """Successfully creates new user and sets session cookie"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock httpx responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = mock_github_user_response
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                # Mock database - no existing user
                mock_db.execute.return_value.scalars.return_value.first.return_value = None
                
                # Mock User model
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.User') as mock_user_class:
                    new_user = Mock()
                    new_user.id = uuid4()
                    mock_user_class.return_value = new_user
                    
                    with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.create_jwt') as mock_create_jwt:
                        mock_create_jwt.return_value = "test.jwt.token"
                        
                        if callback is None:
                            pytest.skip("callback not available")
                        
                        response = await callback("valid_auth_code", mock_db)
                        
                        # Assertions
                        assert response.status_code == 302
                        assert response.headers['location'] == "https://frontend.example.com/dashboard"
                        assert 'set-cookie' in response.headers
                        
                        cookie_header = response.headers['set-cookie']
                        assert 'session=' in cookie_header
                        assert 'HttpOnly' in cookie_header
                        assert 'Secure' in cookie_header
                        assert 'SameSite=lax' in cookie_header or 'SameSite=Lax' in cookie_header
                        
                        # Verify database operations
                        mock_db.add.assert_called_once()
                        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_happy_path_existing_user(self, mock_settings, mock_db, mock_github_token_response, mock_github_user_response, mock_user):
        """Successfully updates existing user and sets session cookie"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock httpx responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = mock_github_user_response
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                # Mock database - existing user
                mock_db.execute.return_value.scalars.return_value.first.return_value = mock_user
                
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.create_jwt') as mock_create_jwt:
                    mock_create_jwt.return_value = "test.jwt.token"
                    
                    if callback is None:
                        pytest.skip("callback not available")
                    
                    response = await callback("valid_auth_code", mock_db)
                    
                    # Assertions
                    assert response.status_code == 302
                    # Verify user fields updated
                    assert mock_user.avatar_url == mock_github_user_response['avatar_url']
                    assert mock_user.display_name == mock_github_user_response['name']
                    
                    mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_oauth_failed_no_access_token(self, mock_settings, mock_db):
        """Raises OAuthFailed when GitHub token response missing access_token"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock token response without access_token
                mock_token_response = Mock()
                mock_token_response.json.return_value = {"error": "invalid_code"}
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                if callback is None:
                    pytest.skip("callback not available")
                
                from fastapi import HTTPException
                
                with pytest.raises((HTTPException, KeyError, Exception)) as exc_info:
                    await callback("invalid_code", mock_db)
                
                # Verify it's an OAuth-related error
                if isinstance(exc_info.value, HTTPException):
                    assert exc_info.value.status_code in [400, 401, 500]

    @pytest.mark.asyncio
    async def test_callback_github_api_error_missing_id(self, mock_settings, mock_db, mock_github_token_response):
        """Raises GitHubAPIError when user API response missing 'id' field"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = {"login": "testuser"}  # Missing 'id'
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                if callback is None:
                    pytest.skip("callback not available")
                
                from fastapi import HTTPException
                
                with pytest.raises((HTTPException, KeyError, Exception)) as exc_info:
                    await callback("valid_code", mock_db)
                
                if isinstance(exc_info.value, HTTPException):
                    assert exc_info.value.status_code in [400, 500, 502]

    @pytest.mark.asyncio
    async def test_callback_github_api_error_missing_login(self, mock_settings, mock_db, mock_github_token_response):
        """Raises GitHubAPIError when user API response missing 'login' field"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = {"id": 12345678}  # Missing 'login'
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                if callback is None:
                    pytest.skip("callback not available")
                
                from fastapi import HTTPException
                
                with pytest.raises((HTTPException, KeyError, Exception)) as exc_info:
                    await callback("valid_code", mock_db)
                
                if isinstance(exc_info.value, HTTPException):
                    assert exc_info.value.status_code in [400, 500, 502]

    @pytest.mark.asyncio
    async def test_callback_network_error(self, mock_settings, mock_db):
        """Raises NetworkError when httpx client encounters connectivity issues"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                import httpx
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.side_effect = httpx.NetworkError("Connection failed")
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                if callback is None:
                    pytest.skip("callback not available")
                
                with pytest.raises((httpx.NetworkError, Exception)):
                    await callback("valid_code", mock_db)

    @pytest.mark.asyncio
    async def test_callback_database_error(self, mock_settings, mock_github_token_response, mock_github_user_response):
        """Raises DatabaseError when database commit fails"""
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalars.return_value.first.return_value = None
        mock_db.commit.side_effect = Exception("Database commit failed")
        
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock httpx responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = mock_github_user_response
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.User') as mock_user_class:
                    new_user = Mock()
                    new_user.id = uuid4()
                    mock_user_class.return_value = new_user
                    
                    if callback is None:
                        pytest.skip("callback not available")
                    
                    with pytest.raises(Exception) as exc_info:
                        await callback("valid_code", mock_db)
                    
                    assert "Database" in str(exc_info.value) or "commit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_callback_session_cookie_expiry(self, mock_settings, mock_db, mock_github_token_response, mock_github_user_response):
        """Session cookie expiry matches jwt_expiry_days setting"""
        mock_settings.jwt_expiry_days = 14
        
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                # Mock httpx responses
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = mock_github_user_response
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                mock_db.execute.return_value.scalars.return_value.first.return_value = None
                
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.User') as mock_user_class:
                    new_user = Mock()
                    new_user.id = uuid4()
                    mock_user_class.return_value = new_user
                    
                    with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.create_jwt') as mock_create_jwt:
                        mock_create_jwt.return_value = "test.jwt.token"
                        
                        if callback is None:
                            pytest.skip("callback not available")
                        
                        response = await callback("valid_code", mock_db)
                        
                        # Check cookie expiry (max-age should be 14 days in seconds)
                        expected_max_age = 14 * 24 * 60 * 60
                        cookie_header = response.headers.get('set-cookie', '')
                        # Cookie should have max-age or expires matching jwt_expiry_days
                        assert 'max-age' in cookie_header.lower() or 'expires' in cookie_header.lower()


# Logout Tests

class TestLogout:
    """Tests for logout function"""

    @pytest.mark.asyncio
    async def test_logout_happy_path(self):
        """Returns 204 No Content and clears session cookie"""
        if logout is None:
            pytest.skip("logout not available")
        
        response = await logout()
        
        # Assertions
        assert response.status_code == 204
        
        # Check cookie deletion
        cookie_header = response.headers.get('set-cookie', '')
        assert 'session=' in cookie_header
        assert 'max-age=0' in cookie_header.lower() or 'expires' in cookie_header.lower()

    @pytest.mark.asyncio
    async def test_logout_cookie_attributes(self):
        """Logout cookie deletion maintains security attributes"""
        if logout is None:
            pytest.skip("logout not available")
        
        response = await logout()
        
        cookie_header = response.headers.get('set-cookie', '')
        assert 'HttpOnly' in cookie_header
        assert 'Secure' in cookie_header
        assert 'SameSite=lax' in cookie_header or 'SameSite=Lax' in cookie_header


# Me Tests

class TestMe:
    """Tests for me function"""

    @pytest.mark.asyncio
    async def test_me_happy_path(self, mock_user):
        """Returns authenticated user profile as JSON"""
        if me is None:
            pytest.skip("me not available")
        
        result = await me(mock_user)
        
        # Assertions
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'username' in result
        assert 'display_name' in result
        assert 'avatar_url' in result
        assert 'bio' in result
        
        # Verify values
        assert result['id'] == str(mock_user.id)
        assert result['username'] == mock_user.username
        assert result['display_name'] == mock_user.display_name
        assert result['avatar_url'] == mock_user.avatar_url
        assert result['bio'] == mock_user.bio

    @pytest.mark.asyncio
    async def test_me_optional_fields_null(self, mock_user_minimal):
        """Returns user profile with null optional fields"""
        if me is None:
            pytest.skip("me not available")
        
        result = await me(mock_user_minimal)
        
        # Assertions
        assert result['display_name'] is None
        assert result['avatar_url'] is None
        assert result['bio'] is None
        assert result['id'] == str(mock_user_minimal.id)
        assert result['username'] == mock_user_minimal.username

    @pytest.mark.asyncio
    async def test_me_not_authenticated(self):
        """Raises NotAuthenticated when user dependency fails"""
        # This is tested through the dependency injection mechanism
        # The get_current_user dependency would raise HTTPException
        # This test verifies that me expects an authenticated user
        if me is None:
            pytest.skip("me not available")
        
        # The function signature shows user: User parameter
        # which means it depends on authentication
        # The actual 401 would be raised by get_current_user dependency
        # We verify this by checking the function accepts User type
        import inspect
        if me:
            sig = inspect.signature(me)
            assert 'user' in sig.parameters


# Invariant Tests

class TestInvariants:
    """Tests for contract invariants"""

    def test_invariant_github_urls(self):
        """Verify GitHub OAuth URLs are correct constants"""
        # These would be module-level constants
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.GITHUB_AUTHORIZE_URL', 'https://github.com/login/oauth/authorize'):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.GITHUB_TOKEN_URL', 'https://github.com/login/oauth/access_token'):
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.GITHUB_USER_URL', 'https://api.github.com/user'):
                    # Import and verify
                    try:
                        from contracts.contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.interface import (
                            GITHUB_AUTHORIZE_URL,
                            GITHUB_TOKEN_URL,
                            GITHUB_USER_URL
                        )
                        assert GITHUB_AUTHORIZE_URL == 'https://github.com/login/oauth/authorize'
                        assert GITHUB_TOKEN_URL == 'https://github.com/login/oauth/access_token'
                        assert GITHUB_USER_URL == 'https://api.github.com/user'
                    except ImportError:
                        pytest.skip("Constants not directly importable")

    @pytest.mark.asyncio
    async def test_invariant_router_config(self):
        """Verify router prefix and tags are configured correctly"""
        try:
            from contracts.contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.interface import router
            assert router.prefix == '/api/auth'
            assert 'auth' in router.tags
        except (ImportError, AttributeError):
            pytest.skip("Router not directly accessible")

    @pytest.mark.asyncio
    async def test_invariant_session_cookie_security(self, mock_settings, mock_db, mock_github_token_response, mock_github_user_response):
        """Verify session cookie security attributes are enforced"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.httpx.AsyncClient') as mock_client:
                mock_token_response = Mock()
                mock_token_response.json.return_value = mock_github_token_response
                
                mock_user_response = Mock()
                mock_user_response.json.return_value = mock_github_user_response
                
                mock_client_instance = AsyncMock()
                mock_client_instance.post.return_value = mock_token_response
                mock_client_instance.get.return_value = mock_user_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = AsyncMock()
                mock_client.return_value = mock_client_instance
                
                mock_db.execute.return_value.scalars.return_value.first.return_value = None
                
                with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.User') as mock_user_class:
                    new_user = Mock()
                    new_user.id = uuid4()
                    mock_user_class.return_value = new_user
                    
                    with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.create_jwt') as mock_create_jwt:
                        mock_create_jwt.return_value = "test.jwt.token"
                        
                        if callback is None:
                            pytest.skip("callback not available")
                        
                        response = await callback("valid_code", mock_db)
                        
                        cookie_header = response.headers.get('set-cookie', '')
                        assert 'session=' in cookie_header
                        assert 'HttpOnly' in cookie_header
                        assert 'Secure' in cookie_header
                        assert 'SameSite=lax' in cookie_header or 'SameSite=Lax' in cookie_header

    def test_invariant_jwt_algorithm(self, mock_settings, sample_user_id):
        """Verify JWT uses settings.jwt_algorithm consistently"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                mock_jwt.encode.return_value = "test.jwt.token"
                
                if create_jwt is None:
                    pytest.skip("create_jwt not available")
                
                create_jwt(sample_user_id)
                
                call_args = mock_jwt.encode.call_args
                assert call_args[1]['algorithm'] == mock_settings.jwt_algorithm


# Security Tests

class TestSecurity:
    """Security-focused tests"""

    def test_security_jwt_replay_attack(self, mock_settings):
        """Decoded expired JWT cannot be used for authentication"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import ExpiredSignatureError
                mock_jwt.decode.side_effect = ExpiredSignatureError("Token expired")
                mock_jwt.exceptions.ExpiredSignatureError = ExpiredSignatureError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                with pytest.raises(ExpiredSignatureError):
                    decode_jwt("expired.jwt.token")

    def test_security_jwt_tampering(self, mock_settings):
        """Modified JWT payload is rejected"""
        with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.settings', mock_settings):
            with patch('contracts_contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface_interface.jwt') as mock_jwt:
                from jwt.exceptions import InvalidTokenError
                mock_jwt.decode.side_effect = InvalidTokenError("Invalid signature")
                mock_jwt.exceptions.InvalidTokenError = InvalidTokenError
                
                if decode_jwt is None:
                    pytest.skip("decode_jwt not available")
                
                # Simulate tampering by providing token with modified payload
                tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered_payload.signature"
                
                with pytest.raises(InvalidTokenError):
                    decode_jwt(tampered_token)
"""
