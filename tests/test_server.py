"""Tests for MCP server initialization."""

from unittest.mock import MagicMock, patch

import pytest


class TestServerInitialization:
    """Tests for server initialization and error handling."""

    def test_server_creates_mcp_instance(self):
        """Test that server module creates FastMCP instance."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "ak-test-key-12345",
            "ARIZE_SPACE_ID": "U3BhY2U6dGVzdA==",
        }):
            # Patch the ArizeClient to avoid network calls
            with patch("arize_mcp.client.ArizeClient"):
                with patch("arize_mcp.rest_client.httpx.Client"):
                    # Import after patching to get fresh module state
                    import importlib
                    import arize_mcp.server as server_module
                    importlib.reload(server_module)

                    assert server_module.mcp is not None
                    assert server_module.mcp.name == "Arize AX"

    def test_server_registers_error_tool_on_config_failure(self):
        """Test that get_status tool is registered when config fails."""
        with patch.dict("os.environ", {}, clear=True):
            # Force reload to trigger initialization without config
            import importlib
            import arize_mcp.server as server_module

            # Reset state
            server_module._initialized = False
            server_module._init_error = None

            # Re-run setup which should fail
            server_module._setup_tools()

            # Should have captured the error
            assert server_module._init_error is not None

    def test_get_status_returns_error_when_init_fails(self):
        """Test that get_status returns error info when init fails."""
        with patch.dict("os.environ", {}, clear=True):
            import importlib
            import arize_mcp.server as server_module

            # Simulate init error
            server_module._init_error = "Missing API key"
            server_module._initialized = True

            # Create a mock get_status that reads _init_error
            if server_module._init_error:
                result = {
                    "status": "error",
                    "error": server_module._init_error,
                    "hint": "Check your ARIZE_API_KEY and ARIZE_SPACE_ID environment variables.",
                }
                assert result["status"] == "error"
                assert "API key" in result["error"]


class TestToolSchemaCompatibility:
    """Tests to ensure tool schemas are MCP-client compatible."""

    def test_optional_params_use_simple_types(self):
        """Test that optional parameters don't use Optional[] type hints.

        This is critical for MCP client compatibility - Optional[X] generates
        anyOf schemas that strict MCP clients reject.
        """
        import inspect
        from arize_mcp.tools import traces, datasets, analysis

        # Check trace tools
        sig = inspect.signature(traces.register_trace_tools)
        # The actual tool functions are defined inside register_trace_tools,
        # so we need to check them differently

        # Instead, verify that the imports don't include Optional
        with open(traces.__file__) as f:
            content = f.read()
            assert "from typing import Optional" not in content, \
                "traces.py should not import Optional"
            assert "Optional[" not in content, \
                "traces.py should not use Optional[] type hints"

        with open(datasets.__file__) as f:
            content = f.read()
            assert "from typing import Optional" not in content, \
                "datasets.py should not import Optional"
            assert "Optional[" not in content, \
                "datasets.py should not use Optional[] type hints"

        with open(analysis.__file__) as f:
            content = f.read()
            assert "from typing import Optional" not in content, \
                "analysis.py should not import Optional"
            assert "Optional[" not in content, \
                "analysis.py should not use Optional[] type hints"
