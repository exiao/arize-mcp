"""Pytest fixtures for arize-mcp tests."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from arize_mcp.config import ArizeConfig


@pytest.fixture
def mock_config():
    """Create a mock ArizeConfig."""
    with patch.dict("os.environ", {
        "ARIZE_API_KEY": "ak-test-api-key-12345",
        "ARIZE_SPACE_ID": "U3BhY2U6dGVzdC1zcGFjZQ==",  # base64 for "Space:test-space"
    }):
        yield ArizeConfig()


@pytest.fixture
def mock_rest_client():
    """Create a mock REST client."""
    client = MagicMock()

    # Mock projects
    client.list_projects.return_value = [
        {"id": "proj-1", "name": "test-project"},
        {"id": "proj-2", "name": "bloom_prod"},
    ]

    # Mock datasets
    client.list_datasets.return_value = [
        {"id": "ds-1", "name": "test-dataset", "example_count": 10},
        {"id": "ds-2", "name": "eval-dataset", "example_count": 50},
    ]
    client.get_dataset.return_value = {
        "id": "ds-1",
        "name": "test-dataset",
        "description": "Test dataset",
    }
    client.list_dataset_examples.return_value = [
        {"id": "ex-1", "input": "test input", "output": "test output"},
    ]
    client.create_dataset.return_value = {
        "id": "ds-new",
        "name": "new-dataset",
    }

    # Mock experiments
    client.list_experiments.return_value = [
        {"id": "exp-1", "name": "test-experiment"},
    ]
    client.get_experiment.return_value = {
        "id": "exp-1",
        "name": "test-experiment",
        "dataset_id": "ds-1",
    }
    client.list_experiment_runs.return_value = [
        {"id": "run-1", "status": "completed"},
    ]

    return client


@pytest.fixture
def mock_graphql_client():
    """Create a mock GraphQL client."""
    client = MagicMock()

    client.list_models.return_value = [
        {"id": "model-1", "name": "test-project"},
    ]
    client.get_tracing_schema.return_value = {
        "span_properties": ["name", "span_kind", "status_code"],
        "evaluations": ["correctness", "relevance"],
    }

    return client


@pytest.fixture
def mock_arize_client():
    """Create a mock Arize SDK client."""
    client = MagicMock()

    # Mock spans export
    mock_df = pd.DataFrame({
        "context.trace_id": ["trace-1", "trace-1", "trace-2"],
        "context.span_id": ["span-1", "span-2", "span-3"],
        "attributes.openinference.span.kind": ["LLM", "CHAIN", "LLM"],
        "status_code": ["OK", "OK", "ERROR"],
        "latency_ms": [100.0, 50.0, 200.0],
        "attributes.input.value": ["input1", "input2", "input3"],
        "attributes.output.value": ["output1", "output2", "output3"],
    })
    client.spans.export_to_df.return_value = mock_df

    # Mock experiments
    mock_experiment = MagicMock()
    mock_experiment.id = "exp-new"

    mock_results_df = pd.DataFrame({
        "id": ["run-1", "run-2"],
        "example_id": ["ex-1", "ex-2"],
        "result": ["output 1", "output 2"],
        "result.trace.id": ["trace-1", "trace-2"],
        "result.trace.timestamp": [1234567890, 1234567891],
    })

    client.experiments.run.return_value = (mock_experiment, mock_results_df)

    # Mock experiments.list_runs
    mock_run = MagicMock()
    mock_run.id = "run-1"
    mock_run.example_id = "ex-1"
    mock_run.output = "test output"
    mock_run.additional_properties = {"trace_id": "trace-1"}

    mock_runs_response = MagicMock()
    mock_runs_response.experiment_runs = [mock_run]
    client.experiments.list_runs.return_value = mock_runs_response

    return client


@pytest.fixture
def mock_clients(mock_config, mock_rest_client, mock_graphql_client, mock_arize_client):
    """Create a mock ArizeClients container."""
    clients = MagicMock()
    clients.config = mock_config
    clients.space_id = mock_config.space_id
    clients.rest = mock_rest_client
    clients.graphql = mock_graphql_client
    clients.arize = mock_arize_client
    return clients


@pytest.fixture
def sample_trace_df():
    """Create a sample trace DataFrame for testing."""
    return pd.DataFrame({
        "context.trace_id": ["trace-1", "trace-1", "trace-2", "trace-3"],
        "context.span_id": ["span-1", "span-2", "span-3", "span-4"],
        "attributes.openinference.span.kind": ["LLM", "CHAIN", "LLM", "RETRIEVER"],
        "status_code": ["OK", "OK", "ERROR", "OK"],
        "latency_ms": [100.0, 50.0, 200.0, 75.0],
        "status_message": [None, None, "Rate limit exceeded", None],
        "attributes.llm.token_count.total": [100, None, 500, None],
    })


@pytest.fixture
def empty_df():
    """Create an empty DataFrame for testing edge cases."""
    return pd.DataFrame()
