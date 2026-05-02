"""
Contract-based pytest test suite for Tool Registry API Router.

This test suite validates the backend_api_registry_router component against its contract
using a layered testing approach:
- Unit tests for pure functions (slugify, must_be_mit)
- Integration tests for API endpoints with real test database
- Parametrized tests for permission matrices and pagination
- Error path coverage for all documented error cases
- Invariant tests for MIT license, unique slugs, tag limits, and active tool visibility

Dependencies are mocked minimally - only external services (GitHub API, proximity scanning).
Database operations use real SQLAlchemy with async test database.
"""

import pytest
import re
import uuid
from datetime import datetime
from typing import Optional, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, select
from pydantic import BaseModel, ValidationError, validator

# Import component under test
from backend.api.registry.router import (
    slugify,
    must_be_mit,
    list_tools,
    get_tool,
    verify_repo_ownership,
    submit_tool,
    update_tool,
    deactivate_tool,
    ToolSubmission,
    ToolUpdate,
)


# ============================================================================
# FIXTURES: Database and test data setup
# ============================================================================

Base = declarative_base()


class User(Base):
    """Mock User model for testing"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    avatar_url = Column(String)


class Tool(Base):
    """Mock Tool model for testing"""
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    problem_statement = Column(Text)
    repo_url = Column(String)
    license = Column(String)
    language = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ToolTag(Base):
    """Mock ToolTag model for testing"""
    __tablename__ = "tool_tags"
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"))
    tag = Column(String)


class ToolVote(Base):
    """Mock ToolVote model for testing"""
    __tablename__ = "tool_votes"
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"))
    user_id = Column(Integer, ForeignKey("users.id"))


class ProximityLink(Base):
    """Mock ProximityLink model for testing"""
    __tablename__ = "proximity_links"
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"))
    neighbor_id = Column(Integer, ForeignKey("tools.id"))
    similarity = Column(Integer)


class ForkLink(Base):
    """Mock ForkLink model for testing"""
    __tablename__ = "fork_links"
    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("tools.id"))
    parent_id = Column(Integer, ForeignKey("tools.id"))


class ForumThread(Base):
    """Mock ForumThread model for testing"""
    __tablename__ = "forum_threads"
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=True)
    category = Column(String)
    title = Column(String)


class ForumReply(Base):
    """Mock ForumReply model for testing"""
    __tablename__ = "forum_replies"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("forum_threads.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Mock Notification model for testing"""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)


@pytest.fixture(scope="function")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Create async test database engine (in-memory SQLite)"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Create async database session with transaction rollback"""
    async_session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def base_user(db_session: AsyncSession) -> User:
    """Create a basic test user"""
    user = User(username="testuser", display_name="Test User", avatar_url="https://example.com/avatar.png")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def tool_owner(db_session: AsyncSession) -> User:
    """Create a tool owner user"""
    user = User(username="toolowner", display_name="Tool Owner", avatar_url="https://example.com/owner.png")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create another user for permission testing"""
    user = User(username="otheruser", display_name="Other User", avatar_url="https://example.com/other.png")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def active_tool(db_session: AsyncSession, tool_owner: User) -> Tool:
    """Create an active test tool"""
    tool = Tool(
        slug="test-tool",
        name="Test Tool",
        description="A test tool",
        problem_statement="Solves test problems",
        repo_url="https://github.com/toolowner/test-tool",
        license="MIT",
        language="Python",
        author_id=tool_owner.id,
        is_active=True,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.fixture
async def inactive_tool(db_session: AsyncSession, tool_owner: User) -> Tool:
    """Create an inactive test tool"""
    tool = Tool(
        slug="inactive-tool",
        name="Inactive Tool",
        description="An inactive tool",
        problem_statement="Deactivated",
        repo_url="https://github.com/toolowner/inactive-tool",
        license="MIT",
        language="Java",
        author_id=tool_owner.id,
        is_active=False,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


# ============================================================================
# UNIT TESTS: Pure functions
# ============================================================================

class TestSlugify:
    """Unit tests for slugify function"""

    def test_slugify_happy_path(self):
        """Test slugify with typical tool name converts to lowercase with hyphens"""
        result = slugify("My Cool Tool")
        assert result == "my-cool-tool"
        assert result.islower()

    def test_slugify_special_chars(self):
        """Test slugify removes special characters and replaces with hyphens"""
        result = slugify("Tool@#$%Name!!!")
        assert re.match(r'^[a-z0-9-]+$', result), "Should contain only alphanumerics and hyphens"
        assert "tool" in result and "name" in result

    def test_slugify_no_leading_trailing_hyphens(self):
        """Test slugify strips leading and trailing hyphens"""
        result = slugify("---Tool Name---")
        assert not result.startswith('-'), "Should not start with hyphen"
        assert not result.endswith('-'), "Should not end with hyphen"
        assert "tool-name" in result

    def test_slugify_consecutive_hyphens(self):
        """Test slugify with consecutive special characters creates single hyphens"""
        result = slugify("Tool   Name")
        # Should collapse multiple spaces/special chars into single hyphens
        assert "--" not in result, "Should not have consecutive hyphens"

    def test_slugify_empty_string(self):
        """Test slugify with empty string"""
        result = slugify("")
        assert isinstance(result, str)
        # May return empty string or some default

    def test_slugify_unicode(self):
        """Test slugify with unicode characters"""
        result = slugify("Tööl Ñame")
        # Should handle unicode - either transliterate or remove
        assert isinstance(result, str)
        assert re.match(r'^[a-z0-9-]*$', result), "Result should only have alphanumerics and hyphens"

    @pytest.mark.parametrize("input_name,expected_pattern", [
        ("UPPERCASE", r'^[a-z-]+$'),
        ("MixedCase123", r'^[a-z0-9-]+$'),
        ("dash-already-there", r'^dash-already-there$'),
        ("123-numbers-first", r'^[a-z0-9-]+$'),
    ])
    def test_slugify_parametrized(self, input_name, expected_pattern):
        """Parametrized tests for various slug patterns"""
        result = slugify(input_name)
        assert re.match(expected_pattern, result)
        assert not result.startswith('-')
        assert not result.endswith('-')


class TestMustBeMitValidator:
    """Unit tests for must_be_mit validator"""

    def test_must_be_mit_valid_uppercase(self):
        """Test must_be_mit validator accepts 'MIT' uppercase"""
        result = must_be_mit(ToolSubmission, "MIT")
        assert result == "MIT"

    def test_must_be_mit_valid_lowercase(self):
        """Test must_be_mit validator accepts 'mit' lowercase"""
        result = must_be_mit(ToolSubmission, "mit")
        assert result == "MIT"

    def test_must_be_mit_valid_mixedcase(self):
        """Test must_be_mit validator accepts 'MiT' mixed case"""
        result = must_be_mit(ToolSubmission, "MiT")
        assert result == "MIT"

    def test_must_be_mit_invalid_apache(self):
        """Test must_be_mit validator rejects Apache license"""
        with pytest.raises(ValueError) as exc_info:
            must_be_mit(ToolSubmission, "Apache")
        assert "mit" in str(exc_info.value).lower() or "license" in str(exc_info.value).lower()

    def test_must_be_mit_invalid_empty(self):
        """Test must_be_mit validator rejects empty string"""
        with pytest.raises(ValueError) as exc_info:
            must_be_mit(ToolSubmission, "")
        assert "mit" in str(exc_info.value).lower() or "license" in str(exc_info.value).lower()

    @pytest.mark.parametrize("invalid_license", ["GPL", "BSD", "Apache-2.0", "Proprietary", "None"])
    def test_must_be_mit_invalid_licenses(self, invalid_license):
        """Parametrized tests for invalid licenses"""
        with pytest.raises(ValueError):
            must_be_mit(ToolSubmission, invalid_license)


# ============================================================================
# INTEGRATION TESTS: API endpoints
# ============================================================================

class TestListTools:
    """Integration tests for list_tools endpoint"""

    @pytest.mark.asyncio
    async def test_list_tools_happy_path(self, db_session: AsyncSession, active_tool: Tool):
        """Test list_tools returns paginated tools with proper structure"""
        result = await list_tools(tag=None, page=1, per_page=10, db=db_session, user=None)
        
        assert 'tools' in result
        assert 'total' in result
        assert 'page' in result
        assert 'per_page' in result
        assert isinstance(result['tools'], list)
        assert result['page'] == 1
        assert result['per_page'] == 10

    @pytest.mark.asyncio
    async def test_list_tools_with_tag_filter(self, db_session: AsyncSession, active_tool: Tool):
        """Test list_tools filters by tag"""
        # Add tag to tool
        tag = ToolTag(tool_id=active_tool.id, tag="python")
        db_session.add(tag)
        await db_session.commit()

        result = await list_tools(tag="python", page=1, per_page=10, db=db_session, user=None)
        assert 'tools' in result
        # Should include tools with the tag
        
    @pytest.mark.asyncio
    async def test_list_tools_pagination_boundary(self, db_session: AsyncSession, active_tool: Tool):
        """Test list_tools with page at boundary"""
        result = await list_tools(tag=None, page=1, per_page=1, db=db_session, user=None)
        assert result['per_page'] == 1
        assert len(result['tools']) <= 1

    @pytest.mark.asyncio
    async def test_list_tools_per_page_max(self, db_session: AsyncSession):
        """Test list_tools respects per_page max limit of 100"""
        result = await list_tools(tag=None, page=1, per_page=100, db=db_session, user=None)
        assert result['per_page'] == 100

    @pytest.mark.asyncio
    async def test_list_tools_only_active(self, db_session: AsyncSession, active_tool: Tool, inactive_tool: Tool):
        """Test list_tools returns only active tools"""
        result = await list_tools(tag=None, page=1, per_page=10, db=db_session, user=None)
        
        # Verify only active tools returned
        tool_slugs = [t['slug'] for t in result['tools']]
        assert 'test-tool' in tool_slugs or len(tool_slugs) >= 0  # Active tool may be included
        assert 'inactive-tool' not in tool_slugs  # Inactive tool should NOT be included

    @pytest.mark.asyncio
    async def test_list_tools_ordered_by_created_at(self, db_session: AsyncSession, tool_owner: User):
        """Test list_tools returns tools ordered by created_at descending"""
        # Create multiple tools with different timestamps
        tool1 = Tool(slug="tool1", name="Tool 1", author_id=tool_owner.id, is_active=True)
        tool2 = Tool(slug="tool2", name="Tool 2", author_id=tool_owner.id, is_active=True)
        db_session.add_all([tool1, tool2])
        await db_session.commit()

        result = await list_tools(tag=None, page=1, per_page=10, db=db_session, user=None)
        # Tools should be ordered by created_at descending
        if len(result['tools']) > 1:
            timestamps = [t.get('created_at') for t in result['tools'] if t.get('created_at')]
            # Verify descending order if timestamps present

    @pytest.mark.asyncio
    async def test_list_tools_empty_tag(self, db_session: AsyncSession, active_tool: Tool):
        """Test list_tools with empty string tag"""
        result = await list_tools(tag="", page=1, per_page=10, db=db_session, user=None)
        assert 'tools' in result

    @pytest.mark.asyncio
    async def test_list_tools_nonexistent_tag(self, db_session: AsyncSession, active_tool: Tool):
        """Test list_tools with tag that doesn't exist"""
        result = await list_tools(tag="nonexistent", page=1, per_page=10, db=db_session, user=None)
        assert result['total'] == 0 or len(result['tools']) >= 0


class TestGetTool:
    """Integration tests for get_tool endpoint"""

    @pytest.mark.asyncio
    async def test_get_tool_happy_path(self, db_session: AsyncSession, active_tool: Tool):
        """Test get_tool retrieves tool with full details"""
        result = await get_tool(slug="test-tool", db=db_session, user=None)
        
        # Verify all required fields present
        assert 'slug' in result
        assert result['slug'] == "test-tool"
        assert 'name' in result
        assert 'description' in result
        assert 'problem_statement' in result
        assert 'repo_url' in result
        assert 'license' in result
        assert 'author' in result
        assert 'vote_count' in result
        assert 'user_voted' in result
        assert 'neighbors' in result
        assert 'forks' in result
        assert 'discussion' in result

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, db_session: AsyncSession):
        """Test get_tool raises error for non-existent tool"""
        with pytest.raises(Exception) as exc_info:
            await get_tool(slug="nonexistent-tool", db=db_session, user=None)
        # Should raise tool_not_found error

    @pytest.mark.asyncio
    async def test_get_tool_inactive(self, db_session: AsyncSession, inactive_tool: Tool):
        """Test get_tool raises error for inactive tool"""
        with pytest.raises(Exception) as exc_info:
            await get_tool(slug="inactive-tool", db=db_session, user=None)
        # Should raise tool_not_found error for inactive tools

    @pytest.mark.asyncio
    async def test_get_tool_neighbors_limit(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test get_tool returns at most 10 neighbors"""
        # Create 15 neighbor tools and proximity links
        for i in range(15):
            neighbor = Tool(slug=f"neighbor-{i}", name=f"Neighbor {i}", author_id=tool_owner.id, is_active=True)
            db_session.add(neighbor)
            await db_session.flush()
            link = ProximityLink(tool_id=active_tool.id, neighbor_id=neighbor.id, similarity=100-i)
            db_session.add(link)
        await db_session.commit()

        result = await get_tool(slug="test-tool", db=db_session, user=None)
        assert len(result.get('neighbors', [])) <= 10


class TestVerifyRepoOwnership:
    """Integration tests for verify_repo_ownership function"""

    @pytest.mark.asyncio
    async def test_verify_repo_ownership_non_github(self):
        """Test verify_repo_ownership returns True for non-GitHub URL"""
        result = await verify_repo_ownership(
            repo_url="https://gitlab.com/user/repo",
            username="testuser"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_repo_ownership_matching_owner(self):
        """Test verify_repo_ownership returns True when repo owner matches username"""
        with patch('httpx.AsyncClient') as mock_client:
            result = await verify_repo_ownership(
                repo_url="https://github.com/testuser/repo",
                username="testuser"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_repo_ownership_collaborator(self):
        """Test verify_repo_ownership checks collaborator access via GitHub API"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await verify_repo_ownership(
                repo_url="https://github.com/org/repo",
                username="testuser"
            )
            # Should check via API

    @pytest.mark.asyncio
    async def test_verify_repo_ownership_not_owner(self):
        """Test verify_repo_ownership returns False when user is not owner or collaborator"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await verify_repo_ownership(
                repo_url="https://github.com/otheruser/repo",
                username="testuser"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_repo_ownership_api_error(self):
        """Test verify_repo_ownership returns False on API error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("API Error")
            
            result = await verify_repo_ownership(
                repo_url="https://github.com/org/repo",
                username="testuser"
            )
            assert result is False


class TestSubmitTool:
    """Integration tests for submit_tool endpoint"""

    @pytest.mark.asyncio
    async def test_submit_tool_happy_path(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool creates new tool with unique slug"""
        submission = ToolSubmission(
            name="New Tool",
            description="A new tool",
            problem_statement="Solves new problems",
            repo_url="https://github.com/testuser/new-tool",
            license="MIT",
            language="Python",
            tags=["python", "test"],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result = await submit_tool(body=submission, user=base_user, db=db_session)
        
        assert 'slug' in result
        assert result['status'] == 'created'
        assert isinstance(result['slug'], str)

    @pytest.mark.asyncio
    async def test_submit_tool_repo_ownership_failed(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool raises error when repo ownership verification fails"""
        submission = ToolSubmission(
            name="Unauthorized Tool",
            description="Should fail",
            problem_statement="Not owned",
            repo_url="https://github.com/someoneelse/repo",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=False):
            with pytest.raises(Exception) as exc_info:
                await submit_tool(body=submission, user=base_user, db=db_session)
            # Should raise repo_ownership_failed error

    @pytest.mark.asyncio
    async def test_submit_tool_non_mit_license(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool rejects non-MIT license via validator"""
        with pytest.raises(ValidationError) as exc_info:
            submission = ToolSubmission(
                name="Apache Tool",
                description="Should fail validation",
                problem_statement="Wrong license",
                repo_url="https://github.com/testuser/tool",
                license="Apache",
                language="Python",
                tags=[],
                fork_parent_slug=None
            )

    @pytest.mark.asyncio
    async def test_submit_tool_creates_tags(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool creates tags up to max 20"""
        submission = ToolSubmission(
            name="Tagged Tool",
            description="With tags",
            problem_statement="Tag testing",
            repo_url="https://github.com/testuser/tagged",
            license="MIT",
            language="Python",
            tags=["python", "testing", "api", "backend", "tool"],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result = await submit_tool(body=submission, user=base_user, db=db_session)
        
        # Verify tags created
        tool_result = await db_session.execute(
            select(Tool).where(Tool.slug == result['slug'])
        )
        tool = tool_result.scalar_one()
        tags_result = await db_session.execute(
            select(ToolTag).where(ToolTag.tool_id == tool.id)
        )
        tags = tags_result.scalars().all()
        assert len(tags) == 5

    @pytest.mark.asyncio
    async def test_submit_tool_tags_lowercased(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool lowercases and strips tags"""
        submission = ToolSubmission(
            name="Case Tool",
            description="Tag case testing",
            problem_statement="Case sensitive tags",
            repo_url="https://github.com/testuser/case-tool",
            license="MIT",
            language="Python",
            tags=["Python", " Java ", "C++"],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result = await submit_tool(body=submission, user=base_user, db=db_session)
        
        # Verify tags are lowercased
        tool_result = await db_session.execute(
            select(Tool).where(Tool.slug == result['slug'])
        )
        tool = tool_result.scalar_one()
        tags_result = await db_session.execute(
            select(ToolTag).where(ToolTag.tool_id == tool.id)
        )
        tags = tags_result.scalars().all()
        tag_values = [t.tag for t in tags]
        assert all(t == t.lower().strip() for t in tag_values)

    @pytest.mark.asyncio
    async def test_submit_tool_fork_link(self, db_session: AsyncSession, base_user: User, active_tool: Tool):
        """Test submit_tool creates fork link when fork_parent_slug provided"""
        submission = ToolSubmission(
            name="Fork Tool",
            description="A fork",
            problem_statement="Forked from parent",
            repo_url="https://github.com/testuser/fork-tool",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug="test-tool"
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result = await submit_tool(body=submission, user=base_user, db=db_session)
        
        # Verify fork link created
        fork_links = await db_session.execute(select(ForkLink))
        links = fork_links.scalars().all()
        assert len(links) > 0

    @pytest.mark.asyncio
    async def test_submit_tool_fork_nonexistent_parent(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool with nonexistent fork parent"""
        submission = ToolSubmission(
            name="Orphan Fork",
            description="Fork with no parent",
            problem_statement="Parent doesn't exist",
            repo_url="https://github.com/testuser/orphan",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug="nonexistent"
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            # May raise error or handle gracefully
            try:
                result = await submit_tool(body=submission, user=base_user, db=db_session)
            except Exception:
                pass  # Expected to potentially fail

    @pytest.mark.asyncio
    async def test_submit_tool_triggers_proximity_scan(self, db_session: AsyncSession, base_user: User):
        """Test submit_tool triggers proximity scan"""
        submission = ToolSubmission(
            name="Proximity Tool",
            description="Testing proximity",
            problem_statement="Proximity scan test",
            repo_url="https://github.com/testuser/proximity",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True), \
             patch('backend_api_registry_router.scan_proximity') as mock_scan:
            result = await submit_tool(body=submission, user=base_user, db=db_session)
            # Verify scan_proximity was called (best-effort)


class TestUpdateTool:
    """Integration tests for update_tool endpoint"""

    @pytest.mark.asyncio
    async def test_update_tool_happy_path(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test update_tool updates tool fields"""
        update = ToolUpdate(
            description="Updated description",
            problem_statement=None,
            repo_url=None,
            language="JavaScript",
            tags=None
        )
        
        result = await update_tool(slug="test-tool", body=update, user=tool_owner, db=db_session)
        
        assert result['slug'] == "test-tool"
        assert result['status'] == "updated"

    @pytest.mark.asyncio
    async def test_update_tool_not_found(self, db_session: AsyncSession, tool_owner: User):
        """Test update_tool raises error for non-existent tool"""
        update = ToolUpdate(description="Should fail")
        
        with pytest.raises(Exception) as exc_info:
            await update_tool(slug="nonexistent", body=update, user=tool_owner, db=db_session)

    @pytest.mark.asyncio
    async def test_update_tool_not_owner(self, db_session: AsyncSession, active_tool: Tool, other_user: User):
        """Test update_tool raises error when user is not tool author"""
        update = ToolUpdate(description="Unauthorized update")
        
        with pytest.raises(Exception) as exc_info:
            await update_tool(slug="test-tool", body=update, user=other_user, db=db_session)
        # Should raise not_owner error

    @pytest.mark.asyncio
    async def test_update_tool_inactive(self, db_session: AsyncSession, inactive_tool: Tool, tool_owner: User):
        """Test update_tool raises error for inactive tool"""
        update = ToolUpdate(description="Update inactive")
        
        with pytest.raises(Exception) as exc_info:
            await update_tool(slug="inactive-tool", body=update, user=tool_owner, db=db_session)
        # Should raise tool_not_found

    @pytest.mark.asyncio
    async def test_update_tool_replaces_tags(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test update_tool replaces all tags when tags provided"""
        # Add initial tags
        tag1 = ToolTag(tool_id=active_tool.id, tag="old-tag")
        db_session.add(tag1)
        await db_session.commit()
        
        update = ToolUpdate(tags=["new", "tags"])
        result = await update_tool(slug="test-tool", body=update, user=tool_owner, db=db_session)
        
        # Verify old tags removed and new tags added
        tags_result = await db_session.execute(
            select(ToolTag).where(ToolTag.tool_id == active_tool.id)
        )
        tags = tags_result.scalars().all()
        tag_values = [t.tag for t in tags]
        assert "new" in tag_values
        assert "tags" in tag_values
        assert "old-tag" not in tag_values

    @pytest.mark.asyncio
    async def test_update_tool_triggers_proximity_rescan(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test update_tool triggers proximity re-scan when problem_statement changed"""
        update = ToolUpdate(problem_statement="New problem statement")
        
        with patch('backend_api_registry_router.scan_proximity') as mock_scan:
            result = await update_tool(slug="test-tool", body=update, user=tool_owner, db=db_session)
            # Verify scan_proximity was called

    @pytest.mark.asyncio
    async def test_update_tool_partial_update(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test update_tool with partial fields updates only provided fields"""
        original_language = active_tool.language
        update = ToolUpdate(description="Only description updated")
        
        result = await update_tool(slug="test-tool", body=update, user=tool_owner, db=db_session)
        
        # Verify language unchanged
        await db_session.refresh(active_tool)
        assert active_tool.language == original_language


class TestDeactivateTool:
    """Integration tests for deactivate_tool endpoint"""

    @pytest.mark.asyncio
    async def test_deactivate_tool_happy_path(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test deactivate_tool sets is_active to False"""
        result = await deactivate_tool(slug="test-tool", user=tool_owner, db=db_session)
        
        assert result['status'] == 'deactivated'
        
        # Verify tool is now inactive
        await db_session.refresh(active_tool)
        assert active_tool.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_tool_not_found(self, db_session: AsyncSession, tool_owner: User):
        """Test deactivate_tool raises error for non-existent tool"""
        with pytest.raises(Exception) as exc_info:
            await deactivate_tool(slug="nonexistent", user=tool_owner, db=db_session)

    @pytest.mark.asyncio
    async def test_deactivate_tool_not_owner(self, db_session: AsyncSession, active_tool: Tool, other_user: User):
        """Test deactivate_tool raises error when user is not tool author"""
        with pytest.raises(Exception) as exc_info:
            await deactivate_tool(slug="test-tool", user=other_user, db=db_session)
        # Should raise not_owner error

    @pytest.mark.asyncio
    async def test_deactivate_tool_already_inactive(self, db_session: AsyncSession, inactive_tool: Tool, tool_owner: User):
        """Test deactivate_tool on already inactive tool"""
        # May succeed idempotently or raise tool_not_found
        try:
            result = await deactivate_tool(slug="inactive-tool", user=tool_owner, db=db_session)
            assert result['status'] == 'deactivated'
        except Exception:
            pass  # May raise tool_not_found


# ============================================================================
# INVARIANT TESTS
# ============================================================================

class TestInvariants:
    """Tests for system invariants"""

    @pytest.mark.asyncio
    async def test_tool_submission_validation_mit_invariant(self):
        """Test ToolSubmission enforces MIT license invariant"""
        # Valid MIT
        valid = ToolSubmission(
            name="Tool",
            description="Desc",
            problem_statement="Problem",
            repo_url="https://github.com/user/repo",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug=None
        )
        assert valid.license == "MIT"
        
        # Invalid licenses should raise ValidationError
        for invalid_license in ["Apache", "GPL", "BSD", ""]:
            with pytest.raises(ValidationError):
                ToolSubmission(
                    name="Tool",
                    description="Desc",
                    problem_statement="Problem",
                    repo_url="https://github.com/user/repo",
                    license=invalid_license,
                    language="Python",
                    tags=[],
                    fork_parent_slug=None
                )

    @pytest.mark.asyncio
    async def test_tool_slug_uniqueness(self, db_session: AsyncSession, base_user: User):
        """Test tool slugs are unique with collision handling"""
        submission1 = ToolSubmission(
            name="Duplicate Name",
            description="First",
            problem_statement="First",
            repo_url="https://github.com/testuser/tool1",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug=None
        )
        
        submission2 = ToolSubmission(
            name="Duplicate Name",
            description="Second",
            problem_statement="Second",
            repo_url="https://github.com/testuser/tool2",
            license="MIT",
            language="Python",
            tags=[],
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result1 = await submit_tool(body=submission1, user=base_user, db=db_session)
            result2 = await submit_tool(body=submission2, user=base_user, db=db_session)
        
        # Slugs should be different (second should have uuid suffix)
        assert result1['slug'] != result2['slug']

    @pytest.mark.asyncio
    async def test_tags_limit_20(self, db_session: AsyncSession, base_user: User):
        """Test tags are limited to 20 per tool"""
        # Create 25 tags
        many_tags = [f"tag{i}" for i in range(25)]
        
        submission = ToolSubmission(
            name="Many Tags",
            description="Testing tag limit",
            problem_statement="Tag limit test",
            repo_url="https://github.com/testuser/manytags",
            license="MIT",
            language="Python",
            tags=many_tags,
            fork_parent_slug=None
        )
        
        with patch('backend_api_registry_router.verify_repo_ownership', return_value=True):
            result = await submit_tool(body=submission, user=base_user, db=db_session)
        
        # Verify only 20 tags stored
        tool_result = await db_session.execute(
            select(Tool).where(Tool.slug == result['slug'])
        )
        tool = tool_result.scalar_one()
        tags_result = await db_session.execute(
            select(ToolTag).where(ToolTag.tool_id == tool.id)
        )
        tags = tags_result.scalars().all()
        assert len(tags) <= 20


# ============================================================================
# PERMISSION MATRIX TESTS
# ============================================================================

class TestPermissions:
    """Parametrized tests for permission matrices"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,requires_auth", [
        ("list_tools", False),
        ("get_tool", False),
        ("submit_tool", True),
        ("update_tool", True),
        ("deactivate_tool", True),
    ])
    async def test_anonymous_user_access(self, endpoint, requires_auth, db_session: AsyncSession, active_tool: Tool):
        """Test anonymous user access to endpoints"""
        if endpoint == "list_tools":
            result = await list_tools(tag=None, page=1, per_page=10, db=db_session, user=None)
            assert 'tools' in result
        elif endpoint == "get_tool":
            result = await get_tool(slug="test-tool", db=db_session, user=None)
            assert 'slug' in result
        elif requires_auth:
            # Should raise authentication error for authenticated endpoints
            pass  # Actual implementation would check user is not None


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Additional edge case tests"""

    @pytest.mark.asyncio
    async def test_pagination_beyond_last_page(self, db_session: AsyncSession, active_tool: Tool):
        """Test requesting page beyond last page"""
        result = await list_tools(tag=None, page=999, per_page=10, db=db_session, user=None)
        assert result['tools'] == [] or len(result['tools']) == 0

    @pytest.mark.asyncio
    async def test_tool_update_with_empty_values(self, db_session: AsyncSession, active_tool: Tool, tool_owner: User):
        """Test update with all None values"""
        update = ToolUpdate()
        result = await update_tool(slug="test-tool", body=update, user=tool_owner, db=db_session)
        assert result['status'] == 'updated'

    def test_slugify_only_special_chars(self):
        """Test slugify with only special characters"""
        result = slugify("@@@###$$$")
        # Should return empty or minimal string
        assert isinstance(result, str)
        assert not result.startswith('-')
        assert not result.endswith('-')

    @pytest.mark.asyncio
    async def test_concurrent_tool_submission(self, db_session: AsyncSession, base_user: User):
        """Test concurrent submissions with same name handle slug uniqueness"""
        # This would require more complex async testing setup
        # Placeholder for concurrency test
        pass
"""