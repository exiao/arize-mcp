"""REST API client for Arize AX API v2."""

import httpx
from typing import Optional

REST_API_BASE = "https://api.arize.com/v2"


class ArizeRestClient:
    """Client for Arize AX REST API v2."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> dict:
        """Make an API request."""
        url = f"{REST_API_BASE}{endpoint}"
        response = self._client.request(method, url, params=params, json=json)

        if response.status_code == 401:
            raise RuntimeError(f"Authentication failed: {response.json().get('detail', 'Invalid API key')}")
        if response.status_code == 404:
            raise RuntimeError(f"Not found: {endpoint}")

        response.raise_for_status()
        return response.json()

    # ========== Projects ==========

    def list_projects(self) -> list[dict]:
        """List all projects."""
        data = self._request("GET", "/projects")
        return data.get("projects", [])

    def get_project(self, project_id: str) -> dict:
        """Get a project by ID."""
        return self._request("GET", f"/projects/{project_id}")

    # ========== Datasets ==========

    def list_datasets(self) -> list[dict]:
        """List all datasets."""
        data = self._request("GET", "/datasets")
        return data.get("datasets", [])

    def get_dataset(self, dataset_id: str) -> dict:
        """Get a dataset by ID."""
        return self._request("GET", f"/datasets/{dataset_id}")

    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        examples: Optional[list[dict]] = None,
    ) -> dict:
        """Create a new dataset."""
        payload = {"name": name}
        if description:
            payload["description"] = description
        if examples:
            payload["examples"] = examples
        return self._request("POST", "/datasets", json=payload)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        self._request("DELETE", f"/datasets/{dataset_id}")
        return True

    def list_dataset_examples(
        self,
        dataset_id: str,
        version_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """List examples in a dataset."""
        params = {"limit": limit}
        if version_id:
            params["version_id"] = version_id
        data = self._request("GET", f"/datasets/{dataset_id}/examples", params=params)
        return data.get("examples", [])

    # ========== Experiments ==========

    def list_experiments(self) -> list[dict]:
        """List all experiments."""
        data = self._request("GET", "/experiments")
        return data.get("experiments", [])

    def get_experiment(self, experiment_id: str) -> dict:
        """Get an experiment by ID."""
        return self._request("GET", f"/experiments/{experiment_id}")

    def list_experiment_runs(self, experiment_id: str, limit: int = 100) -> list[dict]:
        """List runs for an experiment."""
        params = {"limit": limit}
        data = self._request("GET", f"/experiments/{experiment_id}/runs", params=params)
        return data.get("runs", [])
