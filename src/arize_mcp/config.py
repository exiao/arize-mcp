"""Configuration for Arize AX MCP server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ArizeConfig(BaseSettings):
    """Configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ARIZE_",
        env_file=".env",
    )

    api_key: str
    space_id: str


def get_config() -> ArizeConfig:
    """Get configuration from environment."""
    return ArizeConfig()
