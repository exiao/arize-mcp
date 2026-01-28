"""Model/project management tools."""

from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from ..client import ArizeClients


def register_model_tools(mcp: FastMCP, clients: ArizeClients):
    """Register model-related tools."""

    @mcp.tool()
    def list_projects() -> dict:
        """List all projects in the Arize space.

        Returns a list of projects with their IDs and names.
        Use the project name as model_id for trace export operations.

        Note: This uses the REST API v2 which requires appropriate permissions.
        If this fails, you can still use export_traces with a known project name.
        """
        try:
            projects = clients.rest.list_projects()
            return {"projects": projects, "count": len(projects)}
        except RuntimeError as e:
            # Try GraphQL as fallback
            try:
                models = clients.graphql.list_models(clients.space_id)
                return {
                    "projects": models,
                    "count": len(models),
                    "note": "Retrieved via GraphQL API",
                }
            except Exception as graphql_error:
                return {
                    "error": str(e),
                    "graphql_error": str(graphql_error),
                    "hint": "If you know your project name, you can use export_traces directly with that name as model_id.",
                }

    @mcp.tool()
    def get_model_schema(
        model_id: str,
        days: int = 7,
    ) -> dict:
        """Get the tracing schema for a model, including span properties, evaluations, and annotations.

        Args:
            model_id: The model ID (from list_projects)
            days: Number of days to look back for schema discovery (default: 7)

        Returns:
            Schema information including span properties, LLM evals, and annotations

        Note: Requires GraphQL developer permissions.
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

            return clients.graphql.get_tracing_schema(
                model_id=model_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )
        except RuntimeError as e:
            return {
                "error": str(e),
                "hint": "Use export_traces to see available columns in the trace data.",
            }
