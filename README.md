# Arize AX MCP Server

MCP server to access Arize AX data, query traces, manage datasets, and run experiments from Claude Code.

## Features

- **Datasets**: List, create, and manage datasets for experiments
- **Experiments**: List experiments and view results
- **Traces**: Export and filter traces/spans with SQL-style queries
- **Analysis**: Analyze errors, latency distributions, and trace statistics

## Quick Start

### 1. Get your Arize credentials

1. **API Key**: Go to [Arize AX](https://app.arize.com) > Space Settings > API Keys > Generate Key
2. **Space ID**: Found in your Arize Space Settings

### 2. Configure Claude Code

Run this command to add the server to Claude Code:

```bash
claude mcp add arize \
  --transport stdio \
  -e ARIZE_API_KEY=<your-api-key> \
  -e ARIZE_SPACE_ID=<your-space-id> \
  -- uvx --from git+https://github.com/exiao/arize-mcp.git arize-mcp
```

That's it! No cloning or manual installation required.

<details>
<summary>Alternative: Manual JSON configuration</summary>

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project settings):

```json
{
  "mcpServers": {
    "arize": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/exiao/arize-mcp.git", "arize-mcp"],
      "env": {
        "ARIZE_API_KEY": "<your-api-key>",
        "ARIZE_SPACE_ID": "<your-space-id>"
      }
    }
  }
}
```

</details>

<details>
<summary>Alternative: Install from source</summary>

If you want to modify the server or run from a local copy:

```bash
git clone https://github.com/exiao/arize-mcp.git
cd arize-mcp
uv pip install -e .
```

Then configure Claude Code with:

```json
{
  "mcpServers": {
    "arize": {
      "command": "arize-mcp",
      "env": {
        "ARIZE_API_KEY": "<your-api-key>",
        "ARIZE_SPACE_ID": "<your-space-id>"
      }
    }
  }
}
```

</details>

### 4. Use in Claude Code

Once configured, you can ask Claude Code questions like:

```
"List my Arize projects"
"Export traces from bloom_prod for the last 7 days"
"Show me errors in my-project"
"What's the p95 latency for LLM spans?"
"Create a dataset called 'evaluation-set'"
```

## Available Tools

### Projects & Schema
| Tool | Description |
|------|-------------|
| `list_projects` | List all projects in your Arize space |
| `get_model_schema` | Get tracing schema (span properties, evals, annotations) |

### Traces & Spans
| Tool | Description |
|------|-------------|
| `export_traces` | Export traces with time range and column filters |
| `get_trace` | Get all spans for a specific trace ID |
| `filter_spans` | Filter spans by kind, errors, or custom WHERE clause |

### Datasets
| Tool | Description |
|------|-------------|
| `list_datasets` | List all datasets |
| `get_dataset` | Get dataset contents and examples |
| `create_dataset` | Create a new dataset |
| `delete_dataset` | Delete a dataset |

### Experiments
| Tool | Description |
|------|-------------|
| `list_experiments` | List all experiments |
| `get_experiment` | Get experiment results and runs |

### Analysis
| Tool | Description |
|------|-------------|
| `analyze_errors` | Summarize errors with patterns |
| `analyze_latency` | Latency stats (p50, p90, p95, p99) |
| `get_trace_statistics` | Aggregate stats by span kind and status |

## Example Usage

### Export and analyze traces

```
User: "Export traces from bloom_prod for the last 24 hours"

Claude: I'll export the traces from your bloom_prod project.
[Calls export_traces with project_name="bloom_prod", days=1]

Found 1,607 spans. Here's a summary:
- 1,450 LLM Generation spans
- 157 Chain spans
- Average latency: 245ms
```

### Investigate errors

```
User: "Show me errors in bloom_prod from the last week"

Claude: I'll analyze errors in your project.
[Calls analyze_errors with project_name="bloom_prod", days=7]

Found 23 errors:
- "Rate limit exceeded" (15 occurrences)
- "Context length exceeded" (5 occurrences)
- "Invalid response format" (3 occurrences)
```

### Filter specific spans

```
User: "Find spans where token count > 1000"

Claude: I'll filter spans with high token usage.
[Calls filter_spans with where="attributes.llm.token_count.total > 1000"]

Found 45 spans with token count > 1000...
```

## Configuration Options

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ARIZE_API_KEY` | Yes | API key from Arize AX |
| `ARIZE_SPACE_ID` | Yes | Space ID from Arize URL |

### API Permissions

Different features require different API permissions:

| Feature | Permissions Needed |
|---------|-------------------|
| Datasets & Experiments | Dataset access |
| Projects & Schema | Developer permissions |
| Trace Export | Export permissions |

If you get permission errors, generate a new Service Key with the required permissions in Arize AX > Space Settings > API Keys.

## Testing Your Setup

Run the credential test script:

```bash
export ARIZE_API_KEY="your-api-key"
export ARIZE_SPACE_ID="your-space-id"
python test_credentials.py
```

This tests each API endpoint and shows which ones work with your API key.

## Troubleshooting

### "Authentication failed" or "Unable to validate API key"
- Verify your API key is correct and not expired
- Generate a new Service Key with export permissions
- Ensure the Space ID matches your API key's organization

### "User does not have developer permissions"
- Your API key needs developer permissions for GraphQL queries
- Contact your Arize administrator or generate a new key with developer access

### "Model does not exist"
- Check that the project name matches exactly (case-sensitive)
- Use `list_projects` to see available project names

## Development

```bash
# Install with dev dependencies
pip install --pre -e ".[dev]"

# Run tests
pytest

# Test the server locally
fastmcp dev src/arize_mcp/server.py
```

## Technical Details

This MCP server uses:
- **Arize SDK v8** (beta) for trace export via Flight protocol
- **REST API v2** for datasets and experiments
- **GraphQL API** for project listing and schema queries
- **FastMCP** for MCP server implementation
