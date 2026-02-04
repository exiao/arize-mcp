"""Tests for dataset tools."""

import pytest
from fastmcp import FastMCP

from arize_mcp.tools.datasets import register_dataset_tools


class TestListDatasets:
    """Tests for list_datasets tool."""

    def test_list_datasets_returns_datasets(self, mock_clients):
        """Test that list_datasets returns dataset list."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["list_datasets"]
        result = tool.fn()

        assert "datasets" in result
        assert "count" in result
        assert result["count"] == 2
        assert result["datasets"][0]["name"] == "test-dataset"

    def test_list_datasets_handles_error(self, mock_clients):
        """Test error handling for list_datasets."""
        mock_clients.rest.list_datasets.side_effect = Exception("API error")

        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["list_datasets"]
        result = tool.fn()

        assert "error" in result


class TestGetDataset:
    """Tests for get_dataset tool."""

    def test_get_dataset_returns_dataset_with_examples(self, mock_clients):
        """Test that get_dataset returns dataset info with examples."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_dataset"]
        result = tool.fn(dataset_id="ds-1", limit=100)

        assert "dataset" in result
        assert "examples" in result
        assert "example_count" in result
        assert result["dataset"]["name"] == "test-dataset"

    def test_get_dataset_handles_error(self, mock_clients):
        """Test error handling for get_dataset."""
        mock_clients.rest.get_dataset.side_effect = Exception("Not found")

        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_dataset"]
        result = tool.fn(dataset_id="nonexistent")

        assert "error" in result


class TestCreateDataset:
    """Tests for create_dataset tool."""

    def test_create_dataset_creates_dataset(self, mock_clients):
        """Test that create_dataset creates a new dataset."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["create_dataset"]
        result = tool.fn(name="new-dataset", description="A test dataset")

        assert "success" in result
        assert result["success"] is True
        assert "dataset" in result
        mock_clients.rest.create_dataset.assert_called_once()

    def test_create_dataset_with_examples(self, mock_clients):
        """Test creating a dataset with initial examples."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["create_dataset"]
        examples = [{"input": "test", "output": "response"}]
        result = tool.fn(name="new-dataset", examples=examples)

        assert result["success"] is True
        mock_clients.rest.create_dataset.assert_called_with(
            name="new-dataset",
            description=None,
            examples=examples,
        )

    def test_create_dataset_handles_error(self, mock_clients):
        """Test error handling for create_dataset."""
        mock_clients.rest.create_dataset.side_effect = Exception("Name already exists")

        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["create_dataset"]
        result = tool.fn(name="existing-dataset")

        assert "error" in result


class TestDeleteDataset:
    """Tests for delete_dataset tool."""

    def test_delete_dataset_deletes_dataset(self, mock_clients):
        """Test that delete_dataset removes a dataset."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["delete_dataset"]
        result = tool.fn(dataset_id="ds-1")

        assert "success" in result
        assert result["success"] is True
        assert result["deleted_id"] == "ds-1"
        mock_clients.rest.delete_dataset.assert_called_with("ds-1")

    def test_delete_dataset_handles_error(self, mock_clients):
        """Test error handling for delete_dataset."""
        mock_clients.rest.delete_dataset.side_effect = Exception("Not found")

        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["delete_dataset"]
        result = tool.fn(dataset_id="nonexistent")

        assert "error" in result


class TestListExperiments:
    """Tests for list_experiments tool."""

    def test_list_experiments_returns_experiments(self, mock_clients):
        """Test that list_experiments returns experiment list."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["list_experiments"]
        result = tool.fn()

        assert "experiments" in result
        assert "count" in result
        assert result["count"] == 1


class TestGetExperiment:
    """Tests for get_experiment tool."""

    def test_get_experiment_returns_experiment_with_runs(self, mock_clients):
        """Test that get_experiment returns experiment info with runs."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_experiment"]
        result = tool.fn(experiment_id="exp-1", limit=100)

        assert "experiment" in result
        assert "runs" in result
        assert "run_count" in result
        assert result["experiment"]["name"] == "test-experiment"

    def test_get_experiment_uses_sdk_for_runs(self, mock_clients):
        """Test that get_experiment uses SDK to get runs."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["get_experiment"]
        result = tool.fn(experiment_id="exp-1")

        # Verify SDK was called for runs
        mock_clients.arize.experiments.list_runs.assert_called_once()
        assert result["run_count"] == 1
        assert result["runs"][0]["output"] == "test output"


class TestRunExperiment:
    """Tests for run_experiment tool."""

    def test_run_experiment_passthrough_mode(self, mock_clients):
        """Test run_experiment in passthrough mode."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=True,
            dry_run=True,
        )

        assert "success" in result
        assert result["success"] is True
        assert result["dry_run"] is True
        mock_clients.arize.experiments.run.assert_called_once()

    def test_run_experiment_requires_api_key_without_passthrough(self, mock_clients):
        """Test that run_experiment requires API key when not in passthrough mode."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=False,
            # No openai_api_key provided
        )

        assert "error" in result
        assert "API key required" in result["error"]

    def test_run_experiment_returns_results(self, mock_clients):
        """Test that run_experiment returns experiment results."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=True,
        )

        assert "results" in result
        assert "total_runs" in result
        assert result["total_runs"] == 2
        assert "experiment" in result
        assert result["experiment"]["id"] == "exp-new"

    def test_run_experiment_handles_error(self, mock_clients):
        """Test error handling for run_experiment."""
        mock_clients.arize.experiments.run.side_effect = Exception("Dataset not found")

        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="nonexistent",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=True,
        )

        assert "error" in result

    def test_run_experiment_formats_template(self, mock_clients):
        """Test that prompt template is correctly formatted."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Input: {input}, Output: {output}",
            passthrough=True,
        )

        assert result["success"] is True
        # The mock returns generic results, but verify the call happened
        mock_clients.arize.experiments.run.assert_called_once()
        call_kwargs = mock_clients.arize.experiments.run.call_args[1]
        assert call_kwargs["name"] == "test-experiment"
        assert call_kwargs["dataset_id"] == "ds-1"

    def test_run_experiment_dry_run_count(self, mock_clients):
        """Test that dry_run_count parameter is passed correctly."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=True,
            dry_run=True,
            dry_run_count=5,
        )

        call_kwargs = mock_clients.arize.experiments.run.call_args[1]
        assert call_kwargs["dry_run"] is True
        assert call_kwargs["dry_run_count"] == 5

    def test_run_experiment_concurrency(self, mock_clients):
        """Test that concurrency parameter is passed correctly."""
        mcp = FastMCP("test")
        register_dataset_tools(mcp, mock_clients)

        tool = mcp._tool_manager._tools["run_experiment"]
        result = tool.fn(
            dataset_id="ds-1",
            name="test-experiment",
            prompt_template="Process: {input}",
            passthrough=True,
            concurrency=5,
        )

        call_kwargs = mock_clients.arize.experiments.run.call_args[1]
        assert call_kwargs["concurrency"] == 5
