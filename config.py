# config.py
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel

class WindowSize(BaseModel):
    width: int = 1200
    height: int = 800

class MarkerSize(BaseModel):
    width: int = 100
    height: int = 100

class DatabaseConfig(BaseModel):
    path: str = "lifelists.db"

class UIConfig(BaseModel):
    theme: str = "System"
    color_theme: str = "blue"
    window_size: WindowSize = WindowSize()

class ExportConfig(BaseModel):
    default_directory: str = ""
    include_photos: bool = True

class MapConfig(BaseModel):
    default_zoom: int = 5
    marker_size: MarkerSize = MarkerSize()

class CustomField(BaseModel):
    name: str
    type: str
    required: int = 0
    options: Optional[Dict[str, Any]] = None

class LifelistTypeTemplate(BaseModel):
    tiers: List[str]
    entry_term: str
    observation_term: str
    default_fields: List[CustomField] = []

class LifelistTypesConfig(BaseModel):
    templates: Dict[str, LifelistTypeTemplate] = {
        "Wildlife": LifelistTypeTemplate(
            tiers=["wild", "heard", "captive"],
            entry_term="species",
            observation_term="sighting",
            default_fields=[
                CustomField(name="Scientific Name", type="text"),
                CustomField(name="Family", type="text"),
                CustomField(name="Weather", type="text")
            ]
        ),
        "Plants": LifelistTypeTemplate(
            tiers=["wild", "garden", "greenhouse"],
            entry_term="species",
            observation_term="sighting",
            default_fields=[
                CustomField(name="Scientific Name", type="text"),
                CustomField(name="Family", type="text"),
                CustomField(name="Habitat", type="text"),
                CustomField(name="Flowering Season", type="text")
            ]
        ),
        "Books": LifelistTypeTemplate(
            tiers=["read", "currently reading", "want to read", "abandoned"],
            entry_term="book",
            observation_term="reading",
            default_fields=[
                CustomField(name="Author", type="text", required=1),
                CustomField(name="Publisher", type="text"),
                CustomField(name="Year", type="number"),
                CustomField(name="Genre", type="text"),
                CustomField(name="Rating", type="rating", options={"max": 5})
            ]
        ),
        "Travel": LifelistTypeTemplate(
            tiers=["visited", "stayed overnight", "want to visit"],
            entry_term="place",
            observation_term="visit",
            default_fields=[
                CustomField(name="Country", type="text"),
                CustomField(name="City", type="text"),
                CustomField(name="Duration", type="text"),
                CustomField(name="Rating", type="rating", options={"max": 5})
            ]
        ),
        "Foods": LifelistTypeTemplate(
            tiers=["tried", "cooked", "want to try"],
            entry_term="dish",
            observation_term="tasting",
            default_fields=[
                CustomField(name="Cuisine", type="text"),
                CustomField(name="Ingredients", type="text"),
                CustomField(name="Restaurant", type="text"),
                CustomField(name="Rating", type="rating", options={"max": 5})
            ]
        )
    }

class Config(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    ui: UIConfig = UIConfig()
    export: ExportConfig = ExportConfig()
    map: MapConfig = MapConfig()
    lifelist_types: LifelistTypesConfig = LifelistTypesConfig()
    
    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> 'Config':
        config_path = Path(config_path or Path(__file__).parent / "config.json")
        if config_path.exists():
            try:
                return cls.model_validate_json(config_path.read_text())
            except Exception as e:
                print(f"Error loading config: {e}")
        return cls()
    
    def save(self, config_path: Optional[Union[str, Path]] = None) -> None:
        config_path = Path(config_path or Path(__file__).parent / "config.json")
        config_path.write_text(self.model_dump_json(indent=2))
    
    def get_entry_term(self, type_name: str) -> str:
        template = self.lifelist_types.templates.get(type_name)
        return template.entry_term if template else "item"
    
    def get_observation_term(self, type_name: str) -> str:
        template = self.lifelist_types.templates.get(type_name)
        return template.observation_term if template else "entry"
    
    def get_default_tiers(self, type_name: str) -> List[str]:
        template = self.lifelist_types.templates.get(type_name)
        return template.tiers if template else ["owned", "wanted"]
    
    def get_default_fields(self, type_name: str) -> List[CustomField]:
        template = self.lifelist_types.templates.get(type_name)
        return template.default_fields if template else []