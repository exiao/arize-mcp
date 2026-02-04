"""Tests for ArizeRestClient."""

from unittest.mock import MagicMock, patch

import pytest

from arize_mcp.rest_client import ArizeRestClient


class TestArizeRestClientInit:
    """Tests for ArizeRestClient initialization."""

    def test_init_with_space_id(self):
        """Test that ArizeRestClient stores space_id when provided."""
        with patch("arize_mcp.rest_client.httpx.Client"):
            client = ArizeRestClient(
                api_key="ak-test-key",
                space_id="U3BhY2U6dGVzdA=="
            )
            assert client.space_id == "U3BhY2U6dGVzdA=="

    def test_init_without_space_id(self):
        """Test that ArizeRestClient works without space_id (backward compatible)."""
        with patch("arize_mcp.rest_client.httpx.Client"):
            client = ArizeRestClient(api_key="ak-test-key")
            assert client.space_id is None


class TestCreateDatasetPayload:
    """Tests for create_dataset payload construction."""

    @patch("arize_mcp.rest_client.httpx.Client")
    def test_create_dataset_includes_space_id(self, mock_httpx_client):
        """Test that create_dataset includes space_id in the API payload."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "ds-new", "name": "test"}
        mock_httpx_client.return_value.request.return_value = mock_response

        client = ArizeRestClient(
            api_key="ak-test-key",
            space_id="U3BhY2U6dGVzdA=="
        )
        client.create_dataset(
            name="test-dataset",
            description="A test",
            examples=[{"input": "test"}]
        )

        # Verify the request was made with space_id in the payload
        call_args = mock_httpx_client.return_value.request.call_args
        assert call_args is not None
        json_payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_payload["space_id"] == "U3BhY2U6dGVzdA=="
        assert json_payload["name"] == "test-dataset"
        assert json_payload["description"] == "A test"
        assert json_payload["examples"] == [{"input": "test"}]

    @patch("arize_mcp.rest_client.httpx.Client")
    def test_create_dataset_without_space_id(self, mock_httpx_client):
        """Test that create_dataset works without space_id."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "ds-new", "name": "test"}
        mock_httpx_client.return_value.request.return_value = mock_response

        client = ArizeRestClient(api_key="ak-test-key")
        client.create_dataset(name="test-dataset")

        # Verify the request was made without space_id in the payload
        call_args = mock_httpx_client.return_value.request.call_args
        json_payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "space_id" not in json_payload
        assert json_payload["name"] == "test-dataset"

    @patch("arize_mcp.rest_client.httpx.Client")
    def test_create_dataset_minimal_payload(self, mock_httpx_client):
        """Test create_dataset with only required name parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "ds-new", "name": "minimal"}
        mock_httpx_client.return_value.request.return_value = mock_response

        client = ArizeRestClient(
            api_key="ak-test-key",
            space_id="U3BhY2U6dGVzdA=="
        )
        client.create_dataset(name="minimal")

        call_args = mock_httpx_client.return_value.request.call_args
        json_payload = call_args.kwargs.get("json") or call_args[1].get("json")

        # Should have name and space_id, but not description or examples
        assert json_payload["name"] == "minimal"
        assert json_payload["space_id"] == "U3BhY2U6dGVzdA=="
        assert "description" not in json_payload
        assert "examples" not in json_payload
