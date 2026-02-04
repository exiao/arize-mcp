"""Model/project management tools."""

from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from ..client import ArizeClients


def register_model_tools(mcp: FastMCP, clients: ArizeClients):
    """Register model-related tools."""

    @mcp.tool()
    def list_projects() -> dict:
        """List all projects (tracing endpoints) in the Arize space.

        Projects contain traces from your LLM applications. Each project has a
        unique name that you use with export_traces(), filter_spans(), and
        analysis tools.

        Returns:
            projects: List of projects with id and name
            count: Total number of projects

        Note: Use the project 'name' (not 'id') when calling trace tools like
        export_traces(project_name="your-project-name").
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
        """Get the tracing schema for a project, showing available span properties and evaluations.

        Use this to discover what columns are available when filtering traces.

        Args:
            model_id: The project/model ID from list_projects() (use the 'id' field, not 'name')
            days: Number of days to look back for schema discovery (default: 7)

        Returns:
            span_properties: List of available span attribute columns
            evaluations: List of configured LLM evaluation metrics
            annotations: List of human annotation fields

        Note: Requires GraphQL developer permissions. If this fails, use
        export_traces() to see available columns directly.
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
