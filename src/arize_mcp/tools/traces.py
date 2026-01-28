"""Trace export and query tools using Arize SDK v8."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from fastmcp import FastMCP

from ..client import ArizeClients

# Valid span kinds for validation
VALID_SPAN_KINDS = {"LLM", "CHAIN", "RETRIEVER", "TOOL", "EMBEDDING", "AGENT"}

# Regex pattern for validating trace IDs (typically UUIDs or hex strings)
TRACE_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{1,64}$")


def _validate_trace_id(trace_id: str) -> bool:
    """Validate that a trace ID looks like a valid identifier."""
    return bool(TRACE_ID_PATTERN.match(trace_id))


def _validate_span_kind(span_kind: str) -> bool:
    """Validate that span_kind is a known value."""
    return span_kind.upper() in VALID_SPAN_KINDS


def _df_to_records(df: pd.DataFrame, limit: int = 100) -> list[dict]:
    """Convert DataFrame to list of records, handling NaN values."""
    if df.empty:
        return []

    # Take first N rows
    df = df.head(limit)

    # Convert to records, replacing NaN with None
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return records


def register_trace_tools(mcp: FastMCP, clients: ArizeClients):
    """Register trace-related tools."""

    @mcp.tool()
    def export_traces(
        project_name: str,
        days: int = 7,
        limit: int = 100,
        columns: Optional[list[str]] = None,
    ) -> dict:
        """Export traces/spans from an Arize project as a table.

        Args:
            project_name: The project name to export traces from
            days: Number of days to look back (default: 7)
            limit: Maximum number of spans to return (default: 100)
            columns: Optional list of specific columns to include.
                    Common columns: context.span_id, context.trace_id,
                    attributes.input.value, attributes.output.value,
                    attributes.llm.token_count.total, status_code

        Returns:
            Dictionary with traces data and metadata
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # Use v8 client: client.spans.export_to_df()
            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
                columns=columns,
            )

            return {
                "total_rows": len(df),
                "columns": list(df.columns),
                "traces": _df_to_records(df, limit),
            }
        except Exception as e:
            error_msg = str(e)
            if "unauthenticated" in error_msg.lower() or "api key" in error_msg.lower():
                return {
                    "error": "Authentication failed",
                    "details": error_msg,
                    "hint": "Please verify your ARIZE_API_KEY is valid and has export permissions.",
                }
            if "not found" in error_msg.lower():
                return {
                    "error": f"Project '{project_name}' not found",
                    "details": error_msg,
                    "hint": "Check that the project name matches exactly (case-sensitive).",
                }
            return {"error": error_msg}

    @mcp.tool()
    def get_trace(
        project_name: str,
        trace_id: str,
        days: int = 7,
    ) -> dict:
        """Get all spans for a specific trace.

        Args:
            project_name: The project name
            trace_id: The trace ID to retrieve
            days: Number of days to search back (default: 7)

        Returns:
            All spans belonging to the trace
        """
        try:
            # Validate trace_id to prevent injection
            if not _validate_trace_id(trace_id):
                return {
                    "error": "Invalid trace_id format",
                    "hint": "Trace IDs should be alphanumeric with optional hyphens (UUID format).",
                }

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # Use v8 client with filter
            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
                where=f"context.trace_id = '{trace_id}'",
            )

            spans = _df_to_records(df, limit=1000)

            return {
                "trace_id": trace_id,
                "span_count": len(spans),
                "spans": spans,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def filter_spans(
        project_name: str,
        days: int = 7,
        limit: int = 100,
        where: Optional[str] = None,
        span_kind: Optional[str] = None,
        has_error: Optional[bool] = None,
    ) -> dict:
        """Filter spans by various criteria.

        Args:
            project_name: The project name
            days: Number of days to look back (default: 7)
            limit: Maximum number of spans to return (default: 100)
            where: SQL-style filter expression (e.g., "attributes.llm.token_count.total > 1000")
            span_kind: Filter by span kind (e.g., "LLM", "CHAIN", "RETRIEVER", "TOOL")
            has_error: If true, only return spans with errors

        Returns:
            Filtered spans with metadata
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            # Build WHERE clause
            conditions = []
            if where:
                conditions.append(where)
            if span_kind:
                # Validate span_kind against allowlist
                if not _validate_span_kind(span_kind):
                    return {
                        "error": f"Invalid span_kind: {span_kind}",
                        "valid_kinds": list(VALID_SPAN_KINDS),
                    }
                conditions.append(f"span_kind = '{span_kind.upper()}'")
            if has_error is True:
                conditions.append("status_code = 'ERROR'")
            elif has_error is False:
                conditions.append("status_code != 'ERROR'")

            where_clause = " AND ".join(conditions) if conditions else None

            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
                where=where_clause,
            )

            return {
                "total_matches": len(df),
                "filter_applied": where_clause,
                "spans": _df_to_records(df, limit),
            }
        except Exception as e:
            return {"error": str(e)}
