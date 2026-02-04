"""Analysis tools for trace data using Arize SDK v8."""

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from fastmcp import FastMCP

from ..client import ArizeClients

# Valid span kinds for validation
VALID_SPAN_KINDS = {"LLM", "CHAIN", "RETRIEVER", "TOOL", "EMBEDDING", "AGENT"}

# The actual column name in Arize for span kind
SPAN_KIND_COLUMN = "attributes.openinference.span.kind"


def _validate_span_kind(span_kind: str) -> bool:
    """Validate that span_kind is a known value."""
    return span_kind.upper() in VALID_SPAN_KINDS


def _serialize_value(val):
    """Convert value to JSON-serializable format."""
    if val is None:
        return None

    # Handle numpy arrays early (before pd.isna which fails on arrays)
    if isinstance(val, np.ndarray):
        return [_serialize_value(v) for v in val.tolist()]

    # Handle lists (may contain non-serializable items)
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]

    # Handle dicts (may contain non-serializable items)
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}

    # Check for NaN/NaT (scalar values only)
    try:
        if pd.isna(val):
            return None
    except (ValueError, TypeError):
        pass

    # Handle numpy types
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        if np.isnan(val):
            return None
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)

    # Handle timestamps
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()

    return val


def _df_to_records(df: pd.DataFrame, limit: int = 100) -> list[dict]:
    """Convert DataFrame to JSON-serializable list of records."""
    if df.empty:
        return []

    df = df.head(limit)
    records = []
    for _, row in df.iterrows():
        record = {col: _serialize_value(row[col]) for col in df.columns}
        records.append(record)
    return records


def _safe_std(series: pd.Series) -> float:
    """Calculate standard deviation, returning 0 for single values or NaN."""
    if len(series) <= 1:
        return 0.0
    std_val = series.std()
    if math.isnan(std_val):
        return 0.0
    return float(std_val)


def register_analysis_tools(mcp: FastMCP, clients: ArizeClients):
    """Register analysis tools."""

    @mcp.tool()
    def analyze_errors(
        project_name: str,
        days: int = 7,
        limit: int = 20,
    ) -> dict:
        """Analyze errors in traces to identify common failure patterns.

        Use this to understand why your LLM application is failing and
        find the most frequent error types.

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)
            limit: Maximum number of error examples to return (default: 20)

        Returns:
            error_count: Total number of errors in time range
            time_range_days: Days analyzed
            error_patterns: Most common error messages with counts (top 10)
            sample_errors: Example error spans for debugging
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
                where="status_code = 'ERROR'",
            )

            if df.empty:
                return {
                    "error_count": 0,
                    "time_range_days": days,
                    "message": "No errors found in the specified time range",
                }

            # Try to extract error messages
            error_col = None
            for col in ["status_message", "exception.message", "attributes.exception.message"]:
                if col in df.columns:
                    error_col = col
                    break

            result = {
                "error_count": len(df),
                "time_range_days": days,
            }

            if error_col and error_col in df.columns:
                # Group by error message
                error_counts = df[error_col].value_counts().head(10)
                result["error_patterns"] = [
                    {"message": str(msg), "count": int(count)}
                    for msg, count in error_counts.items()
                ]

            # Sample errors
            result["sample_errors"] = _df_to_records(df, limit)

            return _serialize_value(result)
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def analyze_latency(
        project_name: str,
        days: int = 7,
        span_kind: str = None,
    ) -> dict:
        """Analyze latency distribution to identify performance bottlenecks.

        Use this to understand response time patterns and find slow operations.
        Filter by span_kind to analyze specific operation types (e.g., just LLM calls).

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)
            span_kind: Optional filter (LLM, CHAIN, RETRIEVER, TOOL, EMBEDDING, AGENT)

        Returns:
            span_count: Number of spans analyzed
            time_range_days: Days analyzed
            span_kind: Filter applied (if any)
            latency_stats: Latency metrics in milliseconds:
                - min_ms, max_ms, mean_ms, median_ms, std_ms
                - p50_ms, p75_ms, p90_ms, p95_ms, p99_ms (percentiles)
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # Validate span_kind early if provided
            if span_kind and not _validate_span_kind(span_kind):
                return {
                    "error": f"Invalid span_kind: {span_kind}",
                    "valid_kinds": list(VALID_SPAN_KINDS),
                }

            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
            )

            if df.empty:
                return {
                    "span_count": 0,
                    "time_range_days": days,
                    "message": "No spans found in the specified time range",
                }

            # Filter by span_kind client-side (API WHERE clause has column name issues)
            if span_kind and SPAN_KIND_COLUMN in df.columns:
                df = df[df[SPAN_KIND_COLUMN] == span_kind.upper()]
                if df.empty:
                    return {
                        "span_count": 0,
                        "time_range_days": days,
                        "span_kind": span_kind,
                        "message": f"No spans of kind '{span_kind.upper()}' found",
                    }

            # Find latency column
            latency_col = None
            for col in ["latency_ms", "duration_ms", "attributes.latency_ms"]:
                if col in df.columns:
                    latency_col = col
                    break

            if not latency_col:
                return {
                    "span_count": len(df),
                    "time_range_days": days,
                    "error": "No latency column found in data",
                    "available_columns": list(df.columns),
                }

            latencies = df[latency_col].dropna()

            return _serialize_value({
                "span_count": len(df),
                "time_range_days": days,
                "span_kind": span_kind,
                "latency_stats": {
                    "min_ms": float(latencies.min()),
                    "max_ms": float(latencies.max()),
                    "mean_ms": float(latencies.mean()),
                    "median_ms": float(latencies.median()),
                    "std_ms": _safe_std(latencies),
                    "p50_ms": float(latencies.quantile(0.50)),
                    "p75_ms": float(latencies.quantile(0.75)),
                    "p90_ms": float(latencies.quantile(0.90)),
                    "p95_ms": float(latencies.quantile(0.95)),
                    "p99_ms": float(latencies.quantile(0.99)),
                },
            })
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_trace_statistics(
        project_name: str,
        days: int = 7,
    ) -> dict:
        """Get aggregate statistics for a project's traces.

        Use this to get a high-level overview of your LLM application's
        activity, including volume, success rates, and token usage.

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)

        Returns:
            total_spans: Total number of spans
            unique_traces: Number of distinct request traces
            time_range_days: Days analyzed
            by_span_kind: Breakdown by operation type (LLM, CHAIN, etc.)
            by_status: Breakdown by status (OK, ERROR)
            token_usage: Token consumption stats (total, mean, max) if available
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
            )

            if df.empty:
                return {
                    "total_spans": 0,
                    "time_range_days": days,
                    "message": "No spans found in the specified time range",
                }

            result = {
                "total_spans": len(df),
                "time_range_days": days,
            }

            # Count unique traces
            if "context.trace_id" in df.columns:
                result["unique_traces"] = df["context.trace_id"].nunique()

            # Breakdown by span kind
            if SPAN_KIND_COLUMN in df.columns:
                result["by_span_kind"] = df[SPAN_KIND_COLUMN].value_counts().to_dict()

            # Breakdown by status
            if "status_code" in df.columns:
                result["by_status"] = df["status_code"].value_counts().to_dict()

            # Token usage if available
            token_col = None
            for col in [
                "attributes.llm.token_count.total",
                "attributes.llm.token_count.prompt",
                "llm.token_count.total",
            ]:
                if col in df.columns:
                    token_col = col
                    break

            if token_col:
                tokens = df[token_col].dropna()
                if not tokens.empty:
                    result["token_usage"] = {
                        "total": int(tokens.sum()),
                        "mean": float(tokens.mean()),
                        "max": int(tokens.max()),
                    }

            return _serialize_value(result)
        except Exception as e:
            return {"error": str(e)}
