"""Integration tests for MCP server functionality.

These tests verify that the MCP server:
1. Starts successfully in stdio mode
2. Responds to JSON-RPC requests
3. Exposes the expected tools
4. Tools execute correctly

Run with: pytest tests/test_mcp_server.py -v
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


@pytest.fixture
def mcp_server_params(test_db_path):
    """Create MCP server parameters for testing."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-X", "utf8", "-m", "src.server"],
        env={
            "KALIMA_DB_PATH": test_db_path,
        },
        cwd=str(Path(__file__).parent.parent),
    )


@pytest.fixture
async def mcp_session(mcp_server_params):
    """Create an MCP session for testing."""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


class TestMCPServerStartup:
    """Test that MCP server starts correctly."""

    def test_server_module_imports(self):
        """Test that server module can be imported."""
        from src import server
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'main')

    def test_server_has_expected_tools_registered(self):
        """Test that expected tools are defined in tool modules."""
        from src.tools import identity, navigation, research, structural_analysis
        from src.tools import context, workflow, discourse, hermeneutics
        
        assert hasattr(identity, 'register')
        assert hasattr(navigation, 'register')
        assert hasattr(research, 'register')
        assert hasattr(structural_analysis, 'register')
        assert hasattr(context, 'register')
        assert hasattr(workflow, 'register')
        assert hasattr(discourse, 'register')
        assert hasattr(hermeneutics, 'register')


class TestMCPProtocol:
    """Test MCP protocol compliance."""

    @pytest.mark.asyncio
    async def test_initialize_request(self, mcp_session):
        """Test that initialize request succeeds."""
        result = await mcp_session.list_tools()
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_session):
        """Test that tools/list returns expected tools."""
        result = await mcp_session.list_tools()
        
        tool_names = [t.name for t in result.tools]
        
        expected_tools = [
            "decompose_address",
            "classify_element",
            "resolve_address",
            "get_composition",
            "get_verse_with_context",
            "compare_with_traditional",
        ]
        
        for tool in expected_tools:
            assert tool in tool_names, f"Expected tool '{tool}' not found"

    @pytest.mark.asyncio
    async def test_ping(self, mcp_session):
        """Test that ping request succeeds."""
        result = await mcp_session.send_ping()
        assert result is not None


class TestMCPIdentityTools:
    """Test identity tool functionality."""

    @pytest.mark.asyncio
    async def test_resolve_address(self, mcp_session):
        """Test resolve_address tool."""
        result = await mcp_session.call_tool(
            "resolve_address",
            {"address": "1:1"}
        )
        
        assert result is not None
        assert len(result.content) > 0
        assert result.content[0].text is not None

    @pytest.mark.asyncio
    async def test_classify_element(self, mcp_session):
        """Test classify_element tool."""
        result = await mcp_session.call_tool(
            "classify_element",
            {"address": "root:0620"}
        )
        
        assert result is not None
        assert len(result.content) > 0


class TestMCPContextTools:
    """Test context tool functionality."""

    @pytest.mark.asyncio
    async def test_get_verse_with_context(self, mcp_session):
        """Test get_verse_with_context tool."""
        result = await mcp_session.call_tool(
            "get_verse_with_context",
            {"surah": 1, "ayah": 1}
        )
        
        assert result is not None
        assert len(result.content) > 0
        
        content = json.loads(result.content[0].text)
        assert "ref" in content
        assert content["ref"] == "1:1"
        assert "text" in content
        assert "words" in content

    @pytest.mark.asyncio
    async def test_get_verse_lattice(self, mcp_session):
        """Test get_verse_lattice tool."""
        result = await mcp_session.call_tool(
            "get_verse_lattice",
            {"surah": 1, "ayah": 1}
        )
        
        assert result is not None
        assert len(result.content) > 0


class TestMCPServerName:
    """Test server configuration."""

    def test_server_name_is_kalima(self):
        """Test that server name is 'kalima-server'."""
        from src.server import mcp
        assert mcp.name == "kalima-server"


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_db_env_var_name(self):
        """Test that KALIMA_DB_PATH is used (not SCHOLAR_DB_PATH)."""
        from src import db
        
        source = Path(__file__).parent.parent / "src" / "db.py"
        content = source.read_text()
        
        assert "KALIMA_DB_PATH" in content
        assert "SCHOLAR_DB_PATH" not in content

    def test_no_scholar_references_in_source(self):
        """Test that no 'scholar' references remain in db.py."""
        from src import db
        
        source = Path(__file__).parent.parent / "src" / "db.py"
        content = source.read_text()
        
        assert "scholar" not in content.lower()
