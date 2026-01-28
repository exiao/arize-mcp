"""GraphQL client for Arize AX API."""

import httpx

GRAPHQL_ENDPOINT = "https://app.arize.com/graphql"

# GraphQL Queries
LIST_MODELS_QUERY = """
query ListModels($spaceId: ID!) {
  node(id: $spaceId) {
    ... on Space {
      models(first: 50) {
        edges {
          node {
            id
            name
            modelType
          }
        }
        pageInfo {
          hasNextPage
        }
      }
    }
  }
}
"""

GET_MODEL_QUERY = """
query GetModel($modelId: ID!) {
  node(id: $modelId) {
    ... on Model {
      id
      name
      modelType
    }
  }
}
"""

GET_TRACING_SCHEMA_QUERY = """
query GetTracingSchema($modelId: ID!, $startTime: DateTime!, $endTime: DateTime!) {
  model: node(id: $modelId) {
    ... on Model {
      name
      tracingSchema(startTime: $startTime, endTime: $endTime) {
        spanProperties(first: 50) {
          edges {
            node {
              dimension {
                name
                dataType
                category
              }
            }
          }
        }
        llmEvals(first: 50) {
          edges {
            node {
              dimension {
                name
                dataType
                category
              }
            }
          }
        }
        annotations(first: 50) {
          edges {
            node {
              dimension {
                name
                dataType
                category
              }
            }
          }
        }
      }
    }
  }
}
"""


class ArizeGraphQLClient:
    """Client for Arize AX GraphQL API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.Client(timeout=30.0)

    def query(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query."""
        response = self._client.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            },
        )

        # Handle HTTP errors with better messages
        if response.status_code == 403:
            body = response.text
            if "developer permissions" in body.lower():
                raise RuntimeError(
                    "GraphQL API requires developer permissions. "
                    "Please ensure your API key has developer access enabled in Arize AX settings."
                )
            raise RuntimeError(f"Access forbidden: {body}")

        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise RuntimeError(f"GraphQL error: {result['errors']}")

        return result.get("data", {})

    def list_models(self, space_id: str) -> list[dict]:
        """List all models in a space."""
        data = self.query(LIST_MODELS_QUERY, {"spaceId": space_id})

        node = data.get("node")
        if not node:
            return []

        models = node.get("models", {}).get("edges", [])
        return [
            {
                "id": edge["node"]["id"],
                "name": edge["node"]["name"],
                "model_type": edge["node"].get("modelType"),
            }
            for edge in models
        ]

    def get_model(self, model_id: str) -> dict | None:
        """Get model details by ID."""
        data = self.query(GET_MODEL_QUERY, {"modelId": model_id})

        node = data.get("node")
        if not node:
            return None

        return {
            "id": node["id"],
            "name": node["name"],
            "model_type": node.get("modelType"),
        }

    def get_tracing_schema(
        self, model_id: str, start_time: str, end_time: str
    ) -> dict:
        """Get tracing schema for a model."""
        data = self.query(
            GET_TRACING_SCHEMA_QUERY,
            {
                "modelId": model_id,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

        model = data.get("model")
        if not model or not model.get("tracingSchema"):
            return {"span_properties": [], "llm_evals": [], "annotations": []}

        schema = model["tracingSchema"]

        def extract_dimensions(connection: dict) -> list[dict]:
            edges = connection.get("edges", [])
            return [
                {
                    "name": edge["node"]["dimension"]["name"],
                    "data_type": edge["node"]["dimension"]["dataType"],
                    "category": edge["node"]["dimension"]["category"],
                }
                for edge in edges
            ]

        return {
            "model_name": model.get("name"),
            "span_properties": extract_dimensions(schema.get("spanProperties", {})),
            "llm_evals": extract_dimensions(schema.get("llmEvals", {})),
            "annotations": extract_dimensions(schema.get("annotations", {})),
        }
