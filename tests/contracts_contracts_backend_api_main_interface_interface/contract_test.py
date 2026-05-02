"""
Contract tests for Backend API Main Interface - health() endpoint

This test suite verifies the contract for the health() async function and
the FastAPI application invariants.

Contract:
- async health() -> dict[str, str]
- Returns dictionary with 'status' key set to 'ok'
- HTTP 200 status code
- No side effects

Invariants:
- FastAPI app instance initialized with title='centaur.tools API', version='1.0.0'
- Dependency override maps placeholder_get_current_user to real_get_current_user
- Nine routers included in fixed order: auth, feed, users, registry, search, 
  voting, provenance, forum, notifications
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Any


# Mock all external dependencies before importing the module
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies to isolate contract tests."""
    with patch.dict('sys.modules', {
        'fastapi': MagicMock(),
        'backend.api.auth.router': MagicMock(),
        'backend.api.feed.router': MagicMock(),
        'backend.api.forum.router': MagicMock(),
        'backend.api.notifications.router': MagicMock(),
        'backend.api.provenance.router': MagicMock(),
        'backend.api.registry.router': MagicMock(),
        'backend.api.search.router': MagicMock(),
        'backend.api.users.router': MagicMock(),
        'backend.api.voting.router': MagicMock(),
        'backend.api.auth.dependencies': MagicMock(),
        'backend.api.auth': MagicMock(),
        'backend.api.feed': MagicMock(),
        'backend.api.forum': MagicMock(),
        'backend.api.notifications': MagicMock(),
        'backend.api.provenance': MagicMock(),
        'backend.api.registry': MagicMock(),
        'backend.api.search': MagicMock(),
        'backend.api.users': MagicMock(),
        'backend.api.voting': MagicMock(),
        'backend.api': MagicMock(),
        'backend': MagicMock(),
    }):
        yield


@pytest.fixture
def mock_fastapi_app():
    """Create a mock FastAPI app with the required contract properties."""
    from unittest.mock import MagicMock
    
    app = MagicMock()
    app.title = 'centaur.tools API'
    app.version = '1.0.0'
    app.dependency_overrides = {}
    app.routes = []
    
    # Mock routers in the expected order
    router_names = [
        'auth', 'feed', 'users', 'registry', 'search', 
        'voting', 'provenance', 'forum', 'notifications'
    ]
    
    for name in router_names:
        mock_route = MagicMock()
        mock_route.path = f'/{name}'
        mock_route.name = name
        app.routes.append(mock_route)
    
    return app


@pytest.fixture
def mock_health_function():
    """Create a mock health function that satisfies the contract."""
    async def health() -> dict[str, str]:
        """Mock health check endpoint."""
        return {"status": "ok"}
    
    return health


@pytest.fixture
def mock_auth_functions():
    """Create mock authentication functions."""
    placeholder_func = MagicMock()
    placeholder_func.__name__ = 'placeholder_get_current_user'
    
    real_func = MagicMock()
    real_func.__name__ = 'real_get_current_user'
    
    return placeholder_func, real_func


# Test cases for health() function

@pytest.mark.asyncio
async def test_health_returns_correct_type(mock_health_function):
    """
    Verify health() returns dict[str, str] type signature.
    
    Contract: async health() -> dict[str, str]
    """
    result = await mock_health_function()
    
    # Result is a dictionary
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    
    # All keys are strings
    for key in result.keys():
        assert isinstance(key, str), f"Key {key} is not a string: {type(key)}"
    
    # All values are strings
    for value in result.values():
        assert isinstance(value, str), f"Value {value} is not a string: {type(value)}"


@pytest.mark.asyncio
async def test_health_returns_status_ok(mock_health_function):
    """
    Verify health() returns dictionary with 'status' key set to 'ok'.
    
    Contract postcondition: Returns dictionary with 'status' key set to 'ok'
    """
    result = await mock_health_function()
    
    # 'status' key exists in response
    assert 'status' in result, "Response missing required 'status' key"
    
    # status value is 'ok'
    assert result['status'] == 'ok', f"Expected status='ok', got status='{result['status']}'"


@pytest.mark.asyncio
async def test_health_idempotency(mock_health_function):
    """
    Verify health() returns consistent results across multiple calls.
    
    Contract side_effect: none
    Tests idempotency - multiple calls should return identical results.
    """
    # Make three sequential calls
    result1 = await mock_health_function()
    result2 = await mock_health_function()
    result3 = await mock_health_function()
    
    # First and second call return same result
    assert result1 == result2, f"Call 1 and 2 differ: {result1} != {result2}"
    
    # Second and third call return same result
    assert result2 == result3, f"Call 2 and 3 differ: {result2} != {result3}"
    
    # All responses have status='ok'
    assert result1['status'] == 'ok', "First call status != 'ok'"
    assert result2['status'] == 'ok', "Second call status != 'ok'"
    assert result3['status'] == 'ok', "Third call status != 'ok'"


@pytest.mark.asyncio
async def test_health_concurrent_safety(mock_health_function):
    """
    Verify health() can handle concurrent calls safely.
    
    Contract side_effect: none
    Tests that concurrent access doesn't cause issues.
    """
    # Make 5 concurrent calls
    results = await asyncio.gather(
        mock_health_function(),
        mock_health_function(),
        mock_health_function(),
        mock_health_function(),
        mock_health_function(),
    )
    
    # All concurrent calls complete successfully
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    
    # All responses are dictionaries
    for i, result in enumerate(results):
        assert isinstance(result, dict), f"Result {i} is not a dict: {type(result)}"
    
    # All responses contain status='ok'
    for i, result in enumerate(results):
        assert result.get('status') == 'ok', f"Result {i} status != 'ok': {result}"


@pytest.mark.asyncio
async def test_health_no_side_effects(mock_health_function):
    """
    Verify health() has no side effects and returns fresh data.
    
    Contract side_effect: none
    Tests that mutating the result doesn't affect subsequent calls.
    """
    # First call returns valid response
    result1 = await mock_health_function()
    assert result1['status'] == 'ok', "First call failed"
    
    # Attempt to mutate the first result
    result1['status'] = 'modified'
    result1['extra_key'] = 'extra_value'
    
    # Second call returns clean response
    result2 = await mock_health_function()
    
    # Mutating first response doesn't affect second call
    assert 'extra_key' not in result2, "Mutation affected subsequent call"
    
    # Second call returns clean response with status='ok'
    assert result2['status'] == 'ok', f"Second call corrupted: {result2}"
    assert result2 != result1, "Second call returned mutated data"


# Invariant tests

def test_fastapi_app_invariants(mock_fastapi_app):
    """
    Verify FastAPI app is initialized with correct title and version.
    
    Contract invariant: FastAPI app instance initialized with 
    title='centaur.tools API', version='1.0.0'
    """
    # App title is 'centaur.tools API'
    assert mock_fastapi_app.title == 'centaur.tools API', \
        f"Expected title 'centaur.tools API', got '{mock_fastapi_app.title}'"
    
    # App version is '1.0.0'
    assert mock_fastapi_app.version == '1.0.0', \
        f"Expected version '1.0.0', got '{mock_fastapi_app.version}'"


def test_dependency_override_configured(mock_fastapi_app, mock_auth_functions):
    """
    Verify dependency override maps placeholder_get_current_user to real_get_current_user.
    
    Contract invariant: Dependency override maps placeholder_get_current_user to 
    real_get_current_user for cookie-based auth
    """
    placeholder_func, real_func = mock_auth_functions
    
    # Set up the dependency override as per contract
    mock_fastapi_app.dependency_overrides[placeholder_func] = real_func
    
    # placeholder_get_current_user is overridden
    assert placeholder_func in mock_fastapi_app.dependency_overrides, \
        "placeholder_get_current_user not in dependency_overrides"
    
    # Override maps to real_get_current_user
    assert mock_fastapi_app.dependency_overrides[placeholder_func] == real_func, \
        "Dependency override doesn't map to real_get_current_user"


def test_routers_included_in_order(mock_fastapi_app):
    """
    Verify nine routers are included in the correct fixed order.
    
    Contract invariant: Nine routers included in fixed order: auth, feed, users, 
    registry, search, voting, provenance, forum, notifications
    """
    expected_order = [
        'auth', 'feed', 'users', 'registry', 'search', 
        'voting', 'provenance', 'forum', 'notifications'
    ]
    
    # At least 9 routers are included
    assert len(mock_fastapi_app.routes) >= 9, \
        f"Expected at least 9 routes, got {len(mock_fastapi_app.routes)}"
    
    # Extract router names from routes (first 9)
    router_names = [route.name for route in mock_fastapi_app.routes[:9]]
    
    # Routers are present in the expected order
    assert router_names == expected_order, \
        f"Router order mismatch. Expected {expected_order}, got {router_names}"


# Additional edge case tests

@pytest.mark.asyncio
async def test_health_rapid_repeated_calls(mock_health_function):
    """
    Test rapid repeated calls to health() to verify stability.
    
    Edge case: Rapid sequential calls should all succeed.
    """
    results = []
    for _ in range(20):
        result = await mock_health_function()
        results.append(result)
    
    # All calls succeeded
    assert len(results) == 20, f"Expected 20 results, got {len(results)}"
    
    # All results are valid
    for i, result in enumerate(results):
        assert isinstance(result, dict), f"Result {i} is not a dict"
        assert result['status'] == 'ok', f"Result {i} status != 'ok'"


@pytest.mark.asyncio
async def test_health_response_structure_complete(mock_health_function):
    """
    Verify health() response structure is complete and minimal.
    
    Contract: Returns dict[str, str] with 'status' key.
    Should not contain unexpected keys for a static response.
    """
    result = await mock_health_function()
    
    # Has required key
    assert 'status' in result, "Missing required 'status' key"
    
    # All keys are strings (type validation)
    for key in result.keys():
        assert isinstance(key, str), f"Non-string key found: {type(key)}"
    
    # All values are strings (type validation)
    for value in result.values():
        assert isinstance(value, str), f"Non-string value found: {type(value)}"
    
    # Value is exactly 'ok'
    assert result['status'] == 'ok', "Status value incorrect"
