# CLAUDE.md

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
    ├── datasets.py    # list/get/create/delete datasets, run_experiment
    └── analysis.py    # analyze_errors, analyze_latency, get_trace_statistics

tests/
├── conftest.py            # Shared fixtures (mock clients, sample data)
├── test_config.py         # Config validation tests
├── test_server.py         # Server initialization tests
├── test_rest_client.py    # REST client tests (space_id handling)
├── test_tools_models.py   # Project/model tool tests
├── test_tools_traces.py   # Trace export/filter tool tests
├── test_tools_datasets.py # Dataset/experiment/run_experiment tests
└── test_tools_analysis.py # Analysis tool tests
```

## Key Commands

```bash
# Install from git (no clone required)
uvx --from git+https://github.com/exiao/arize-mcp.git arize-mcp

# Install from source
uv pip install -e .

# Run the MCP server
uv run python -m arize_mcp.server

# Test credentials
ARIZE_API_KEY="..." ARIZE_SPACE_ID="..." python test_credentials.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=arize_mcp --cov-report=term-missing

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

## MCP Tools Reference

### Projects & Schema
| Tool | Parameters | Description |
|------|------------|-------------|
| `list_projects` | none | List all projects (REST fallback to GraphQL) |
| `get_model_schema` | `model_id`, `days=7` | Get tracing schema (requires developer permissions) |

### Traces & Spans
| Tool | Parameters | Description |
|------|------------|-------------|
| `export_traces` | `project_name`, `days=7`, `limit=100`, `columns=None` | Export spans with optional column filtering |
| `get_trace` | `project_name`, `trace_id`, `days=7` | Get all spans for a specific trace ID |
| `filter_spans` | `project_name`, `days=7`, `limit=100`, `where=None`, `span_kind=None`, `has_error=None` | Filter spans with SQL-style WHERE |

### Datasets & Experiments
| Tool | Parameters | Description |
|------|------------|-------------|
| `list_datasets` | none | List all datasets in the space |
| `get_dataset` | `dataset_id`, `limit=100` | Get dataset metadata and examples |
| `create_dataset` | `name`, `description=None`, `examples=None` | Create new dataset |
| `delete_dataset` | `dataset_id` | Delete a dataset |
| `list_experiments` | none | List all experiments |
| `get_experiment` | `experiment_id`, `limit=100` | Get experiment runs (uses SDK v8) |
| `run_experiment` | `dataset_id`, `name`, `prompt_template`, ... | Run LLM task over dataset |

### Analysis
| Tool | Parameters | Description |
|------|------------|-------------|
| `analyze_errors` | `project_name`, `days=7`, `limit=20` | Identify error patterns |
| `analyze_latency` | `project_name`, `days=7`, `span_kind=None` | Latency percentiles (p50, p75, p90, p95, p99) |
| `get_trace_statistics` | `project_name`, `days=7` | Aggregate stats including token usage |

## Tool Parameters

All trace-related tools use `project_name` (not `model_id`) to match the Arize SDK v8 API:

```python
export_traces(project_name="bloom_prod", days=7, limit=100)
filter_spans(project_name="bloom_prod", span_kind="LLM", has_error=True)
analyze_latency(project_name="bloom_prod", span_kind="LLM")
```

**Valid span_kind values**: `LLM`, `CHAIN`, `RETRIEVER`, `TOOL`, `EMBEDDING`, `AGENT` (case-insensitive)

## Running Experiments

The `run_experiment` tool runs LLM tasks over dataset examples:

```python
# OpenAI
run_experiment(
    dataset_id="abc123",
    name="eval_v1",
    prompt_template="Classify: {input.text}",
    openai_api_key="sk-...",
    model="gpt-4o-mini"
)

# OpenRouter
run_experiment(
    dataset_id="abc123",
    name="claude_eval",
    prompt_template="Analyze: {input}",
    openai_api_key="sk-or-...",
    base_url="https://openrouter.ai/api/v1",
    model="anthropic/claude-3-haiku"
)

# Dry run (test without logging to Arize)
run_experiment(..., dry_run=True, dry_run_count=5)

# Passthrough (test prompt formatting without LLM calls)
run_experiment(..., passthrough=True)
```

Prompt template placeholders: `{input}`, `{input.field}`, `{output}`, `{metadata}`, `{id}`, `{dataset_row}`

## Environment Variables

Required:
- `ARIZE_API_KEY`: API key starting with `ak-`
- `ARIZE_SPACE_ID`: Base64-encoded space ID from Arize URL

Optional (for `run_experiment`):
- `OPENAI_API_KEY`: OpenAI or OpenRouter API key for running experiments
- `OPENAI_BASE_URL`: Custom API endpoint (e.g., `https://openrouter.ai/api/v1`)

## Configuration

Config validation in `config.py`:
- API key must start with `ak-` (enforced by Pydantic validator)
- Space ID must be valid base64 (regex: `^[A-Za-z0-9+/]+=*$`)
- Supports `.env` file loading
- Extra environment variables are ignored (`extra="ignore"`)

## MCP Protocol Compatibility

Critical for MCP JSON protocol compatibility (in `client.py`):
- Arize SDK logging suppressed at ERROR level to prevent ANSI escape codes
- tqdm progress bars disabled via `TQDM_DISABLE=1`
- Server uses delayed initialization with `get_status()` tool for debugging credential issues

## Testing

Unit tests use mocks and don't require credentials:

```bash
uv run pytest                    # Run all tests
uv run pytest tests/test_tools_datasets.py  # Specific file
uv run pytest -v                 # Verbose output
```

Integration testing with real credentials:

```bash
export ARIZE_API_KEY="your-api-key"
export ARIZE_SPACE_ID="your-space-id"
python test_credentials.py
```

The `test_credentials.py` script tests all API endpoints:
- REST API v2 (datasets, experiments)
- GraphQL API (projects, schema)
- SDK v8 Flight (trace export)

## Error Handling

Tools return error dicts with hints instead of raising exceptions:

```python
{"error": "message", "hint": "suggestion"}
```

Fallback mechanisms:
- `list_projects`: REST API → GraphQL fallback
- `get_experiment`: Uses SDK v8 for runs (REST may not return them)
- Span kind filtering: Client-side (WHERE clause has issues with this column)

## Common Issues

1. **"Unable to validate API key"**: The API key lacks export permissions. Generate a new Service Key with export access.

2. **"User does not have developer permissions"**: GraphQL requires developer permissions. Use a key with developer access.

3. **Page size errors**: GraphQL queries use `first: 50` (maximum allowed).

4. **Pre-release dependency**: Arize SDK v8 is in beta. Install with `pip install --pre` or use `uv`.

5. **JSON serialization errors**: The codebase uses `_serialize_value()` to handle numpy/pandas types (np.integer, np.floating, pd.Timestamp, etc.)

6. **Project name case sensitivity**: Project names are case-sensitive. Use `list_projects` to verify exact names.

7. **Trace ID validation**: Trace IDs are validated with regex `^[a-fA-F0-9-]{1,64}$` to prevent injection.

## Dependencies

From `pyproject.toml`:
- `fastmcp>=2.0` - MCP server framework
- `arize>=8.0.0b2` (pre-release) - SDK v8 for experiments and trace export
- `pandas>=2.0` - DataFrame handling for span exports
- `pydantic-settings>=2.0` - Configuration management
- `httpx>=0.24` - REST and GraphQL API client
- `openai>=1.0` - Required for `run_experiment` tool

Dev dependencies:
- `pytest>=7.0`, `pytest-cov>=4.0`

Python requires: `>=3.10`
