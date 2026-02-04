"""Tests for model/project tools."""

from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP

from arize_mcp.tools.models import register_model_tools


class TestListProjects:
    """Tests for list_projects tool."""

    def test_list_projects_returns_projects(self, mock_clients):
        """Test that list_projects returns project list."""
        mcp = FastMCP("test")
        register_model_tools(mcp, mock_clients)

        # Get the registered tool
        tool = mcp._tool_manager._tools["list_projects"]
        result = tool.fn()

        assert "projects" in result
        assert "count" in result
        assert result["count"] == 2
        assert result["projects"][0]["name"] == "test-project"

    def test_list_projects_falls_back_to_graphql(self, mock_clients):
        """Test fallback to GraphQL when REST fails."""
        mock_clients.rest.list_projects.side_effect = RuntimeError("REST error")

        mcp = FastMCP("test")
        register_model_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["list_projects"]
        result = tool.fn()

        # Should have fallen back to GraphQL
        assert "projects" in result
        mock_clients.graphql.list_models.assert_called_once()

    def test_list_projects_returns_error_on_failure(self, mock_clients):
        """Test error handling when both APIs fail."""
        mock_clients.rest.list_projects.side_effect = RuntimeError("REST error")
        mock_clients.graphql.list_models.side_effect = RuntimeError("GraphQL error")

        mcp = FastMCP("test")
        register_model_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["list_projects"]
        result = tool.fn()

        assert "error" in result
        assert "hint" in result


class TestGetModelSchema:
    """Tests for get_model_schema tool."""

    def test_get_model_schema_returns_schema(self, mock_clients):
        """Test that get_model_schema returns schema info."""
        mcp = FastMCP("test")
        register_model_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_model_schema"]
        result = tool.fn(model_id="test-project", days=7)

        assert "span_properties" in result
        assert "evaluations" in result
        mock_clients.graphql.get_tracing_schema.assert_called_once()

    def test_get_model_schema_returns_error_on_failure(self, mock_clients):
        """Test error handling when GraphQL fails."""
        mock_clients.graphql.get_tracing_schema.side_effect = RuntimeError("Permission denied")

        mcp = FastMCP("test")
        register_model_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_model_schema"]
        result = tool.fn(model_id="test-project", days=7)

        assert "error" in result
        assert "hint" in result
