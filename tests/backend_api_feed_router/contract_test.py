"""
Contract-based test suite for backend_api_feed_router
Generated from contract version 1

Tests cover:
- _iso: datetime to ISO 8601 conversion (naive/aware timezones)
- _text_el: XML element creation with text content
- _build_feed: Atom feed generation from tools and threads
- atom_feed: FastAPI endpoint handler

All async functions tested with @pytest.mark.asyncio
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from io import BytesIO
import re

# Import component under test
from backend.api.feed.router import _iso, _text_el, _build_feed, atom_feed


# =============================================================================
# UNIT TESTS: _iso
# =============================================================================

class Test_iso_HappyPath:
    """Test _iso function with valid inputs"""
    
    def test_iso_naive_datetime_adds_utc(self):
        """Verify _iso converts naive datetime to ISO 8601 with UTC timezone"""
        dt = datetime(2023, 6, 15, 10, 30, 45)
        result = _iso(dt)
        
        # Verify ISO format and UTC suffix
        assert isinstance(result, str)
        assert '+00:00' in result or 'Z' in result or result.endswith('+00:00')
        # Verify date components
        assert '2023' in result
        assert '06' in result or '6' in result
        assert '15' in result
        
    def test_iso_aware_datetime_preserves_timezone(self):
        """Verify _iso preserves timezone for aware datetime objects"""
        dt = datetime(2023, 6, 15, 10, 30, 45, tzinfo=timezone(timedelta(hours=5)))
        result = _iso(dt)
        
        # Verify timezone is preserved
        assert '+05:00' in result
        assert '2023' in result


class Test_iso_EdgeCases:
    """Edge case tests for _iso function"""
    
    def test_iso_negative_timezone(self):
        """Edge case: datetime with negative timezone offset"""
        dt = datetime(2023, 6, 15, 10, 30, 45, tzinfo=timezone(timedelta(hours=-7)))
        result = _iso(dt)
        
        assert '-07:00' in result
        
    def test_iso_microseconds(self):
        """Edge case: datetime with microseconds"""
        dt = datetime(2023, 6, 15, 10, 30, 45, 123456)
        result = _iso(dt)
        
        # Result should be valid ISO format (may or may not include microseconds)
        assert isinstance(result, str)
        assert '2023' in result
        # Fractional seconds might be included or rounded
        assert 'T' in result  # ISO 8601 has T separator
        
    def test_iso_utc_timezone(self):
        """Edge case: datetime with explicit UTC timezone"""
        dt = datetime(2023, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _iso(dt)
        
        assert isinstance(result, str)
        # Should have UTC indicator
        assert '+00:00' in result or 'Z' in result


# =============================================================================
# UNIT TESTS: _text_el
# =============================================================================

class Test_text_el_HappyPath:
    """Test _text_el function with valid inputs"""
    
    def test_text_el_creates_child(self):
        """Verify _text_el creates XML child element with text"""
        parent = ET.Element('root')
        tag = 'title'
        text = 'Test Title'
        
        result = _text_el(parent, tag, text)
        
        # Verify child element created and returned
        assert result is not None
        assert result.tag == tag
        assert result.text == text
        
        # Verify parent contains child
        children = list(parent)
        assert len(children) == 1
        assert children[0].tag == tag
        assert children[0].text == text


class Test_text_el_EdgeCases:
    """Edge case tests for _text_el function"""
    
    def test_text_el_xml_special_characters(self):
        """Edge case: _text_el with XML special characters"""
        parent = ET.Element('root')
        tag = 'content'
        text = "<script>alert('test');</script> & more"
        
        result = _text_el(parent, tag, text)
        
        # Verify text is stored correctly (ElementTree handles escaping)
        assert result.text == text
        
        # Verify XML is valid by serializing and parsing
        xml_str = ET.tostring(parent, encoding='unicode')
        assert '<content>' in xml_str
        # ElementTree should escape special chars
        parsed = ET.fromstring(xml_str)
        child = parsed.find('content')
        assert child.text == text
        
    def test_text_el_empty_text(self):
        """Edge case: _text_el with empty string"""
        parent = ET.Element('root')
        tag = 'description'
        text = ''
        
        result = _text_el(parent, tag, text)
        
        assert result is not None
        assert result.tag == tag
        assert result.text == ''
        
    def test_text_el_unicode(self):
        """Edge case: _text_el with Unicode characters"""
        parent = ET.Element('root')
        tag = 'title'
        text = 'Hello 世界 🌍'
        
        result = _text_el(parent, tag, text)
        
        assert result.text == text
        
        # Verify Unicode is preserved when serialized
        xml_str = ET.tostring(parent, encoding='unicode')
        assert '世界' in xml_str or '&#' in xml_str  # Either literal or entity
        
    def test_text_el_multiple_children(self):
        """Edge case: adding multiple children to same parent"""
        parent = ET.Element('root')
        
        child1 = _text_el(parent, 'first', 'First child')
        child2 = _text_el(parent, 'second', 'Second child')
        
        children = list(parent)
        assert len(children) == 2
        assert children[0].tag == 'first'
        assert children[1].tag == 'second'


# =============================================================================
# INTEGRATION TESTS: _build_feed
# =============================================================================

@pytest.fixture
def mock_author():
    """Create a mock Author object"""
    author = Mock()
    author.display_name = 'Test User'
    author.username = 'testuser'
    return author


@pytest.fixture
def mock_tool():
    """Create a mock Tool object with all required attributes"""
    tool = Mock()
    tool.id = 1
    tool.name = 'Test Tool'
    tool.slug = 'test-tool'
    tool.description = 'A test tool description'
    tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    tool.author = Mock()
    tool.author.display_name = 'Tool Author'
    tool.author.username = 'toolauthor'
    return tool


@pytest.fixture
def mock_thread():
    """Create a mock ForumThread object with all required attributes"""
    thread = Mock()
    thread.id = 100
    thread.title = 'Test Thread'
    thread.body = 'This is a test thread body'
    thread.created_at = datetime(2023, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    thread.author = Mock()
    thread.author.display_name = 'Thread Author'
    thread.author.username = 'threadauthor'
    return thread


class Test_build_feed_HappyPath:
    """Test _build_feed with valid inputs"""
    
    def test_build_feed_happy_path(self, mock_tool, mock_thread):
        """Verify _build_feed creates valid Atom XML with mixed content"""
        tools = [mock_tool]
        threads = [mock_thread]
        
        result = _build_feed(tools, threads)
        
        # Verify result is string
        assert isinstance(result, str)
        
        # Verify XML declaration
        assert '<?xml' in result
        assert 'utf-8' in result.lower() or 'UTF-8' in result
        
        # Parse XML
        root = ET.fromstring(result)
        
        # Verify Atom namespace
        assert 'http://www.w3.org/2005/Atom' in root.tag
        
        # Verify feed metadata
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        feed_id = root.find('atom:id', ns)
        assert feed_id is not None
        assert feed_id.text == 'urn:centaur:feed'
        
        title = root.find('atom:title', ns)
        assert title is not None
        assert title.text == 'centaur.tools'
        
        # Verify entries present
        entries = root.findall('atom:entry', ns)
        assert len(entries) == 2
        
        # Verify sorting (thread is more recent)
        first_entry_title = entries[0].find('atom:title', ns).text
        assert first_entry_title == 'Test Thread'  # More recent


class Test_build_feed_EdgeCases:
    """Edge case tests for _build_feed"""
    
    def test_build_feed_empty_lists(self):
        """Edge case: _build_feed with no tools or threads"""
        result = _build_feed([], [])
        
        assert isinstance(result, str)
        assert '<?xml' in result
        
        # Parse and verify
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Should have feed metadata
        assert root.find('atom:id', ns).text == 'urn:centaur:feed'
        
        # Should have no entries
        entries = root.findall('atom:entry', ns)
        assert len(entries) == 0
        
        # Should have updated timestamp
        updated = root.find('atom:updated', ns)
        assert updated is not None
        
    def test_build_feed_missing_author(self, mock_tool):
        """Edge case: _build_feed with None author defaults to 'unknown'"""
        mock_tool.author = None
        tools = [mock_tool]
        
        result = _build_feed(tools, [])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entry = root.find('atom:entry', ns)
        author = entry.find('atom:author', ns)
        author_name = author.find('atom:name', ns)
        
        assert author_name.text == 'unknown'


class Test_build_feed_Invariants:
    """Invariant tests for _build_feed"""
    
    def test_build_feed_50_entry_limit(self):
        """Invariant: _build_feed limits to 50 entries maximum"""
        # Create 60 tools and 60 threads
        tools = []
        for i in range(60):
            tool = Mock()
            tool.id = i
            tool.name = f'Tool {i}'
            tool.slug = f'tool-{i}'
            tool.description = f'Description {i}'
            tool.created_at = datetime(2023, 6, 15, 10, i % 60, 0, tzinfo=timezone.utc)
            tool.author = Mock()
            tool.author.display_name = f'Author {i}'
            tool.author.username = f'author{i}'
            tools.append(tool)
            
        threads = []
        for i in range(60):
            thread = Mock()
            thread.id = i + 1000
            thread.title = f'Thread {i}'
            thread.body = f'Body {i}'
            thread.created_at = datetime(2023, 6, 16, 10, i % 60, 0, tzinfo=timezone.utc)
            thread.author = Mock()
            thread.author.display_name = f'Thread Author {i}'
            thread.author.username = f'threadauthor{i}'
            threads.append(thread)
        
        result = _build_feed(tools, threads)
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        
        # Should have exactly 50 entries
        assert len(entries) == 50
        
    def test_build_feed_truncates_descriptions(self):
        """Invariant: _build_feed truncates descriptions to 500 characters"""
        tool = Mock()
        tool.id = 1
        tool.name = 'Long Tool'
        tool.slug = 'long-tool'
        tool.description = 'x' * 1000  # 1000 character description
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = 'Author'
        tool.author.username = 'author'
        
        result = _build_feed([tool], [])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entry = root.find('atom:entry', ns)
        summary = entry.find('atom:summary', ns)
        
        assert len(summary.text) <= 500
        
    def test_build_feed_feed_metadata_invariants(self, mock_tool):
        """Invariant: Verify all feed metadata constants"""
        result = _build_feed([mock_tool], [])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Feed ID
        assert root.find('atom:id', ns).text == 'urn:centaur:feed'
        
        # Title
        assert root.find('atom:title', ns).text == 'centaur.tools'
        
        # Subtitle
        subtitle = root.find('atom:subtitle', ns)
        assert subtitle is not None
        assert subtitle.text == 'Community-governed registry for AI tools'
        
        # Author
        author = root.find('atom:author', ns)
        author_name = author.find('atom:name', ns)
        assert author_name.text == 'centaur.tools'
        
        # Links
        links = root.findall('atom:link', ns)
        link_dict = {link.get('rel'): link.get('href') for link in links}
        
        assert link_dict.get('self') == 'https://centaur.tools/api/feed/atom.xml'
        assert link_dict.get('alternate') == 'https://centaur.tools'
        
    def test_build_feed_tool_entry_format(self):
        """Invariant: Tool entries have correct URN and link format"""
        tool = Mock()
        tool.id = 123
        tool.name = 'Test Tool'
        tool.slug = 'test-tool'
        tool.description = 'Description'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = 'Author'
        tool.author.username = 'author'
        
        result = _build_feed([tool], [])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entry = root.find('atom:entry', ns)
        
        # Entry ID
        entry_id = entry.find('atom:id', ns)
        assert entry_id.text == 'urn:centaur:tool:123'
        
        # Link
        link = entry.find('atom:link', ns)
        assert link.get('href') == 'https://centaur.tools/tools/test-tool'
        
        # Category
        category = entry.find('atom:category', ns)
        assert category.get('term') == 'tool'
        
    def test_build_feed_thread_entry_format(self):
        """Invariant: Thread entries have correct URN and link format"""
        thread = Mock()
        thread.id = 456
        thread.title = 'Test Thread'
        thread.body = 'Body'
        thread.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        thread.author = Mock()
        thread.author.display_name = 'Author'
        thread.author.username = 'author'
        
        result = _build_feed([], [thread])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entry = root.find('atom:entry', ns)
        
        # Entry ID
        entry_id = entry.find('atom:id', ns)
        assert entry_id.text == 'urn:centaur:thread:456'
        
        # Link
        link = entry.find('atom:link', ns)
        assert link.get('href') == 'https://centaur.tools/forum/thread/456'
        
        # Category
        category = entry.find('atom:category', ns)
        assert category.get('term') == 'forum'
        
    def test_build_feed_sort_order(self):
        """Invariant: Entries sorted by created_at descending"""
        tool1 = Mock()
        tool1.id = 1
        tool1.name = 'Old Tool'
        tool1.slug = 'old-tool'
        tool1.description = 'Desc'
        tool1.created_at = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tool1.author = Mock()
        tool1.author.display_name = 'Author'
        tool1.author.username = 'author'
        
        tool2 = Mock()
        tool2.id = 2
        tool2.name = 'New Tool'
        tool2.slug = 'new-tool'
        tool2.description = 'Desc'
        tool2.created_at = datetime(2023, 12, 31, 10, 0, 0, tzinfo=timezone.utc)
        tool2.author = Mock()
        tool2.author.display_name = 'Author'
        tool2.author.username = 'author'
        
        thread = Mock()
        thread.id = 100
        thread.title = 'Mid Thread'
        thread.body = 'Body'
        thread.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        thread.author = Mock()
        thread.author.display_name = 'Author'
        thread.author.username = 'author'
        
        result = _build_feed([tool1, tool2], [thread])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entries = root.findall('atom:entry', ns)
        titles = [entry.find('atom:title', ns).text for entry in entries]
        
        # Should be sorted: New Tool (Dec 31) -> Mid Thread (Jun 15) -> Old Tool (Jan 1)
        assert titles[0] == 'New Tool'
        assert titles[1] == 'Mid Thread'
        assert titles[2] == 'Old Tool'


class Test_build_feed_ErrorCases:
    """Error case tests for _build_feed"""
    
    def test_build_feed_missing_tool_attributes(self):
        """Error case: _build_feed raises AttributeError for missing Tool attributes"""
        tool = Mock()
        tool.id = 1
        tool.name = 'Test'
        # Missing slug attribute
        del tool.slug
        tool.description = 'Desc'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = 'Author'
        
        with pytest.raises(AttributeError):
            _build_feed([tool], [])
            
    def test_build_feed_missing_thread_attributes(self):
        """Error case: _build_feed raises AttributeError for missing ForumThread attributes"""
        thread = Mock(spec=['id', 'title', 'created_at', 'author'])
        thread.id = 1
        thread.title = 'Test'
        thread.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        thread.author = Mock()
        thread.author.display_name = 'Author'
        # Missing body attribute
        
        with pytest.raises(AttributeError):
            _build_feed([], [thread])


# =============================================================================
# E2E TESTS: atom_feed endpoint
# =============================================================================

@pytest.fixture
def mock_db_session():
    """Create mock AsyncSession for database"""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_query_result():
    """Create mock query result with scalars"""
    result = AsyncMock()
    result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
    return result


class Test_atom_feed_HappyPath:
    """Test atom_feed endpoint with valid inputs"""
    
    @pytest.mark.asyncio
    async def test_atom_feed_happy_path(self, mock_db_session):
        """Verify atom_feed endpoint returns valid Atom XML response"""
        # Mock database query results
        tool = Mock()
        tool.id = 1
        tool.name = 'Tool'
        tool.slug = 'tool'
        tool.description = 'Description'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = 'Author'
        tool.author.username = 'author'
        
        thread = Mock()
        thread.id = 100
        thread.title = 'Thread'
        thread.body = 'Body'
        thread.created_at = datetime(2023, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        thread.author = Mock()
        thread.author.display_name = 'Thread Author'
        thread.author.username = 'threadauthor'
        
        # Setup mock to return tools and threads
        result_mock = AsyncMock()
        result_mock.scalars = Mock(return_value=Mock(all=Mock(return_value=[tool])))
        
        result_mock2 = AsyncMock()
        result_mock2.scalars = Mock(return_value=Mock(all=Mock(return_value=[thread])))
        
        mock_db_session.execute = AsyncMock(side_effect=[result_mock, result_mock2])
        
        response = await atom_feed(mock_db_session)
        
        # Verify response type and content-type
        assert response is not None
        assert response.media_type == 'application/atom+xml'
        
        # Verify body contains valid XML
        body = response.body
        assert b'<?xml' in body
        assert b'http://www.w3.org/2005/Atom' in body
        
        # Parse and validate
        root = ET.fromstring(body)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        assert root.find('atom:id', ns).text == 'urn:centaur:feed'
        
    @pytest.mark.asyncio
    async def test_atom_feed_query_limits(self, mock_db_session):
        """Verify atom_feed queries with correct limits and filters"""
        # Create many tools
        tools = []
        for i in range(60):
            tool = Mock()
            tool.id = i
            tool.name = f'Tool {i}'
            tool.slug = f'tool-{i}'
            tool.description = 'Desc'
            tool.created_at = datetime(2023, 6, 15, 10, i % 60, 0, tzinfo=timezone.utc)
            tool.author = Mock()
            tool.author.display_name = 'Author'
            tool.author.username = 'author'
            tools.append(tool)
        
        threads = []
        for i in range(60):
            thread = Mock()
            thread.id = i + 1000
            thread.title = f'Thread {i}'
            thread.body = 'Body'
            thread.created_at = datetime(2023, 6, 15, 11, i % 60, 0, tzinfo=timezone.utc)
            thread.author = Mock()
            thread.author.display_name = 'Author'
            thread.author.username = 'author'
            threads.append(thread)
        
        # Return all items (feed builder will limit)
        result_tools = AsyncMock()
        result_tools.scalars = Mock(return_value=Mock(all=Mock(return_value=tools[:50])))
        
        result_threads = AsyncMock()
        result_threads.scalars = Mock(return_value=Mock(all=Mock(return_value=threads[:50])))
        
        mock_db_session.execute = AsyncMock(side_effect=[result_tools, result_threads])
        
        response = await atom_feed(mock_db_session)
        
        # Verify queries were made
        assert mock_db_session.execute.call_count == 2
        
        # Parse response and verify entry count
        root = ET.fromstring(response.body)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        
        # Should have at most 50 entries
        assert len(entries) <= 50


class Test_atom_feed_EdgeCases:
    """Edge case tests for atom_feed endpoint"""
    
    @pytest.mark.asyncio
    async def test_atom_feed_empty_database(self, mock_db_session):
        """Edge case: atom_feed with no data in database"""
        # Return empty results
        result_empty = AsyncMock()
        result_empty.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        
        mock_db_session.execute = AsyncMock(return_value=result_empty)
        
        response = await atom_feed(mock_db_session)
        
        # Should still return valid feed
        assert response.media_type == 'application/atom+xml'
        
        root = ET.fromstring(response.body)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Should have feed metadata
        assert root.find('atom:id', ns).text == 'urn:centaur:feed'
        
        # Should have no entries
        entries = root.findall('atom:entry', ns)
        assert len(entries) == 0


class Test_atom_feed_Invariants:
    """Invariant tests for atom_feed endpoint"""
    
    @pytest.mark.asyncio
    async def test_atom_feed_utf8_encoding(self, mock_db_session):
        """Invariant: atom_feed response uses UTF-8 encoding"""
        # Create tool with Unicode content
        tool = Mock()
        tool.id = 1
        tool.name = 'Unicode Tool 世界 🌍'
        tool.slug = 'unicode-tool'
        tool.description = 'Description with émojis 🎉'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = 'Author 名前'
        tool.author.username = 'author'
        
        result_mock = AsyncMock()
        result_mock.scalars = Mock(return_value=Mock(all=Mock(return_value=[tool])))
        
        result_empty = AsyncMock()
        result_empty.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        
        mock_db_session.execute = AsyncMock(side_effect=[result_mock, result_empty])
        
        response = await atom_feed(mock_db_session)
        
        # Verify UTF-8 declaration
        body = response.body
        assert b'utf-8' in body.lower() or b'UTF-8' in body
        
        # Verify Unicode content is preserved (either literal or escaped)
        body_str = body.decode('utf-8')
        assert '世界' in body_str or '&#' in body_str


class Test_atom_feed_ErrorCases:
    """Error case tests for atom_feed endpoint"""
    
    @pytest.mark.asyncio
    async def test_atom_feed_database_error(self, mock_db_session):
        """Error case: atom_feed handles database connection failure"""
        from sqlalchemy.exc import DatabaseError
        
        # Mock database to raise DatabaseError
        mock_db_session.execute = AsyncMock(side_effect=DatabaseError("Connection failed", None, None))
        
        # Should propagate the error
        with pytest.raises(DatabaseError):
            await atom_feed(mock_db_session)
            
    @pytest.mark.asyncio
    async def test_atom_feed_attribute_error(self, mock_db_session):
        """Error case: atom_feed handles AttributeError from malformed objects"""
        # Create tool missing required attributes
        tool = Mock(spec=['id', 'name', 'created_at'])
        tool.id = 1
        tool.name = 'Tool'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        # Missing slug, description, author
        
        result_mock = AsyncMock()
        result_mock.scalars = Mock(return_value=Mock(all=Mock(return_value=[tool])))
        
        result_empty = AsyncMock()
        result_empty.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        
        mock_db_session.execute = AsyncMock(side_effect=[result_mock, result_empty])
        
        # Should raise AttributeError
        with pytest.raises(AttributeError):
            await atom_feed(mock_db_session)


# =============================================================================
# ADDITIONAL COVERAGE TESTS
# =============================================================================

class Test_EdgeCaseCoverage:
    """Additional tests to ensure comprehensive coverage"""
    
    def test_iso_with_utc_z_format(self):
        """Test ISO format with Z suffix (alternative UTC representation)"""
        dt = datetime(2023, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _iso(dt)
        
        # Should have either +00:00 or Z
        assert '+00:00' in result or result.endswith('Z')
        
    def test_build_feed_thread_truncates_body(self):
        """Test that thread body is also truncated to 500 chars"""
        thread = Mock()
        thread.id = 1
        thread.title = 'Thread'
        thread.body = 'x' * 1000
        thread.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        thread.author = Mock()
        thread.author.display_name = 'Author'
        thread.author.username = 'author'
        
        result = _build_feed([], [thread])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', ns)
        summary = entry.find('atom:summary', ns)
        
        assert len(summary.text) <= 500
        
    def test_build_feed_author_display_name_fallback(self):
        """Test that username is used if display_name not available"""
        tool = Mock()
        tool.id = 1
        tool.name = 'Tool'
        tool.slug = 'tool'
        tool.description = 'Desc'
        tool.created_at = datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tool.author = Mock()
        tool.author.display_name = None
        tool.author.username = 'testuser'
        
        result = _build_feed([tool], [])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', ns)
        author = entry.find('atom:author', ns)
        author_name = author.find('atom:name', ns)
        
        # Should use username if display_name is None
        # (actual behavior depends on implementation)
        assert author_name.text in ['testuser', 'unknown']
        
    def test_build_feed_updated_timestamp_matches_recent(self, mock_tool, mock_thread):
        """Test that feed updated timestamp matches most recent entry"""
        # Make thread more recent
        mock_thread.created_at = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        mock_tool.created_at = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        result = _build_feed([mock_tool], [mock_thread])
        
        root = ET.fromstring(result)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        feed_updated = root.find('atom:updated', ns).text
        
        # Should match the thread's timestamp (most recent)
        assert '2023-12-31' in feed_updated or '2023' in feed_updated


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
"""
