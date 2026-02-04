"""Tests for configuration validation."""

import pytest
from unittest.mock import patch

from pydantic import ValidationError

from arize_mcp.config import ArizeConfig, get_config


class TestArizeConfig:
    """Tests for ArizeConfig validation."""

    def test_valid_config(self):
        """Test that valid config values pass validation."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "ak-test-key-12345",
            "ARIZE_SPACE_ID": "U3BhY2U6dGVzdA==",
        }):
            config = ArizeConfig()
            assert config.api_key == "ak-test-key-12345"
            assert config.space_id == "U3BhY2U6dGVzdA=="

    def test_api_key_must_start_with_ak(self):
        """Test that API key must start with 'ak-'."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "invalid-key",
            "ARIZE_SPACE_ID": "U3BhY2U6dGVzdA==",
        }):
            with pytest.raises(ValidationError) as exc_info:
                ArizeConfig()
            assert "ak-" in str(exc_info.value)

    def test_space_id_must_be_valid_base64(self):
        """Test that space ID must be valid base64."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "ak-test-key",
            "ARIZE_SPACE_ID": "not-valid-base64!!!",
        }):
            with pytest.raises(ValidationError) as exc_info:
                ArizeConfig()
            assert "base64" in str(exc_info.value).lower()

    def test_missing_api_key(self):
        """Test that missing API key raises error."""
        with patch.dict("os.environ", {
            "ARIZE_SPACE_ID": "U3BhY2U6dGVzdA==",
        }, clear=True):
            with pytest.raises(ValidationError):
                ArizeConfig()

    def test_missing_space_id(self):
        """Test that missing space ID raises error."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "ak-test-key",
        }, clear=True):
            with pytest.raises(ValidationError):
                ArizeConfig()

    def test_get_config_returns_config(self):
        """Test that get_config() returns an ArizeConfig instance."""
        with patch.dict("os.environ", {
            "ARIZE_API_KEY": "ak-test-key-12345",
            "ARIZE_SPACE_ID": "U3BhY2U6dGVzdA==",
        }):
            config = get_config()
            assert isinstance(config, ArizeConfig)
