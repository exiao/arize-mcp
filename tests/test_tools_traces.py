"""Tests for trace tools."""

import pandas as pd
import pytest
from fastmcp import FastMCP

from arize_mcp.tools.traces import register_trace_tools, _validate_trace_id, _validate_span_kind


class TestValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_trace_id_accepts_uuid(self):
        """Test that UUID-format trace IDs are valid."""
        assert _validate_trace_id("550e8400-e29b-41d4-a716-446655440000")
        assert _validate_trace_id("abc123def456")
        assert _validate_trace_id("ABCDEF123456")

    def test_validate_trace_id_rejects_invalid(self):
        """Test that invalid trace IDs are rejected."""
        assert not _validate_trace_id("'; DROP TABLE traces; --")
        assert not _validate_trace_id("invalid<script>")
        assert not _validate_trace_id("")

    def test_validate_span_kind_accepts_valid(self):
        """Test that valid span kinds are accepted."""
        assert _validate_span_kind("LLM")
        assert _validate_span_kind("llm")
        assert _validate_span_kind("CHAIN")
        assert _validate_span_kind("RETRIEVER")
        assert _validate_span_kind("TOOL")
        assert _validate_span_kind("EMBEDDING")
        assert _validate_span_kind("AGENT")

    def test_validate_span_kind_rejects_invalid(self):
        """Test that invalid span kinds are rejected."""
        assert not _validate_span_kind("INVALID")
        assert not _validate_span_kind("unknown")


class TestExportTraces:
    """Tests for export_traces tool."""

    def test_export_traces_returns_data(self, mock_clients):
        """Test that export_traces returns trace data."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["export_traces"]
        result = tool.fn(project_name="test-project", days=7, limit=100)

        assert "total_rows" in result
        assert "columns" in result
        assert "traces" in result
        assert result["total_rows"] == 3

    def test_export_traces_respects_limit(self, mock_clients):
        """Test that export_traces respects the limit parameter."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["export_traces"]
        result = tool.fn(project_name="test-project", days=7, limit=2)

        assert len(result["traces"]) <= 2

    def test_export_traces_handles_auth_error(self, mock_clients):
        """Test error handling for authentication failures."""
        mock_clients.arize.spans.export_to_df.side_effect = Exception("unauthenticated")

        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["export_traces"]
        result = tool.fn(project_name="test-project")

        assert "error" in result
        assert "Authentication failed" in result["error"]
        assert "hint" in result

    def test_export_traces_handles_not_found(self, mock_clients):
        """Test error handling for project not found."""
        mock_clients.arize.spans.export_to_df.side_effect = Exception("project not found")

        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["export_traces"]
        result = tool.fn(project_name="nonexistent")

        assert "error" in result
        assert "not found" in result["error"]


class TestGetTrace:
    """Tests for get_trace tool."""

    def test_get_trace_returns_spans(self, mock_clients):
        """Test that get_trace returns spans for a trace ID."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_trace"]
        result = tool.fn(
            project_name="test-project",
            trace_id="550e8400-e29b-41d4-a716-446655440000",
            days=7,
        )

        assert "trace_id" in result
        assert "span_count" in result
        assert "spans" in result

    def test_get_trace_validates_trace_id(self, mock_clients):
        """Test that invalid trace IDs are rejected."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_trace"]
        result = tool.fn(
            project_name="test-project",
            trace_id="'; DROP TABLE--",
            days=7,
        )

        assert "error" in result
        assert "Invalid trace_id" in result["error"]


class TestFilterSpans:
    """Tests for filter_spans tool."""

    def test_filter_spans_with_span_kind(self, mock_clients):
        """Test filtering by span kind."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["filter_spans"]
        result = tool.fn(project_name="test-project", span_kind="LLM")

        assert "total_matches" in result
        assert "filter_applied" in result
        assert "spans" in result
        assert "attributes.openinference.span.kind = 'LLM'" in result["filter_applied"]

    def test_filter_spans_with_error_filter(self, mock_clients):
        """Test filtering for error spans."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["filter_spans"]
        result = tool.fn(project_name="test-project", has_error=True)

        assert "filter_applied" in result
        assert "status_code = 'ERROR'" in result["filter_applied"]

    def test_filter_spans_validates_span_kind(self, mock_clients):
        """Test that invalid span kinds are rejected."""
        mcp = FastMCP("test")
        register_trace_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["filter_spans"]
        result = tool.fn(project_name="test-project", span_kind="INVALID")

        assert "error" in result
        assert "Invalid span_kind" in result["error"]
        assert "valid_kinds" in result
