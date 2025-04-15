# services/config_service.py
"""
Config Service - Manages application configuration
"""
import os
from typing import Dict, Any, Optional

from LifelistTracker.utils.file_utils import FileUtils


class IConfigService:
    """Interface for configuration service"""

    def get_config(self, section: Optional[str] = None, key: Optional[str] = None) -> Any:
        pass

    def set_config(self, section: str, key: str, value: Any) -> None:
        pass

    def get_database_path(self) -> str:
        pass

    def get_window_size(self) -> Dict[str, int]:
        pass

    def get_theme(self) -> str:
        pass

    def get_color_theme(self) -> str:
        pass


class ConfigService(IConfigService):
    """Service for managing application configuration"""

    def __init__(self):
        """
        Initialize the configuration service

        """
        self._default_config_file = "config.json"
        self._config_data = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", self._default_config_file)

        # Load configuration or create default
        if os.path.exists(config_path):
            self._config_data = FileUtils.read_json(config_path)

        # If loading failed or file doesn't exist, use defaults
        if self._config_data is None:
            self._config_data = self._get_default_config()
            self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", self._default_config_file)
        FileUtils.write_json(config_path, self._config_data)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "database": {
                "path": "lifelists.db"
            },
            "ui": {
                "theme": "System",
                "color_theme": "blue",
                "window_size": {
                    "width": 1200,
                    "height": 800
                }
            },
            "export": {
                "default_directory": "",
                "include_photos": True
            },
            "map": {
                "default_zoom": 5,
                "marker_size": {
                    "width": 100,
                    "height": 100
                }
            }
        }

    def get_config(self, section: Optional[str] = None, key: Optional[str] = None) -> Any:
        """
        Get configuration value

        Args:
            section: Optional configuration section
            key: Optional key within section

        Returns:
            Configuration value, section dict, or entire config
        """
        if section is None:
            return self._config_data

        if section not in self._config_data:
            return None

        if key is None:
            return self._config_data[section]

        if key not in self._config_data[section]:
            return None

        return self._config_data[section][key]

    def set_config(self, section: str, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            section: Configuration section
            key: Key within section
            value: Value to set
        """
        if section not in self._config_data:
            self._config_data[section] = {}

        self._config_data[section][key] = value
        self._save_config()

    def get_database_path(self) -> str:
        """
        Get database path from configuration

        Returns:
            Database path
        """
        return self.get_config("database", "path") or "lifelists.db"

    def get_window_size(self) -> Dict[str, int]:
        """
        Get window size from configuration

        Returns:
            Window size as {"width": int, "height": int}
        """
        return self.get_config("ui", "window_size") or {"width": 1200, "height": 800}

    def get_theme(self) -> str:
        """
        Get UI theme from configuration

        Returns:
            UI theme
        """
        return self.get_config("ui", "theme") or "System"

    def get_color_theme(self) -> str:
        """
        Get UI color theme from configuration

        Returns:
            UI color theme
        """
        return self.get_config("ui", "color_theme") or "blue"