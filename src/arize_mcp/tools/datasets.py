"""Dataset management tools using Arize REST API v2."""

import json

from fastmcp import FastMCP

from ..client import ArizeClients


def _serialize_value(val):
    """Convert non-JSON-serializable values to JSON-compatible types."""
    import numpy as np
    import pandas as pd

    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        if np.isnan(val):
            return None
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    return val


def register_dataset_tools(mcp: FastMCP, clients: ArizeClients):
    """Register dataset-related tools."""

    @mcp.tool()
    def list_datasets() -> dict:
        """List all datasets in the Arize space.

        Datasets contain examples (input/output pairs) used for running experiments
        and evaluating LLM performance.

        Returns:
            datasets: List of dataset objects with id, name, created_at
            count: Total number of datasets
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
        """Get a dataset and its examples by ID.

        Use list_datasets() first to find available dataset IDs.

        Args:
            dataset_id: The dataset ID (base64 encoded, e.g., "RGF0YXNldDo...")
            limit: Maximum number of examples to return (default: 100)

        Returns:
            dataset: Dataset metadata (id, name, description, versions)
            examples: List of examples with input/output pairs
            example_count: Number of examples returned
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
            name: Name for the new dataset (must be unique)
            description: Optional description of the dataset
            examples: Optional list of examples to add. Each example should have
                'input' and 'output' keys, e.g., [{"input": "question", "output": "answer"}]

        Returns:
            success: True if created successfully
            dataset: Created dataset object with id, name
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

        Experiments are runs of LLM tasks over datasets, created by run_experiment().
        Each experiment contains multiple runs (one per dataset example).

        Returns:
            experiments: List of experiment objects with id, name, dataset_id, created_at
            count: Total number of experiments
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
        """Get detailed results from an experiment.

        Use list_experiments() first to find available experiment IDs.

        Args:
            experiment_id: The experiment ID (base64 encoded, e.g., "RXhwZXJpbWVudDo...")
            limit: Maximum number of runs to return (default: 100)

        Returns:
            experiment: Experiment metadata (id, name, dataset_id, created_at)
            runs: List of individual run results, each with:
                - id: Run identifier
                - example_id: ID of the dataset example used
                - output: LLM output for this example
                - trace_id: Link to trace for debugging
            run_count: Number of runs returned
        """
        try:
            experiment = clients.rest.get_experiment(experiment_id)

            # Use SDK to get runs (REST API may not return them)
            sdk_runs = clients.arize.experiments.list_runs(
                experiment_id=experiment_id, limit=limit
            )

            runs = []
            for run in sdk_runs.experiment_runs:
                run_dict = {
                    "id": run.id,
                    "example_id": run.example_id,
                    "output": run.output,
                }
                if run.additional_properties:
                    run_dict.update(run.additional_properties)
                runs.append(run_dict)

            return {
                "experiment": experiment,
                "runs": runs,
                "run_count": len(runs),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def run_experiment(
        dataset_id: str,
        name: str,
        prompt_template: str,
        openai_api_key: str = None,
        base_url: str = None,
        model: str = "gpt-4o-mini",
        system_prompt: str = None,
        temperature: float = 0.0,
        concurrency: int = 3,
        dry_run: bool = False,
        dry_run_count: int = 10,
        passthrough: bool = False,
    ) -> dict:
        """Run an experiment on a dataset using an LLM task.

        This tool runs an LLM task over each example in a dataset and records
        the results as an experiment in Arize.

        Args:
            dataset_id: ID of the dataset to run the experiment on
            name: Name for the experiment
            prompt_template: Prompt template with placeholders like {input} or
                {input.question}. Available variables: input, output,
                metadata, id, dataset_row (full row dict)
            openai_api_key: API key for LLM calls. If not provided, will
                check OPENAI_API_KEY environment variable
            base_url: Base URL for OpenAI-compatible API. Use for OpenRouter
                (https://openrouter.ai/api/v1), Azure, or local models.
                If not provided, checks OPENAI_BASE_URL env var, then defaults to OpenAI.
            model: Model to use (default: gpt-4o-mini). For OpenRouter, use
                format like "anthropic/claude-3-haiku" or "openai/gpt-4o"
            system_prompt: Optional system prompt for the LLM
            temperature: Temperature for LLM generation (default: 0.0)
            concurrency: Parallel execution level (default: 3)
            dry_run: If True, test locally without logging to Arize (default: False)
            dry_run_count: Number of examples to run in dry-run mode (default: 10)
            passthrough: If True, return formatted prompt instead of calling LLM.
                Useful for testing prompt templates without API costs.

        Returns:
            Experiment results including ID, run count, and sample results

        Example (OpenAI):
            run_experiment(
                dataset_id="abc123",
                name="sentiment_analysis_v1",
                openai_api_key="sk-...",
                prompt_template="Classify the sentiment of: {input.text}",
                system_prompt="You are a sentiment classifier."
            )

        Example (OpenRouter):
            run_experiment(
                dataset_id="abc123",
                name="claude_eval",
                openai_api_key="sk-or-...",
                base_url="https://openrouter.ai/api/v1",
                model="anthropic/claude-3-haiku",
                prompt_template="Analyze: {input}"
            )
        """
        try:
            import os

            # Resolve API key and base URL
            resolved_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            resolved_base_url = base_url or os.environ.get("OPENAI_BASE_URL")

            if not passthrough and not resolved_api_key:
                return {
                    "error": "API key required",
                    "hint": "Provide openai_api_key parameter or set OPENAI_API_KEY environment variable. "
                    "Alternatively, use passthrough=True to test prompt formatting without LLM calls.",
                }

            openai_client = None
            if not passthrough:
                from openai import OpenAI
                client_kwargs = {"api_key": resolved_api_key}
                if resolved_base_url:
                    client_kwargs["base_url"] = resolved_base_url
                openai_client = OpenAI(**client_kwargs)

            def _format_prompt(template: str, example) -> str:
                """Format prompt template with example data.

                The example can be either:
                - A dict-like _ReadOnly object with keys: input, output, id, etc.
                - An Example dataclass with attributes: input, output, metadata, etc.
                """
                # Handle both dict-like and attribute-based access
                def get_value(obj, key, default=None):
                    try:
                        return obj[key] if hasattr(obj, '__getitem__') else getattr(obj, key, default)
                    except (KeyError, AttributeError):
                        return default

                # Build context from example data
                # The example may have flat keys (input, output) or nested Example structure
                context = {}

                # Try to get standard fields
                input_val = get_value(example, 'input')
                output_val = get_value(example, 'output')
                metadata_val = get_value(example, 'metadata')
                id_val = get_value(example, 'id')

                # Handle input - could be a string, dict, or None
                if input_val is not None:
                    if isinstance(input_val, str):
                        context['input'] = input_val
                    elif hasattr(input_val, 'items'):
                        context['input'] = dict(input_val)
                    else:
                        context['input'] = input_val
                else:
                    context['input'] = {}

                # Handle output similarly
                if output_val is not None:
                    if isinstance(output_val, str):
                        context['output'] = output_val
                    elif hasattr(output_val, 'items'):
                        context['output'] = dict(output_val)
                    else:
                        context['output'] = output_val
                else:
                    context['output'] = {}

                # Metadata and ID
                if metadata_val and hasattr(metadata_val, 'items'):
                    context['metadata'] = dict(metadata_val)
                else:
                    context['metadata'] = metadata_val or {}

                context['id'] = str(id_val) if id_val else ''

                # Also include the full example as dataset_row for access to all fields
                if hasattr(example, 'items'):
                    context['dataset_row'] = dict(example)
                elif hasattr(example, 'dataset_row'):
                    context['dataset_row'] = dict(example.dataset_row) if example.dataset_row else {}
                else:
                    context['dataset_row'] = {}

                # Handle nested dot notation like {input.question}
                # First, flatten nested dicts for simple access
                flat_context = {}
                for key, value in context.items():
                    flat_context[key] = value
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_context[f"{key}.{sub_key}"] = sub_value

                # Replace placeholders
                result = template
                for key, value in flat_context.items():
                    placeholder = "{" + key + "}"
                    if placeholder in result:
                        if isinstance(value, dict):
                            result = result.replace(placeholder, json.dumps(value))
                        else:
                            result = result.replace(placeholder, str(value))

                return result

            def task(example) -> str:
                """Run LLM on an example or return formatted prompt in passthrough mode."""
                formatted_prompt = _format_prompt(prompt_template, example)

                if passthrough:
                    # Return formatted prompt without calling LLM
                    return formatted_prompt

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": formatted_prompt})

                response = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )

                return response.choices[0].message.content

            # Run the experiment
            experiment, results_df = clients.arize.experiments.run(
                name=name,
                dataset_id=dataset_id,
                task=task,
                concurrency=concurrency,
                dry_run=dry_run,
                dry_run_count=dry_run_count,
            )

            # Serialize results
            results = _serialize_value(results_df.to_dict(orient="records"))

            response = {
                "success": True,
                "dry_run": dry_run,
                "results": results[:100] if len(results) > 100 else results,
                "total_runs": len(results),
            }

            if experiment:
                response["experiment"] = {
                    "id": str(experiment.id),
                    "name": name,
                    "dataset_id": dataset_id,
                }

            return response

        except ImportError:
            return {
                "error": "OpenAI package not installed",
                "hint": "Install with: pip install openai",
            }
        except Exception as e:
            error_msg = str(e)
            # Provide helpful hints for common errors
            if "API key" in error_msg or "authentication" in error_msg.lower():
                return {
                    "error": error_msg,
                    "hint": "Check that your OpenAI API key is valid",
                }
            if "dataset" in error_msg.lower() and "not found" in error_msg.lower():
                return {
                    "error": error_msg,
                    "hint": "Verify the dataset_id exists using list_datasets()",
                }
            return {"error": error_msg}
