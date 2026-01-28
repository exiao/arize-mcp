"""Arize AX MCP Server - Main entry point."""

from fastmcp import FastMCP

from .config import get_config
from .client import ArizeClients
from .tools import (
    register_model_tools,
    register_trace_tools,
    register_dataset_tools,
    register_analysis_tools,
)

# Create the MCP server
mcp = FastMCP(
    "Arize AX",
    instructions="Query and analyze traces, spans, datasets, and experiments from Arize AX observability platform",
)


def _setup_tools():
    """Initialize clients and register tools."""
    config = get_config()
    clients = ArizeClients(config)

    register_model_tools(mcp, clients)
    register_trace_tools(mcp, clients)
    register_dataset_tools(mcp, clients)
    register_analysis_tools(mcp, clients)


# Register tools on import
_setup_tools()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
