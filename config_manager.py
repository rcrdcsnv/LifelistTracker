"""
ConfigManager - Manages application configuration
"""
import os
from typing import Dict, Any, Optional, List

from file_utils import FileUtils


class ConfigManager:
    """
    Manager class for application configuration
    """
    _instance = None
    _default_config_file = "config.json"
    _config_data = None

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self._default_config_file)

        # Load configuration or create default
        if os.path.exists(config_path):
            self._config_data = FileUtils.read_json(config_path)

        # If loading failed or file doesn't exist, use defaults
        if self._config_data is None:
            self._config_data = self._get_default_config()
            self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self._default_config_file)
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
            },
            "lifelist_types": {
                "templates": {
                    "Wildlife": {
                        "tiers": ["wild", "heard", "captive"],
                        "entry_term": "species",
                        "observation_term": "sighting",
                        "default_fields": [
                            {"name": "Scientific Name", "type": "text", "required": 0},
                            {"name": "Family", "type": "text", "required": 0},
                            {"name": "Weather", "type": "text", "required": 0}
                        ]
                    },
                    "Plants": {
                        "tiers": ["wild", "garden", "greenhouse"],
                        "entry_term": "species",
                        "observation_term": "sighting",
                        "default_fields": [
                            {"name": "Scientific Name", "type": "text", "required": 0},
                            {"name": "Family", "type": "text", "required": 0},
                            {"name": "Habitat", "type": "text", "required": 0},
                            {"name": "Flowering Season", "type": "text", "required": 0}
                        ]
                    },
                    "Books": {
                        "tiers": ["read", "currently reading", "want to read", "abandoned"],
                        "entry_term": "book",
                        "observation_term": "reading",
                        "default_fields": [
                            {"name": "Author", "type": "text", "required": 1},
                            {"name": "Publisher", "type": "text", "required": 0},
                            {"name": "Year", "type": "number", "required": 0},
                            {"name": "Genre", "type": "text", "required": 0},
                            {"name": "Rating", "type": "rating", "options": {"max": 5}, "required": 0}
                        ]
                    },
                    "Travel": {
                        "tiers": ["visited", "stayed overnight", "want to visit"],
                        "entry_term": "place",
                        "observation_term": "visit",
                        "default_fields": [
                            {"name": "Country", "type": "text", "required": 0},
                            {"name": "City", "type": "text", "required": 0},
                            {"name": "Duration", "type": "text", "required": 0},
                            {"name": "Rating", "type": "rating", "options": {"max": 5}, "required": 0}
                        ]
                    },
                    "Foods": {
                        "tiers": ["tried", "cooked", "want to try"],
                        "entry_term": "dish",
                        "observation_term": "tasting",
                        "default_fields": [
                            {"name": "Cuisine", "type": "text", "required": 0},
                            {"name": "Ingredients", "type": "text", "required": 0},
                            {"name": "Restaurant", "type": "text", "required": 0},
                            {"name": "Rating", "type": "rating", "options": {"max": 5}, "required": 0}
                        ]
                    }
                }
            }
        }

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """
        Get the singleton instance of the ConfigManager

        Returns:
            ConfigManager: Singleton instance
        """
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def get_config(self, section: Optional[str] = None, key: Optional[str] = None) -> Any:
        """
        Get configuration value

        Args:
            section: Optional configuration section
            key: Optional key within section

        Returns:
            Any: Configuration value, section dict, or entire config
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
            str: Database path
        """
        return self.get_config("database", "path") or "lifelists.db"

    def get_window_size(self) -> Dict[str, int]:
        """
        Get window size from configuration

        Returns:
            dict: Window size as {"width": int, "height": int}
        """
        return self.get_config("ui", "window_size") or {"width": 1200, "height": 800}

    def get_theme(self) -> str:
        """
        Get UI theme from configuration

        Returns:
            str: UI theme
        """
        return self.get_config("ui", "theme") or "System"

    def get_color_theme(self) -> str:
        """
        Get UI color theme from configuration

        Returns:
            str: UI color theme
        """
        return self.get_config("ui", "color_theme") or "blue"
        
    def get_lifelist_type_template(self, type_name: str) -> Dict[str, Any]:
        """
        Get template configuration for a lifelist type

        Args:
            type_name: Name of the lifelist type

        Returns:
            dict: Template configuration
        """
        templates = self.get_config("lifelist_types", "templates")
        if templates and type_name in templates:
            return templates[type_name]
        return {
            "tiers": ["owned", "wanted"],
            "entry_term": "item",
            "observation_term": "entry",
            "default_fields": []
        }
        
    def get_entry_term(self, type_name: str) -> str:
        """
        Get the term used for entries in this lifelist type

        Args:
            type_name: Name of the lifelist type

        Returns:
            str: Term for entries (e.g., "species", "book", "movie")
        """
        template = self.get_lifelist_type_template(type_name)
        return template.get("entry_term", "item")
        
    def get_observation_term(self, type_name: str) -> str:
        """
        Get the term used for observations in this lifelist type

        Args:
            type_name: Name of the lifelist type

        Returns:
            str: Term for observations (e.g., "sighting", "reading", "viewing")
        """
        template = self.get_lifelist_type_template(type_name)
        return template.get("observation_term", "entry")
        
    def get_default_tiers(self, type_name: str) -> List[str]:
        """
        Get default tiers for a lifelist type

        Args:
            type_name: Name of the lifelist type

        Returns:
            list: Default tier names
        """
        template = self.get_lifelist_type_template(type_name)
        return template.get("tiers", ["owned", "wanted"])
        
    def get_default_fields(self, type_name: str) -> List[Dict[str, Any]]:
        """
        Get default custom fields for a lifelist type

        Args:
            type_name: Name of the lifelist type

        Returns:
            list: Default field definitions
        """
        template = self.get_lifelist_type_template(type_name)
        return template.get("default_fields", [])