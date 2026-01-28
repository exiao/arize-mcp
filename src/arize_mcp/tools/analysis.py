"""Analysis tools for trace data using Arize SDK v8."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from fastmcp import FastMCP

from ..client import ArizeClients


def register_analysis_tools(mcp: FastMCP, clients: ArizeClients):
    """Register analysis tools."""

    @mcp.tool()
    def analyze_errors(
        project_name: str,
        days: int = 7,
        limit: int = 20,
    ) -> dict:
        """Analyze errors in traces to identify patterns.

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)
            limit: Maximum number of error examples to return (default: 20)

        Returns:
            Error summary with counts and example errors
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
            sample = df.head(limit)
            result["sample_errors"] = sample.where(pd.notnull(sample), None).to_dict(
                orient="records"
            )

            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def analyze_latency(
        project_name: str,
        days: int = 7,
        span_kind: Optional[str] = None,
    ) -> dict:
        """Analyze latency distribution for traces.

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)
            span_kind: Optional filter by span kind (LLM, CHAIN, RETRIEVER, TOOL)

        Returns:
            Latency statistics including percentiles
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            where_clause = f"span_kind = '{span_kind}'" if span_kind else None

            df = clients.arize.spans.export_to_df(
                space_id=clients.space_id,
                project_name=project_name,
                start_time=start_time,
                end_time=end_time,
                where=where_clause,
            )

            if df.empty:
                return {
                    "span_count": 0,
                    "time_range_days": days,
                    "message": "No spans found in the specified time range",
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

            return {
                "span_count": len(df),
                "time_range_days": days,
                "span_kind": span_kind,
                "latency_stats": {
                    "min_ms": float(latencies.min()),
                    "max_ms": float(latencies.max()),
                    "mean_ms": float(latencies.mean()),
                    "median_ms": float(latencies.median()),
                    "std_ms": float(latencies.std()) if len(latencies) > 1 else 0,
                    "p50_ms": float(latencies.quantile(0.50)),
                    "p75_ms": float(latencies.quantile(0.75)),
                    "p90_ms": float(latencies.quantile(0.90)),
                    "p95_ms": float(latencies.quantile(0.95)),
                    "p99_ms": float(latencies.quantile(0.99)),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_trace_statistics(
        project_name: str,
        days: int = 7,
    ) -> dict:
        """Get aggregate statistics for traces.

        Args:
            project_name: The project name to analyze
            days: Number of days to look back (default: 7)

        Returns:
            Statistics including counts by span kind and status
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
            if "span_kind" in df.columns:
                result["by_span_kind"] = df["span_kind"].value_counts().to_dict()

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

            return result
        except Exception as e:
            return {"error": str(e)}
