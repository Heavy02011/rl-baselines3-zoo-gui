"""Configuration manager for loading and saving YAML configuration."""
import os
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from ruamel.yaml import YAML


class ConfigManager(QObject):
    """Manages YAML configuration with round-trip preservation."""

    config_changed = pyqtSignal(str, object)  # key path, new value

    def __init__(self, config_path: str):
        """Initialize the config manager.

        Args:
            config_path: Path to the YAML configuration file.
        """
        super().__init__()
        self.config_path = config_path
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self._config: dict = {}
        self.load()

    def load(self) -> dict:
        """Load configuration from file.

        Returns:
            The loaded configuration dictionary.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = self.yaml.load(f) or {}
        else:
            self._config = {}
        return self._config

    def save(self) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            self.yaml.dump(self._config, f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key path.

        Args:
            key_path: Dot-separated path (e.g., 'simulator.host')
            default: Default value if key not found

        Returns:
            The configuration value or default.
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set a configuration value by dot-separated key path.

        Args:
            key_path: Dot-separated path (e.g., 'simulator.host')
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.config_changed.emit(key_path, value)

    def get_section(self, section: str) -> dict:
        """Get an entire configuration section.

        Args:
            section: Section name (top-level key)

        Returns:
            The section dictionary or empty dict.
        """
        return self._config.get(section, {})

    def set_section(self, section: str, data: dict) -> None:
        """Set an entire configuration section.

        Args:
            section: Section name (top-level key)
            data: Dictionary of values for the section
        """
        self._config[section] = data
        self.config_changed.emit(section, data)

    @property
    def config(self) -> dict:
        """Get the full configuration dictionary."""
        return self._config

    def validate(self) -> list[str]:
        """Validate the configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Validate required paths
        ae_path = self.get("autoencoder.model_path", "")
        if ae_path and not os.path.isfile(ae_path):
            errors.append(f"Autoencoder model not found: {ae_path}")

        hyperparams_path = self.get("training.hyperparams_file", "")
        if hyperparams_path and not os.path.isfile(hyperparams_path):
            errors.append(f"Hyperparams file not found: {hyperparams_path}")

        # Validate port range
        port = self.get("simulator.port", 9091)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append(f"Invalid port number: {port}")

        # Validate steering limits
        steer_left = self.get("environment.steer_left", -0.6)
        steer_right = self.get("environment.steer_right", 0.6)
        if steer_left >= steer_right:
            errors.append("steer_left must be less than steer_right")

        return errors
