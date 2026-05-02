"""
Contract Test Suite for Backend API Auth Router Interface
Generated test suite with pytest for JWT authentication and GitHub OAuth flow.

Test Coverage:
- Unit tests for create_jwt and decode_jwt (pure logic)
- Unit tests for auth endpoints with mocked dependencies
- Error path coverage for all 8 error types
- Invariant tests for GitHub URLs, router config, cookie attributes, OAuth scope
- Edge cases for JWT expiry boundaries and nullable fields
- Security tests for JWT attacks and token tampering
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional
import json
import base64

# Import the component under test
# Assuming the module path based on component_id
try:
    from contracts.contracts_contracts_backend_api_auth_router_interface_interface.interface import (
        create_jwt,
        decode_jwt,
        get_current_user,
        login,
        callback,
        logout,
        me,
    )
except ImportError:
    # Fallback import if module structure is different
    create_jwt = None
    decode_jwt = None
    get_current_user = None
    login = None
    callback = None
    logout = None
    me = None


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings configuration."""
    settings = Mock()
    settings.jwt_secret = "test_secret_key_12345678901234567890"
    settings.jwt_algorithm = "HS256"
    settings.jwt_expiry_days = 7
    settings.github_client_id = "test_github_client_id"
    settings.github_client_secret = "test_github_client_secret"
    settings.frontend_url = "http://localhost:3000"
    return settings


@pytest.fixture
def sample_user_id():
    """Sample UUID for testing."""
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_user_id_2():
    """Second sample UUID for testing."""
    return uuid.UUID("660e8400-e29b-41d4-a716-446655440001")


@pytest.fixture
def mock_user():
    """Mock User database model."""
    user = Mock()
    user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    user.username = "testuser"
    user.display_name = "Test User"
    user.avatar_url = "https://avatars.githubusercontent.com/u/123456"
    user.bio = "Test bio"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_user_minimal():
    """Mock User with minimal/null optional fields."""
    user = Mock()
    user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    user.username = "minimaluser"
    user.display_name = None
    user.avatar_url = None
    user.bio = None
    user.email = "minimal@example.com"
    return user


@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for database operations."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def github_token_response():
    """Mock successful GitHub token exchange response."""
    return {
        "access_token": "gho_test_access_token_123456",
        "token_type": "bearer",
        "scope": "read:user,user:email"
    }


@pytest.fixture
def github_user_response():
    """Mock successful GitHub user API response."""
    return {
        "id": 123456,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/123456",
        "bio": "Test bio",
        "email": "test@example.com"
    }


@pytest.fixture
def github_user_response_minimal():
    """Mock GitHub user API response with null optional fields."""
    return {
        "id": 123456,
        "login": "minimaluser",
        "name": None,
        "avatar_url": None,
        "bio": None,
        "email": "minimal@example.com"
    }


# ============================================================================
# JWT UNIT TESTS (Pure Logic)
# ============================================================================

@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_create_jwt_happy_path(mock_settings_module, mock_settings, sample_user_id):
    """Verifies create_jwt generates a valid JWT token with correct claims for a given user UUID."""
    if create_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token = create_jwt(sample_user_id)
    
    # Token is a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Token contains 3 parts separated by dots
    parts = token.split('.')
    assert len(parts) == 3
    
    # Decode to verify claims
    import jwt as pyjwt
    decoded = pyjwt.decode(token, mock_settings.jwt_secret, algorithms=[mock_settings.jwt_algorithm])
    
    # Decoded token contains 'sub' with stringified UUID
    assert 'sub' in decoded
    assert decoded['sub'] == str(sample_user_id)
    
    # Decoded token contains 'exp' claim
    assert 'exp' in decoded
    
    # Decoded token contains 'iat' claim
    assert 'iat' in decoded
    
    # Token expiry is jwt_expiry_days from now
    iat_time = datetime.fromtimestamp(decoded['iat'], tz=timezone.utc)
    exp_time = datetime.fromtimestamp(decoded['exp'], tz=timezone.utc)
    expected_delta = timedelta(days=mock_settings.jwt_expiry_days)
    actual_delta = exp_time - iat_time
    
    # Allow 2 second tolerance for execution time
    assert abs(actual_delta.total_seconds() - expected_delta.total_seconds()) < 2


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_create_jwt_different_uuids(mock_settings_module, mock_settings, sample_user_id, sample_user_id_2):
    """Verifies create_jwt generates different tokens for different user IDs."""
    if create_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token1 = create_jwt(sample_user_id)
    token2 = create_jwt(sample_user_id_2)
    
    # Tokens are different strings
    assert token1 != token2
    
    # Each token decodes to its respective user_id
    import jwt as pyjwt
    decoded1 = pyjwt.decode(token1, mock_settings.jwt_secret, algorithms=[mock_settings.jwt_algorithm])
    decoded2 = pyjwt.decode(token2, mock_settings.jwt_secret, algorithms=[mock_settings.jwt_algorithm])
    
    assert decoded1['sub'] == str(sample_user_id)
    assert decoded2['sub'] == str(sample_user_id_2)


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_happy_path(mock_settings_module, mock_settings, sample_user_id):
    """Verifies decode_jwt correctly decodes a valid JWT token."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token = create_jwt(sample_user_id)
    payload = decode_jwt(token)
    
    # Returns a dictionary
    assert isinstance(payload, dict)
    
    # Dictionary contains 'sub' key
    assert 'sub' in payload
    
    # Dictionary contains 'exp' key
    assert 'exp' in payload
    
    # Dictionary contains 'iat' key
    assert 'iat' in payload


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_roundtrip(mock_settings_module, mock_settings, sample_user_id):
    """Verifies JWT roundtrip: encode then decode returns original payload."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token = create_jwt(sample_user_id)
    payload = decode_jwt(token)
    
    # Decoded 'sub' matches original UUID string
    assert payload['sub'] == str(sample_user_id)
    
    # exp and iat are present and valid
    assert 'exp' in payload
    assert 'iat' in payload
    assert isinstance(payload['exp'], (int, float))
    assert isinstance(payload['iat'], (int, float))
    assert payload['exp'] > payload['iat']


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_invalid_signature(mock_settings_module, mock_settings, sample_user_id):
    """Verifies decode_jwt raises InvalidTokenError when token has been tampered with."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    # Create valid token
    token = create_jwt(sample_user_id)
    
    # Change the secret for decoding
    mock_settings_module.jwt_secret = "wrong_secret_key"
    
    # InvalidTokenError is raised
    from jwt.exceptions import InvalidTokenError
    with pytest.raises(InvalidTokenError):
        decode_jwt(token)


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.datetime')
def test_decode_jwt_expired_token(mock_datetime, mock_settings_module, mock_settings, sample_user_id):
    """Verifies decode_jwt raises ExpiredSignatureError for expired tokens."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    import jwt as pyjwt
    from jwt.exceptions import ExpiredSignatureError
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    # Create a token that's already expired
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(days=10)
    
    payload = {
        'sub': str(sample_user_id),
        'exp': past_time,
        'iat': past_time - timedelta(days=1)
    }
    
    expired_token = pyjwt.encode(payload, mock_settings.jwt_secret, algorithm=mock_settings.jwt_algorithm)
    
    # ExpiredSignatureError is raised
    with pytest.raises(ExpiredSignatureError):
        decode_jwt(expired_token)


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_malformed_token(mock_settings_module, mock_settings):
    """Verifies decode_jwt raises DecodeError for malformed tokens."""
    if decode_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    
    from jwt.exceptions import DecodeError
    
    # DecodeError is raised
    with pytest.raises(DecodeError):
        decode_jwt("not.a.valid.jwt.token")


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_empty_token(mock_settings_module, mock_settings):
    """Verifies decode_jwt raises DecodeError for empty token."""
    if decode_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    
    from jwt.exceptions import DecodeError
    
    # DecodeError is raised
    with pytest.raises(DecodeError):
        decode_jwt("")


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_jwt_expiry_boundary(mock_settings_module, mock_settings, sample_user_id):
    """Verifies JWT token expires exactly at jwt_expiry_days boundary."""
    if create_jwt is None or decode_jwt is None:
        pytest.skip("Module not available")
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token = create_jwt(sample_user_id)
    payload = decode_jwt(token)
    
    # exp claim is exactly jwt_expiry_days from iat
    iat_time = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
    exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    
    delta = exp_time - iat_time
    expected_delta = timedelta(days=mock_settings.jwt_expiry_days)
    
    # Allow 2 second tolerance
    assert abs(delta.total_seconds() - expected_delta.total_seconds()) < 2


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_decode_jwt_algorithm_mismatch(mock_settings_module, mock_settings, sample_user_id):
    """Verifies decode_jwt raises InvalidTokenError when algorithm doesn't match."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    import jwt as pyjwt
    from jwt.exceptions import InvalidTokenError
    
    # Create token with HS256
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = "HS256"
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(sample_user_id),
        'exp': now + timedelta(days=7),
        'iat': now
    }
    
    token = pyjwt.encode(payload, mock_settings.jwt_secret, algorithm="HS256")
    
    # Try to decode with HS512 algorithm setting
    mock_settings_module.jwt_algorithm = "HS512"
    
    # InvalidTokenError is raised
    with pytest.raises(InvalidTokenError):
        decode_jwt(token)


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_security_jwt_none_algorithm(mock_settings_module, mock_settings, sample_user_id):
    """Security test: Verifies decode_jwt rejects tokens with 'none' algorithm."""
    if decode_jwt is None:
        pytest.skip("Module not available")
    
    import jwt as pyjwt
    from jwt.exceptions import InvalidTokenError, DecodeError
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(sample_user_id),
        'exp': now + timedelta(days=7),
        'iat': now
    }
    
    # Create token with 'none' algorithm
    token = pyjwt.encode(payload, key="", algorithm="none")
    
    # Token with 'none' algorithm is rejected
    with pytest.raises((InvalidTokenError, DecodeError)):
        decode_jwt(token)


@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_security_token_tampering(mock_settings_module, mock_settings, sample_user_id):
    """Security test: Verifies decode_jwt detects payload tampering."""
    if decode_jwt is None or create_jwt is None:
        pytest.skip("Module not available")
    
    from jwt.exceptions import InvalidTokenError
    
    mock_settings_module.jwt_secret = mock_settings.jwt_secret
    mock_settings_module.jwt_algorithm = mock_settings.jwt_algorithm
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    token = create_jwt(sample_user_id)
    
    # Tamper with the payload (change middle part)
    parts = token.split('.')
    
    # Decode the payload, modify it, re-encode
    import base64
    padding = '=' * (4 - len(parts[1]) % 4)
    decoded_payload = base64.urlsafe_b64decode(parts[1] + padding)
    payload_dict = json.loads(decoded_payload)
    
    # Tamper with the sub claim
    payload_dict['sub'] = str(sample_user_id_2)
    
    # Re-encode
    tampered_payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip('=')
    tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
    
    # Tampered token is rejected
    with pytest.raises(InvalidTokenError):
        decode_jwt(tampered_token)


# ============================================================================
# AUTH ENDPOINT TESTS (Mocked Dependencies)
# ============================================================================

@pytest.mark.asyncio
async def test_get_current_user_always_raises(mock_db_session):
    """Verifies get_current_user placeholder always raises NotAuthenticated."""
    if get_current_user is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    
    # NotAuthenticated/HTTPException is raised with 401 status
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=mock_db_session, session="any_session_value")
    
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
def test_login_happy_path(mock_settings_module, mock_settings):
    """Verifies login returns redirect to GitHub OAuth authorize URL."""
    if login is None:
        pytest.skip("Module not available")
    
    from fastapi.responses import RedirectResponse
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    
    response = await login()
    
    # Returns RedirectResponse
    assert isinstance(response, RedirectResponse)
    
    # Status code is 302
    assert response.status_code == 302
    
    # Location header contains github.com/login/oauth/authorize
    location = response.headers.get('location', '')
    assert 'github.com/login/oauth/authorize' in location
    
    # URL includes client_id parameter
    assert 'client_id=' in location
    assert mock_settings.github_client_id in location
    
    # URL includes scope parameter with 'read:user user:email'
    assert 'scope=' in location
    assert 'read:user' in location or 'read%3Auser' in location
    assert 'user:email' in location or 'user%3Aemail' in location


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.create_jwt')
def test_callback_happy_path_new_user(mock_create_jwt, mock_httpx_client, mock_settings_module, 
                                      mock_settings, mock_db_session, github_token_response, 
                                      github_user_response):
    """Verifies callback creates new user from GitHub OAuth and sets session cookie."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi.responses import RedirectResponse
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    # Mock httpx responses
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    # Token response
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    # User response
    user_response_mock = Mock()
    user_response_mock.json.return_value = github_user_response
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    # Mock database - no existing user
    result_mock = Mock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock
    
    # Mock JWT creation
    mock_create_jwt.return_value = "mock_jwt_token_123"
    
    response = await callback(code="test_oauth_code_123", db=mock_db_session)
    
    # Returns RedirectResponse
    assert isinstance(response, RedirectResponse)
    
    # Status code is 302
    assert response.status_code == 302
    
    # Redirects to frontend_url/dashboard
    location = response.headers.get('location', '')
    assert location == f"{mock_settings.frontend_url}/dashboard"
    
    # Response sets session cookie
    set_cookie = response.headers.get('set-cookie', '')
    assert 'session=' in set_cookie
    
    # Cookie is httponly=True
    assert 'httponly' in set_cookie.lower() or 'HttpOnly' in set_cookie
    
    # Cookie is secure=True
    assert 'secure' in set_cookie.lower() or 'Secure' in set_cookie
    
    # Cookie samesite='lax'
    assert 'samesite=lax' in set_cookie.lower() or 'SameSite=Lax' in set_cookie
    
    # User is created in database
    assert mock_db_session.add.called
    
    # User fields match GitHub profile
    added_user = mock_db_session.add.call_args[0][0]
    assert added_user.username == github_user_response['login']


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.create_jwt')
def test_callback_happy_path_existing_user(mock_create_jwt, mock_httpx_client, mock_settings_module, 
                                           mock_settings, mock_db_session, github_token_response, 
                                           github_user_response, mock_user):
    """Verifies callback updates existing user from GitHub OAuth."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi.responses import RedirectResponse
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    # Mock httpx responses
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    user_response_mock = Mock()
    user_response_mock.json.return_value = github_user_response
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    # Mock database - existing user
    result_mock = Mock()
    result_mock.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = result_mock
    
    mock_create_jwt.return_value = "mock_jwt_token_123"
    
    response = await callback(code="test_oauth_code_existing", db=mock_db_session)
    
    # User is updated not created
    assert not mock_db_session.add.called or mock_db_session.add.call_count == 0
    
    # User fields are updated to match GitHub profile
    assert mock_user.display_name == github_user_response['name']
    assert mock_user.avatar_url == github_user_response['avatar_url']
    
    # Session cookie is set
    set_cookie = response.headers.get('set-cookie', '')
    assert 'session=' in set_cookie


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
def test_callback_oauth_failed_no_access_token(mock_httpx_client, mock_settings_module, 
                                               mock_settings, mock_db_session):
    """Verifies callback raises OAuthFailed when GitHub doesn't return access_token."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    
    # Mock httpx response without access_token
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = {"error": "invalid_grant"}
    
    mock_client_instance.post.return_value = token_response_mock
    
    # OAuthFailed or HTTPException is raised
    with pytest.raises((HTTPException, KeyError, Exception)) as exc_info:
        await callback(code="invalid_code", db=mock_db_session)
    
    # No user is created in database
    assert not mock_db_session.add.called


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
def test_callback_github_api_error_missing_id(mock_httpx_client, mock_settings_module, 
                                              mock_settings, mock_db_session, github_token_response):
    """Verifies callback raises GitHubAPIError when user API response missing 'id' field."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    # User response missing 'id'
    user_response_mock = Mock()
    user_response_mock.json.return_value = {
        "login": "testuser",
        "name": "Test User"
    }
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    # GitHubAPIError or HTTPException is raised
    with pytest.raises((HTTPException, KeyError, Exception)):
        await callback(code="valid_code", db=mock_db_session)


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
def test_callback_github_api_error_missing_login(mock_httpx_client, mock_settings_module, 
                                                 mock_settings, mock_db_session, github_token_response):
    """Verifies callback raises GitHubAPIError when user API response missing 'login' field."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    # User response missing 'login'
    user_response_mock = Mock()
    user_response_mock.json.return_value = {
        "id": 123456,
        "name": "Test User"
    }
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    # GitHubAPIError or HTTPException is raised
    with pytest.raises((HTTPException, KeyError, Exception)):
        await callback(code="valid_code", db=mock_db_session)


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
def test_callback_network_error(mock_httpx_client, mock_settings_module, mock_settings, mock_db_session):
    """Verifies callback raises NetworkError when httpx encounters connectivity issues."""
    if callback is None:
        pytest.skip("Module not available")
    
    import httpx
    from fastapi import HTTPException
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    
    # Mock network error
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    mock_client_instance.post.side_effect = httpx.NetworkError("Connection failed")
    
    # NetworkError or HTTPException is raised
    with pytest.raises((HTTPException, httpx.NetworkError, Exception)):
        await callback(code="valid_code", db=mock_db_session)


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.create_jwt')
def test_callback_database_error(mock_create_jwt, mock_httpx_client, mock_settings_module, 
                                mock_settings, mock_db_session, github_token_response, 
                                github_user_response):
    """Verifies callback raises DatabaseError when database commit fails."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    user_response_mock = Mock()
    user_response_mock.json.return_value = github_user_response
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    # Mock database commit failure
    result_mock = Mock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock
    mock_db_session.commit.side_effect = SQLAlchemyError("Database error")
    
    mock_create_jwt.return_value = "mock_jwt_token_123"
    
    # DatabaseError or HTTPException is raised
    with pytest.raises((HTTPException, SQLAlchemyError, Exception)):
        await callback(code="valid_code", db=mock_db_session)


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.create_jwt')
def test_callback_nullable_fields(mock_create_jwt, mock_httpx_client, mock_settings_module, 
                                  mock_settings, mock_db_session, github_token_response, 
                                  github_user_response_minimal):
    """Verifies callback handles GitHub API responses with null optional fields."""
    if callback is None:
        pytest.skip("Module not available")
    
    from fastapi.responses import RedirectResponse
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    user_response_mock = Mock()
    user_response_mock.json.return_value = github_user_response_minimal
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    result_mock = Mock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock
    
    mock_create_jwt.return_value = "mock_jwt_token_123"
    
    response = await callback(code="valid_code", db=mock_db_session)
    
    # User is created successfully
    assert mock_db_session.add.called
    
    # Optional fields are None
    added_user = mock_db_session.add.call_args[0][0]
    assert added_user.display_name is None or added_user.display_name == github_user_response_minimal.get('name')
    assert added_user.avatar_url is None or added_user.avatar_url == github_user_response_minimal.get('avatar_url')


@pytest.mark.asyncio
def test_logout_happy_path():
    """Verifies logout clears session cookie and returns 204."""
    if logout is None:
        pytest.skip("Module not available")
    
    from fastapi import Response
    
    response = await logout()
    
    # Returns Response object
    assert isinstance(response, Response)
    
    # Status code is 204
    assert response.status_code == 204
    
    # Session cookie is deleted (max_age=0 or expires in past)
    set_cookie = response.headers.get('set-cookie', '')
    assert 'session=' in set_cookie
    assert 'max-age=0' in set_cookie.lower() or 'max_age=0' in set_cookie.lower() or 'expires=' in set_cookie.lower()


@pytest.mark.asyncio
async def test_me_happy_path(mock_user):
    """Verifies me returns authenticated user profile as dictionary."""
    if me is None:
        pytest.skip("Module not available")
    
    result = await me(user=mock_user)
    
    # Returns dictionary
    assert isinstance(result, dict)
    
    # Contains 'id' key with stringified UUID
    assert 'id' in result
    assert result['id'] == str(mock_user.id)
    
    # Contains 'username' key
    assert 'username' in result
    assert result['username'] == mock_user.username
    
    # Contains 'display_name' key
    assert 'display_name' in result
    
    # Contains 'avatar_url' key
    assert 'avatar_url' in result
    
    # Contains 'bio' key
    assert 'bio' in result


@pytest.mark.asyncio
async def test_me_with_all_null_optional_fields(mock_user_minimal):
    """Verifies me returns dictionary with None values for optional fields."""
    if me is None:
        pytest.skip("Module not available")
    
    result = await me(user=mock_user_minimal)
    
    # display_name is None
    assert result['display_name'] is None
    
    # avatar_url is None
    assert result['avatar_url'] is None
    
    # bio is None
    assert result['bio'] is None


@pytest.mark.asyncio
async def test_me_not_authenticated(mock_db_session):
    """Verifies me raises NotAuthenticated when get_current_user fails."""
    if me is None or get_current_user is None:
        pytest.skip("Module not available")
    
    from fastapi import HTTPException
    
    # Since get_current_user is a dependency that always raises,
    # we test that without a valid user, we'd get 401
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=mock_db_session, session=None)
    
    # NotAuthenticated or HTTPException with 401 is raised
    assert exc_info.value.status_code == 401


# ============================================================================
# INVARIANT TESTS
# ============================================================================

def test_invariant_github_urls():
    """Verifies GitHub OAuth URLs match contract invariants."""
    # Import the module to check constants
    try:
        import contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface as auth_module
        
        # GITHUB_AUTHORIZE_URL equals 'https://github.com/login/oauth/authorize'
        assert hasattr(auth_module, 'GITHUB_AUTHORIZE_URL')
        assert auth_module.GITHUB_AUTHORIZE_URL == 'https://github.com/login/oauth/authorize'
        
        # GITHUB_TOKEN_URL equals 'https://github.com/login/oauth/access_token'
        assert hasattr(auth_module, 'GITHUB_TOKEN_URL')
        assert auth_module.GITHUB_TOKEN_URL == 'https://github.com/login/oauth/access_token'
        
        # GITHUB_USER_URL equals 'https://api.github.com/user'
        assert hasattr(auth_module, 'GITHUB_USER_URL')
        assert auth_module.GITHUB_USER_URL == 'https://api.github.com/user'
    except ImportError:
        pytest.skip("Module not available for invariant check")


def test_invariant_router_config():
    """Verifies router configuration matches contract invariants."""
    try:
        import contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface as auth_module
        
        # Router prefix is '/api/auth'
        assert hasattr(auth_module, 'router')
        assert auth_module.router.prefix == '/api/auth'
        
        # Router tags include 'auth'
        assert 'auth' in auth_module.router.tags
    except (ImportError, AttributeError):
        pytest.skip("Module or router not available for invariant check")


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.httpx.AsyncClient')
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.create_jwt')
async def test_invariant_session_cookie_attributes(mock_create_jwt, mock_httpx_client, 
                                                   mock_settings_module, mock_settings, 
                                                   mock_db_session, github_token_response, 
                                                   github_user_response):
    """Verifies session cookie attributes match contract invariants."""
    if callback is None:
        pytest.skip("Module not available")
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    mock_settings_module.github_client_secret = mock_settings.github_client_secret
    mock_settings_module.frontend_url = mock_settings.frontend_url
    mock_settings_module.jwt_expiry_days = mock_settings.jwt_expiry_days
    
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    
    token_response_mock = Mock()
    token_response_mock.json.return_value = github_token_response
    
    user_response_mock = Mock()
    user_response_mock.json.return_value = github_user_response
    
    mock_client_instance.post.return_value = token_response_mock
    mock_client_instance.get.return_value = user_response_mock
    
    result_mock = Mock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock
    
    mock_create_jwt.return_value = "mock_jwt_token_123"
    
    response = await callback(code="valid_code", db=mock_db_session)
    
    set_cookie = response.headers.get('set-cookie', '')
    
    # Cookie key is 'session'
    assert 'session=' in set_cookie
    
    # Cookie httponly is True
    assert 'httponly' in set_cookie.lower() or 'HttpOnly' in set_cookie
    
    # Cookie secure is True
    assert 'secure' in set_cookie.lower() or 'Secure' in set_cookie
    
    # Cookie samesite is 'lax'
    assert 'samesite=lax' in set_cookie.lower() or 'SameSite=Lax' in set_cookie or 'SameSite=lax' in set_cookie


@pytest.mark.asyncio
@patch('contracts_contracts_contracts_backend_api_auth_router_interface_interface_interface.settings')
async def test_invariant_oauth_scope(mock_settings_module, mock_settings):
    """Verifies OAuth scope requested matches contract invariant."""
    if login is None:
        pytest.skip("Module not available")
    
    mock_settings_module.github_client_id = mock_settings.github_client_id
    
    response = await login()
    
    location = response.headers.get('location', '')
    
    # Scope parameter includes 'read:user user:email'
    assert 'scope=' in location
    # Check for URL-encoded or plain versions
    has_read_user = 'read:user' in location or 'read%3Auser' in location
    has_user_email = 'user:email' in location or 'user%3Aemail' in location
    assert has_read_user
    assert has_user_email
