"""Dataset management tools using Arize REST API v2."""

from fastmcp import FastMCP

from ..client import ArizeClients


def register_dataset_tools(mcp: FastMCP, clients: ArizeClients):
    """Register dataset-related tools."""

    @mcp.tool()
    def list_datasets() -> dict:
        """List all datasets in the Arize space.

        Returns:
            List of datasets with their IDs, names, and metadata
        """
        try:
            datasets = clients.rest.list_datasets()
            return {
                "datasets": datasets,
                "count": len(datasets),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_dataset(dataset_id: str, limit: int = 100) -> dict:
        """Get a dataset and its examples.

        Args:
            dataset_id: ID of the dataset
            limit: Maximum number of examples to return (default: 100)

        Returns:
            Dataset info with examples
        """
        try:
            dataset = clients.rest.get_dataset(dataset_id)
            examples = clients.rest.list_dataset_examples(dataset_id, limit=limit)

            return {
                "dataset": dataset,
                "examples": examples,
                "example_count": len(examples),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def create_dataset(
        name: str,
        description: str = None,
        examples: list[dict] = None,
    ) -> dict:
        """Create a new dataset in Arize.

        Args:
            name: Name for the new dataset
            description: Optional description of the dataset
            examples: Optional list of example dictionaries to add

        Returns:
            Created dataset info
        """
        try:
            result = clients.rest.create_dataset(
                name=name,
                description=description,
                examples=examples,
            )
            return {
                "success": True,
                "dataset": result,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def delete_dataset(dataset_id: str) -> dict:
        """Delete a dataset from Arize.

        Args:
            dataset_id: ID of the dataset to delete

        Returns:
            Confirmation of deletion
        """
        try:
            clients.rest.delete_dataset(dataset_id)
            return {
                "success": True,
                "deleted_id": dataset_id,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def list_experiments() -> dict:
        """List all experiments in the Arize space.

        Returns:
            List of experiments with their IDs and metadata
        """
        try:
            experiments = clients.rest.list_experiments()
            return {
                "experiments": experiments,
                "count": len(experiments),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_experiment(experiment_id: str, limit: int = 100) -> dict:
        """Get results from an experiment.

        Args:
            experiment_id: ID of the experiment
            limit: Maximum number of runs to return (default: 100)

        Returns:
            Experiment info with runs
        """
        try:
            experiment = clients.rest.get_experiment(experiment_id)
            runs = clients.rest.list_experiment_runs(experiment_id, limit=limit)

            return {
                "experiment": experiment,
                "runs": runs,
                "run_count": len(runs),
            }
        except Exception as e:
            return {"error": str(e)}
