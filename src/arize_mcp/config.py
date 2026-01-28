"""Configuration for Arize AX MCP server."""

import base64
import re

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArizeConfig(BaseSettings):
    """Configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ARIZE_",
        env_file=".env",
    )

    api_key: str
    space_id: str

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that the API key has the expected format."""
        if not v.startswith("ak-"):
            raise ValueError(
                "ARIZE_API_KEY must start with 'ak-'. "
                "Get your API key from: https://app.arize.com > Space Settings > API Keys"
            )
        return v

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        """Validate that the space ID is valid base64."""
        # Space IDs are base64-encoded and typically start with "U3BhY2U6"
        # which decodes to "Space:"
        if not re.match(r"^[A-Za-z0-9+/]+=*$", v):
            raise ValueError(
                "ARIZE_SPACE_ID must be a valid base64 string. "
                "Find it in your Arize URL: /spaces/YOUR_SPACE_ID/..."
            )
        try:
            base64.b64decode(v)
        except Exception:
            raise ValueError(
                "ARIZE_SPACE_ID must be a valid base64 string. "
                "Find it in your Arize URL: /spaces/YOUR_SPACE_ID/..."
            )
        return v


def get_config() -> ArizeConfig:
    """Get configuration from environment."""
    return ArizeConfig()
