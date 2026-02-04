"""Tests for analysis tools."""

import pandas as pd
import pytest
from fastmcp import FastMCP

from arize_mcp.tools.analysis import register_analysis_tools, _safe_std


class TestSafeStd:
    """Tests for _safe_std helper function."""

    def test_safe_std_single_value(self):
        """Test that single value returns 0."""
        series = pd.Series([100.0])
        assert _safe_std(series) == 0.0

    def test_safe_std_empty_series(self):
        """Test that empty series returns 0."""
        series = pd.Series([], dtype=float)
        assert _safe_std(series) == 0.0

    def test_safe_std_multiple_values(self):
        """Test that multiple values compute std correctly."""
        series = pd.Series([10.0, 20.0, 30.0])
        result = _safe_std(series)
        assert result > 0


class TestAnalyzeErrors:
    """Tests for analyze_errors tool."""

    def test_analyze_errors_returns_summary(self, mock_clients, sample_trace_df):
        """Test that analyze_errors returns error summary."""
        # Filter to only error spans
        error_df = sample_trace_df[sample_trace_df["status_code"] == "ERROR"]
        mock_clients.arize.spans.export_to_df.return_value = error_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_errors"]
        result = tool.fn(project_name="test-project", days=7, limit=20)

        assert "error_count" in result
        assert "time_range_days" in result
        assert result["error_count"] == 1

    def test_analyze_errors_no_errors(self, mock_clients, empty_df):
        """Test analyze_errors when no errors exist."""
        mock_clients.arize.spans.export_to_df.return_value = empty_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_errors"]
        result = tool.fn(project_name="test-project", days=7)

        assert result["error_count"] == 0
        assert "message" in result

    def test_analyze_errors_extracts_patterns(self, mock_clients):
        """Test that error patterns are extracted from messages."""
        error_df = pd.DataFrame({
            "status_code": ["ERROR", "ERROR", "ERROR"],
            "status_message": ["Rate limit", "Rate limit", "Timeout"],
        })
        mock_clients.arize.spans.export_to_df.return_value = error_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_errors"]
        result = tool.fn(project_name="test-project")

        assert "error_patterns" in result
        assert len(result["error_patterns"]) >= 1

    def test_analyze_errors_handles_exception(self, mock_clients):
        """Test error handling in analyze_errors."""
        mock_clients.arize.spans.export_to_df.side_effect = Exception("API error")

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_errors"]
        result = tool.fn(project_name="test-project")

        assert "error" in result


class TestAnalyzeLatency:
    """Tests for analyze_latency tool."""

    def test_analyze_latency_returns_stats(self, mock_clients, sample_trace_df):
        """Test that analyze_latency returns latency statistics."""
        mock_clients.arize.spans.export_to_df.return_value = sample_trace_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_latency"]
        result = tool.fn(project_name="test-project", days=7)

        assert "span_count" in result
        assert "latency_stats" in result
        stats = result["latency_stats"]
        assert "min_ms" in stats
        assert "max_ms" in stats
        assert "mean_ms" in stats
        assert "p95_ms" in stats
        assert "p99_ms" in stats

    def test_analyze_latency_with_span_kind_filter(self, mock_clients, sample_trace_df):
        """Test filtering by span kind."""
        mock_clients.arize.spans.export_to_df.return_value = sample_trace_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_latency"]
        result = tool.fn(project_name="test-project", span_kind="LLM")

        assert result["span_kind"] == "LLM"

    def test_analyze_latency_rejects_invalid_span_kind(self, mock_clients):
        """Test that invalid span kinds are rejected."""
        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_latency"]
        result = tool.fn(project_name="test-project", span_kind="INVALID")

        assert "error" in result
        assert "valid_kinds" in result

    def test_analyze_latency_no_data(self, mock_clients, empty_df):
        """Test analyze_latency when no data exists."""
        mock_clients.arize.spans.export_to_df.return_value = empty_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["analyze_latency"]
        result = tool.fn(project_name="test-project")

        assert result["span_count"] == 0
        assert "message" in result


class TestGetTraceStatistics:
    """Tests for get_trace_statistics tool."""

    def test_get_trace_statistics_returns_counts(self, mock_clients, sample_trace_df):
        """Test that get_trace_statistics returns aggregate counts."""
        mock_clients.arize.spans.export_to_df.return_value = sample_trace_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_trace_statistics"]
        result = tool.fn(project_name="test-project", days=7)

        assert "total_spans" in result
        assert "unique_traces" in result
        assert "by_span_kind" in result
        assert "by_status" in result
        assert result["total_spans"] == 4
        assert result["unique_traces"] == 3

    def test_get_trace_statistics_includes_token_usage(self, mock_clients, sample_trace_df):
        """Test that token usage stats are included when available."""
        mock_clients.arize.spans.export_to_df.return_value = sample_trace_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_trace_statistics"]
        result = tool.fn(project_name="test-project")

        assert "token_usage" in result
        assert "total" in result["token_usage"]
        assert "mean" in result["token_usage"]

    def test_get_trace_statistics_no_data(self, mock_clients, empty_df):
        """Test get_trace_statistics when no data exists."""
        mock_clients.arize.spans.export_to_df.return_value = empty_df

        mcp = FastMCP("test")
        register_analysis_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_trace_statistics"]
        result = tool.fn(project_name="test-project")

        assert result["total_spans"] == 0
        assert "message" in result
