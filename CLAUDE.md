# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that provides Claude Code access to Arize AX, an AI observability platform. It enables querying traces, managing datasets, and analyzing LLM application performance directly from Claude Code.

## Architecture

```
src/arize_mcp/
├── server.py          # FastMCP server entry point
├── config.py          # Pydantic settings (ARIZE_API_KEY, ARIZE_SPACE_ID)
├── client.py          # Client container (ArizeClient, REST, GraphQL)
├── rest_client.py     # REST API v2 client for datasets/experiments
├── graphql.py         # GraphQL client for projects/schema
└── tools/
    ├── models.py      # list_projects, get_model_schema
    ├── traces.py      # export_traces, get_trace, filter_spans
    ├── datasets.py    # list/get/create/delete datasets, experiments
    └── analysis.py    # analyze_errors, analyze_latency, get_trace_statistics
```

## Key Commands

```bash
# Install dependencies
uv pip install -e .

# Run the MCP server
uv run python -m arize_mcp.server

# Test credentials
ARIZE_API_KEY="..." ARIZE_SPACE_ID="..." python test_credentials.py

# Run tests
pytest

# Development mode with FastMCP
fastmcp dev src/arize_mcp/server.py
```

## API Clients

The server uses three different API clients:

1. **ArizeClient (SDK v8)**: For trace/span export via Flight protocol
   - `clients.arize.spans.export_to_df()`

2. **ArizeRestClient**: For datasets and experiments via REST API v2
   - Uses `Authorization: Bearer <api_key>` header
   - Endpoint: `https://api.arize.com/v2/`

3. **ArizeGraphQLClient**: For project listing and schema queries
   - Uses `x-api-key: <api_key>` header
   - Endpoint: `https://app.arize.com/graphql`

## Tool Parameters

All trace-related tools use `project_name` (not `model_id`) to match the Arize SDK v8 API:

```python
export_traces(project_name="bloom_prod", days=7, limit=100)
filter_spans(project_name="bloom_prod", span_kind="LLM", has_error=True)
analyze_latency(project_name="bloom_prod", span_kind="LLM")
```

## Environment Variables

Required:
- `ARIZE_API_KEY`: API key starting with `ak-`
- `ARIZE_SPACE_ID`: Base64-encoded space ID from Arize URL

## Testing

The `test_credentials.py` script tests all API endpoints:
- REST API v2 (datasets, experiments)
- GraphQL API (projects, schema)
- SDK v8 Flight (trace export)

## Common Issues

1. **"Unable to validate API key"**: The API key lacks export permissions. Generate a new Service Key with export access.

2. **"User does not have developer permissions"**: GraphQL requires developer permissions. Use a key with developer access.

3. **Page size errors**: GraphQL queries use `first: 50` (maximum allowed).

4. **Pre-release dependency**: Arize SDK v8 is in beta. Install with `pip install --pre` or use `uv`.
