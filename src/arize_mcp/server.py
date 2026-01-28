"""Arize AX MCP Server - Main entry point."""

from fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP(
    "Arize AX",
    instructions="Query and analyze traces, spans, datasets, and experiments from Arize AX observability platform",
)

# Track initialization state
_initialized = False
_init_error: str | None = None


def _setup_tools() -> None:
    """Initialize clients and register tools."""
    global _initialized, _init_error

    if _initialized:
        return

    try:
        from .config import get_config
        from .client import ArizeClients
        from .tools import (
            register_model_tools,
            register_trace_tools,
            register_dataset_tools,
            register_analysis_tools,
        )

        config = get_config()
        clients = ArizeClients(config)

        register_model_tools(mcp, clients)
        register_trace_tools(mcp, clients)
        register_dataset_tools(mcp, clients)
        register_analysis_tools(mcp, clients)

        _initialized = True
    except Exception as e:
        _init_error = str(e)
        _register_error_tool()
        _initialized = True  # Mark as initialized to avoid retrying


def _register_error_tool() -> None:
    """Register a tool that reports the initialization error."""
    @mcp.tool()
    def get_status() -> dict:
        """Get the status of the Arize MCP server.

        Returns configuration errors if the server failed to initialize.
        """
        if _init_error:
            return {
                "status": "error",
                "error": _init_error,
                "hint": "Check your ARIZE_API_KEY and ARIZE_SPACE_ID environment variables.",
            }
        return {"status": "ok"}


# Initialize tools on import - errors are caught and exposed via get_status tool
_setup_tools()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
