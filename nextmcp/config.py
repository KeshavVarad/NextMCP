"""
Configuration management for NextMCP applications.

Supports loading configuration from:
- .env files
- YAML configuration files
- Environment variables
- Command-line arguments
"""

import logging
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager that loads settings from multiple sources.

    Priority order (highest to lowest):
    1. Environment variables
    2. Config file (YAML)
    3. Default values
    """

    def __init__(
        self,
        config_file: str | None = None,
        env_file: str | None = ".env",
        load_env: bool = True,
    ):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file (default: config.yaml)
            env_file: Path to .env file (default: .env)
            load_env: Whether to load .env file (default: True)
        """
        self._config: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {
            "host": "127.0.0.1",
            "port": 8000,
            "log_level": "INFO",
            "debug": False,
        }

        # Load .env file if available
        if load_env and load_dotenv is not None:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment variables from {env_file}")
            else:
                logger.debug(f"No .env file found at {env_file}")

        # Load YAML config file if provided
        if config_file:
            self.load_yaml(config_file)
        else:
            # Try default locations
            for default_path in ["config.yaml", "config.yml", "nextmcp.yaml"]:
                if Path(default_path).exists():
                    self.load_yaml(default_path)
                    break

        # Apply defaults
        for key, value in self._defaults.items():
            if key not in self._config:
                self._config[key] = value

    def load_yaml(self, file_path: str) -> None:
        """
        Load configuration from a YAML file.

        Args:
            file_path: Path to the YAML configuration file
        """
        if yaml is None:
            logger.warning("PyYAML not installed, skipping YAML config loading")
            return

        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return

        try:
            with open(path) as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    self._config.update(yaml_config)
                    logger.info(f"Loaded configuration from {file_path}")
        except Exception as e:
            logger.error(f"Error loading config from {file_path}: {e}")
            raise

    def get(self, key: str, default: Any = None, env_var: str | None = None) -> Any:
        """
        Get a configuration value.

        Checks in order:
        1. Environment variable (if env_var specified)
        2. Config file value
        3. Default value

        Args:
            key: Configuration key
            default: Default value if key not found
            env_var: Optional environment variable name to check

        Returns:
            Configuration value
        """
        # Check environment variable first
        if env_var:
            env_value = os.getenv(env_var)
            if env_value is not None:
                return self._parse_env_value(env_value)

        # Check uppercase env var based on key
        env_key = key.upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._parse_env_value(env_value)

        # Check config file
        if key in self._config:
            return self._config[key]

        # Return default
        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type.

        Args:
            value: String value from environment variable

        Returns:
            Parsed value (bool, int, float, or string)
        """
        # Handle booleans
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Handle numbers
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def get_host(self) -> str:
        """Get server host."""
        return self.get("host", self._defaults["host"], "MCP_HOST")

    def get_port(self) -> int:
        """Get server port."""
        port = self.get("port", self._defaults["port"], "MCP_PORT")
        return int(port)

    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get("log_level", self._defaults["log_level"], "LOG_LEVEL")

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return bool(self.get("debug", self._defaults["debug"], "DEBUG"))

    def to_dict(self) -> dict[str, Any]:
        """
        Get all configuration as a dictionary.

        Returns:
            Dictionary of all configuration values
        """
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in configuration."""
        return key in self._config


def load_config(config_file: str | None = None, env_file: str = ".env", **overrides) -> Config:
    """
    Convenience function to load configuration.

    Args:
        config_file: Path to YAML config file
        env_file: Path to .env file
        **overrides: Additional configuration overrides

    Returns:
        Config instance

    Example:
        config = load_config(config_file="config.yaml")
        host = config.get_host()
        port = config.get_port()
    """
    config = Config(config_file=config_file, env_file=env_file)

    # Apply overrides
    for key, value in overrides.items():
        config.set(key, value)

    return config
