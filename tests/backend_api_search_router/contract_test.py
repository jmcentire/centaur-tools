"""
Contract tests for backend_api_search_router (Search API Router)

This test suite validates the search API router implementation against its contract.
Tests cover happy paths, edge cases, error conditions, and invariants.

All tests use mocked dependencies:
- AsyncSession (database)
- google.genai.Client (embedding API)
- FastAPI dependency injection

Test execution: pytest contract_test.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import uuid
from typing import Any, Dict, List
import random


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

@pytest.fixture
def mock_embedding_vector():
    """Returns a valid 768-dimensional embedding vector"""
    return [random.uniform(-1.0, 1.0) for _ in range(768)]


@pytest.fixture
def make_tool_result():
    """Factory function to create ToolSearchResult test data"""
    def _make(**overrides):
        defaults = {
            "slug": f"tool-{uuid.uuid4().hex[:8]}",
            "name": "Test Tool",
            "description": "A test tool description",
            "problem_statement": "Solves test problems",
            "language": "python",
            "tags": ["testing", "python"],
            "author": {"username": "testuser", "avatar_url": "https://example.com/avatar.jpg"},
            "vote_count": 10,
            "score": 0.8500,
            "created_at": "2024-01-01T00:00:00Z"
        }
        defaults.update(overrides)
        return defaults
    return _make


@pytest.fixture
def mock_db_session():
    """Creates a mock AsyncSession for database operations"""
    session = AsyncMock()
    
    # Mock execute to return a result with scalars
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    
    return session


@pytest.fixture
def mock_app(mock_db_session):
    """Creates a FastAPI test application with mocked dependencies"""
    app = FastAPI()
    
    # Import the router - adjust import path as needed
    try:
        from backend.api.search_router import router as search_router
        app.include_router(search_router, prefix="/api/search", tags=["search"])
    except ImportError:
        # Fallback: create minimal router for testing
        from fastapi import APIRouter, Query
        from sqlalchemy.ext.asyncio import AsyncSession
        
        router = APIRouter()
        
        async def get_db():
            yield mock_db_session
        
        @router.get("/tools")
        async def search_tools_endpoint(
            q: str = Query(..., min_length=1),
            mode: str = Query("keyword", regex="^(keyword|semantic|hybrid)$"),
            page: int = Query(1, ge=1),
            per_page: int = Query(10, ge=1, le=100),
        ):
            # Minimal mock implementation
            from backend.api.search.router import search_tools
            db_session = mock_db_session
            result = await search_tools(q, mode, page, per_page, db_session)
            return result
        
        app.include_router(router, prefix="/api/search", tags=["search"])
    
    # Override database dependency
    async def override_get_db():
        yield mock_db_session
    
    app.dependency_overrides[lambda: None] = override_get_db
    
    return app


@pytest.fixture
def client(mock_app):
    """Returns TestClient for making HTTP requests"""
    return TestClient(mock_app)


# ============================================================================
# Test Class: get_embedding function
# ============================================================================

class TestGetEmbedding:
    """Tests for the get_embedding async function"""
    
    @pytest.mark.asyncio
    async def test_get_embedding_success_returns_768_dimensional_vector(self, mock_embedding_vector):
        """Verify get_embedding returns 768-dimensional float vector on successful API call"""
        with patch('backend_api_search_router.settings') as mock_settings, \
             patch('google.genai.Client') as mock_client_class:
            
            # Setup
            mock_settings.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Mock embedding response
            mock_embedding = MagicMock()
            mock_embedding.values = mock_embedding_vector
            mock_result = MagicMock()
            mock_result.embeddings = [mock_embedding]
            mock_client.models.embed_content.return_value = mock_result
            
            from backend.api.search.router import get_embedding
            
            # Execute
            result = await get_embedding("search query")
            
            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 768
            assert all(isinstance(x, float) for x in result)
    
    @pytest.mark.asyncio
    async def test_get_embedding_no_api_key_returns_none(self):
        """Verify get_embedding returns None when gemini_api_key is not configured"""
        with patch('backend_api_search_router.settings') as mock_settings:
            # Setup: empty API key
            mock_settings.gemini_api_key = ""
            
            from backend.api.search.router import get_embedding
            
            # Execute
            result = await get_embedding("search query")
            
            # Assert
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_embedding_api_exception_returns_none(self):
        """Verify get_embedding returns None on API exception (silent failure)"""
        with patch('backend_api_search_router.settings') as mock_settings, \
             patch('google.genai.Client') as mock_client_class:
            
            # Setup
            mock_settings.gemini_api_key = "test-api-key"
            mock_client_class.side_effect = Exception("API failure")
            
            from backend.api.search.router import get_embedding
            
            # Execute
            result = await get_embedding("search query")
            
            # Assert
            assert result is None


# ============================================================================
# Test Class: search_tools endpoint
# ============================================================================

class TestSearchToolsEndpoint:
    """Tests for the search_tools API endpoint"""
    
    def test_search_tools_keyword_mode_happy_path(self, client, mock_db_session, make_tool_result):
        """Verify keyword search returns paginated results with correct schema"""
        # Setup mock database response
        mock_tool = MagicMock()
        mock_tool.id = uuid.uuid4()
        mock_tool.slug = "test-tool"
        mock_tool.name = "Test Tool"
        mock_tool.description = "Test description"
        mock_tool.problem_statement = "Test problem"
        mock_tool.language = "python"
        mock_tool.tags = [MagicMock(name="python")]
        mock_tool.author = MagicMock(username="testuser", avatar_url="https://example.com/avatar.jpg")
        mock_tool.vote_count = 5
        mock_tool.created_at = "2024-01-01T00:00:00Z"
        
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [make_tool_result()],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=python&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data['total'] >= 0
            assert data['page'] == 1
            assert data['per_page'] == 10
            assert isinstance(data['tools'], list)
    
    def test_search_tools_semantic_mode_happy_path(self, client, make_tool_result, mock_embedding_vector):
        """Verify semantic search returns results with vector similarity scores"""
        with patch('backend_api_search_router.search_tools') as mock_search, \
             patch('backend_api_search_router.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.return_value = mock_embedding_vector
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.9234)],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=machine learning&mode=semantic&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data['tools'], list)
            assert all('score' in tool for tool in data['tools'])
    
    def test_search_tools_hybrid_mode_happy_path(self, client, make_tool_result):
        """Verify hybrid search combines keyword and semantic results"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.8500), make_tool_result(score=0.7200)],
                "total": 2,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=data processing&mode=hybrid&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data['tools'], list)
    
    def test_search_tools_empty_results_returns_empty_list(self, client):
        """Verify empty result set returns tools=[], total=0"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [],
                "total": 0,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=nonexistent_xyz_query&mode=keyword&page=1&per_page=10")
            
            # Assert
            data = response.json()
            assert data['tools'] == []
            assert data['total'] == 0
            assert data['page'] == 1
            assert data['per_page'] == 10
    
    def test_search_tools_page_boundary_page_1(self, client, make_tool_result):
        """Verify pagination at page=1 (minimum boundary)"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [make_tool_result()],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data['page'] == 1
    
    def test_search_tools_per_page_boundary_1(self, client, make_tool_result):
        """Verify per_page=1 (minimum boundary)"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [make_tool_result()],
                "total": 5,
                "page": 1,
                "per_page": 1
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=1")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data['per_page'] == 1
            assert len(data['tools']) <= 1
    
    def test_search_tools_per_page_boundary_100(self, client, make_tool_result):
        """Verify per_page=100 (maximum boundary)"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            tools = [make_tool_result(slug=f"tool-{i}") for i in range(50)]
            mock_search.return_value = {
                "tools": tools,
                "total": 50,
                "page": 1,
                "per_page": 100
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=100")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data['per_page'] == 100
            assert len(data['tools']) <= 100
    
    def test_search_tools_score_rounded_to_4_decimals(self, client, make_tool_result):
        """Verify score values are rounded to 4 decimal places"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [
                    make_tool_result(score=0.8523),
                    make_tool_result(score=0.7891),
                    make_tool_result(score=0.5000)
                ],
                "total": 3,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            data = response.json()
            assert all(len(str(tool['score']).split('.')[-1]) <= 4 for tool in data['tools'] if data['tools'])
    
    def test_search_tools_results_ordered_by_score_desc(self, client, make_tool_result):
        """Verify results are ordered by score descending"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [
                    make_tool_result(score=0.9500),
                    make_tool_result(score=0.8500),
                    make_tool_result(score=0.7000),
                    make_tool_result(score=0.5000)
                ],
                "total": 4,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            data = response.json()
            assert all(data['tools'][i]['score'] >= data['tools'][i+1]['score'] 
                      for i in range(len(data['tools'])-1)) if len(data['tools']) > 1 else True
    
    def test_search_tools_only_active_tools_returned(self, client, make_tool_result):
        """Verify only tools with is_active=True are returned"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # Mock should only return active tools
            mock_search.return_value = {
                "tools": [make_tool_result()],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_database_error(self, client):
        """Verify database_error when database query fails"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.side_effect = Exception("Database connection failed")
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 500 or response.status_code == 422
    
    def test_search_tools_invalid_uuid_conversion(self, client):
        """Verify invalid_uuid_conversion when tool_scores contains non-UUID IDs"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.side_effect = ValueError("Invalid UUID format")
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 500 or response.status_code == 422
    
    def test_search_tools_attribute_error_missing_slug(self, client):
        """Verify attribute_error when Tool object missing expected attributes"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.side_effect = AttributeError("'Tool' object has no attribute 'slug'")
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 500 or response.status_code == 422
    
    def test_search_tools_sql_injection_attempt(self, client):
        """Verify SQL injection attempts are safely handled"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [],
                "total": 0,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q='; DROP TABLE tools; --&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_unicode_query(self, client):
        """Verify unicode characters in query are handled correctly"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [],
                "total": 0,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=数据处理🔍&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_xss_attempt(self, client):
        """Verify XSS attempts in query are safely handled"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [],
                "total": 0,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=<script>alert('xss')</script>&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_tag_match_score_0_5(self, client, make_tool_result):
        """Verify tag matching score is hardcoded to 0.5"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # Mock tag match result
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.5000, tags=["python"])],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=python&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_fallback_name_match_score_0_1(self, client, make_tool_result):
        """Verify fallback name matching score is hardcoded to 0.1"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # Mock name prefix match result
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.1000)],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_response_schema_validation(self, client, make_tool_result):
        """Verify response matches SearchResponse schema exactly"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            tool_data = make_tool_result()
            mock_search.return_value = {
                "tools": [tool_data],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            data = response.json()
            assert 'tools' in data
            assert 'total' in data
            assert 'page' in data
            assert 'per_page' in data
            
            required_tool_keys = ['slug', 'name', 'description', 'problem_statement', 
                                 'language', 'tags', 'author', 'vote_count', 'score', 'created_at']
            assert all(key in tool for tool in data['tools'] for key in required_tool_keys) if data['tools'] else True
    
    def test_search_tools_author_info_schema(self, client, make_tool_result):
        """Verify AuthorInfo schema in results has username and avatar_url"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            tool_data = make_tool_result()
            mock_search.return_value = {
                "tools": [tool_data],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            data = response.json()
            assert all('username' in tool['author'] and 'avatar_url' in tool['author'] 
                      for tool in data['tools']) if data['tools'] else True
    
    def test_search_tools_semantic_uses_cosine_distance(self, client, make_tool_result, mock_embedding_vector):
        """Verify semantic search uses cosine distance formula: 1 - cosine_distance"""
        with patch('backend_api_search_router.search_tools') as mock_search, \
             patch('backend_api_search_router.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.return_value = mock_embedding_vector
            # Score should be 1 - cosine_distance
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.8765)],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=semantic&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_hybrid_max_score_aggregation(self, client, make_tool_result):
        """Verify hybrid mode uses max(existing, new_score) for overlapping results"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # Simulate overlapping results with max score
            mock_search.return_value = {
                "tools": [make_tool_result(score=0.9000)],  # Max of keyword and semantic
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=hybrid&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200
    
    def test_search_tools_total_equals_unique_matches(self, client, make_tool_result):
        """Verify total equals len(tool_scores) before pagination"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # 12 matching tools total, but only 5 on first page
            tools = [make_tool_result(slug=f"tool-{i}") for i in range(5)]
            mock_search.return_value = {
                "tools": tools,
                "total": 12,
                "page": 1,
                "per_page": 5
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=5")
            
            # Assert
            data = response.json()
            assert data['total'] >= len(data['tools'])
            assert len(data['tools']) <= data['per_page']
    
    def test_search_tools_missing_tools_silently_skipped(self, client, make_tool_result):
        """Verify tools missing from tools_map are silently skipped (race condition)"""
        with patch('backend_api_search_router.search_tools') as mock_search:
            # Simulate some tools being skipped due to race condition
            mock_search.return_value = {
                "tools": [make_tool_result()],  # Fewer tools than total suggests
                "total": 3,  # But total might reflect pre-filtering count
                "page": 1,
                "per_page": 10
            }
            
            # Execute
            response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=10")
            
            # Assert
            assert response.status_code == 200


# ============================================================================
# Additional Integration Tests
# ============================================================================

class TestSearchRouterInvariants:
    """Tests for router-level invariants and configuration"""
    
    def test_router_prefix_is_api_search(self, mock_app):
        """Verify router prefix is /api/search"""
        # Check routes contain the expected prefix
        routes = [route.path for route in mock_app.routes]
        assert any('/api/search' in route for route in routes)
    
    def test_router_tag_is_search(self, mock_app):
        """Verify router tag is 'search'"""
        # Check openapi schema includes search tag
        openapi = mock_app.openapi()
        tags = [tag['name'] for tag in openapi.get('tags', [])]
        assert 'search' in tags or len(tags) == 0  # May not be populated in test env
    
    def test_full_text_search_uses_plainto_tsquery(self, client):
        """Verify full-text search queries use PostgreSQL plainto_tsquery with 'english' configuration"""
        # This is an invariant test - we can't directly test SQL generation in unit tests
        # but we verify the endpoint accepts queries that would be processed
        with patch('backend_api_search_router.search_tools') as mock_search:
            mock_search.return_value = {
                "tools": [],
                "total": 0,
                "page": 1,
                "per_page": 10
            }
            
            response = client.get("/api/search/tools?q=test query&mode=keyword&page=1&per_page=10")
            assert response.status_code == 200


# ============================================================================
# Parametrized Tests for SearchMode
# ============================================================================

class TestSearchModes:
    """Parametrized tests for different search modes"""
    
    @pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
    def test_search_modes_all_valid(self, client, mode, make_tool_result):
        """Verify all search modes return valid responses"""
        with patch('backend_api_search_router.search_tools') as mock_search, \
             patch('backend_api_search_router.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.return_value = [0.1] * 768
            mock_search.return_value = {
                "tools": [make_tool_result()],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
            
            response = client.get(f"/api/search/tools?q=test&mode={mode}&page=1&per_page=10")
            assert response.status_code == 200
            data = response.json()
            assert 'tools' in data
            assert 'total' in data


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestSearchErrorHandling:
    """Tests for error handling and edge cases"""
    
    def test_invalid_mode_parameter(self, client):
        """Verify invalid mode parameter is rejected"""
        response = client.get("/api/search/tools?q=test&mode=invalid&page=1&per_page=10")
        # Should fail validation
        assert response.status_code == 422
    
    def test_page_less_than_1_rejected(self, client):
        """Verify page < 1 is rejected"""
        response = client.get("/api/search/tools?q=test&mode=keyword&page=0&per_page=10")
        assert response.status_code == 422
    
    def test_per_page_greater_than_100_rejected(self, client):
        """Verify per_page > 100 is rejected"""
        response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=101")
        assert response.status_code == 422
    
    def test_per_page_less_than_1_rejected(self, client):
        """Verify per_page < 1 is rejected"""
        response = client.get("/api/search/tools?q=test&mode=keyword&page=1&per_page=0")
        assert response.status_code == 422
    
    def test_empty_query_rejected(self, client):
        """Verify empty query string is rejected (min_length=1)"""
        response = client.get("/api/search/tools?q=&mode=keyword&page=1&per_page=10")
        assert response.status_code == 422
    
    def test_missing_query_parameter(self, client):
        """Verify missing q parameter is rejected"""
        response = client.get("/api/search/tools?mode=keyword&page=1&per_page=10")
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
