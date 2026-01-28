"""Arize AX client wrappers."""

from arize import ArizeClient

from .config import ArizeConfig
from .graphql import ArizeGraphQLClient
from .rest_client import ArizeRestClient


class ArizeClients:
    """Container for all Arize clients."""

    def __init__(self, config: ArizeConfig):
        self.config = config

        # Unified Arize client (v8) for spans export
        # Note: datasets.list() uses REST but has SSL issues in some envs
        # spans.export_to_df() uses Flight protocol
        self.arize = ArizeClient(api_key=config.api_key)

        # REST API v2 client for datasets, experiments, projects
        # Uses Bearer auth which works correctly
        self.rest = ArizeRestClient(api_key=config.api_key)

        # GraphQL client for models and schema (requires developer permissions)
        self.graphql = ArizeGraphQLClient(api_key=config.api_key)

    @property
    def space_id(self) -> str:
        return self.config.space_id
