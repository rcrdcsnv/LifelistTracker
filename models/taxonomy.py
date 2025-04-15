# models/taxonomy.py
"""
Taxonomy model - Represents a taxonomy reference
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class TaxonomyEntry:
    """Model representing a taxonomy entry"""

    def __init__(self, id: Optional[int] = None, taxonomy_id: Optional[int] = None,
                 scientific_name: str = "", common_name: Optional[str] = None,
                 family: Optional[str] = None, genus: Optional[str] = None,
                 species: Optional[str] = None, subspecies: Optional[str] = None,
                 order_name: Optional[str] = None, class_name: Optional[str] = None,
                 code: Optional[str] = None, rank: Optional[str] = None,
                 is_custom: bool = False, additional_data: Optional[Dict[str, Any]] = None):
        self.id = id
        self.taxonomy_id = taxonomy_id
        self.scientific_name = scientific_name
        self.common_name = common_name
        self.family = family
        self.genus = genus
        self.species = species
        self.subspecies = subspecies
        self.order_name = order_name
        self.class_name = class_name
        self.code = code
        self.rank = rank
        self.is_custom = is_custom
        self.additional_data = additional_data or {}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaxonomyEntry':
        """Create a TaxonomyEntry from a dictionary"""
        additional_data = data.get('additional_data')
        if isinstance(additional_data, str):
            import json
            try:
                additional_data = json.loads(additional_data)
            except:
                additional_data = {}

        return TaxonomyEntry(
            id=data.get('id'),
            taxonomy_id=data.get('taxonomy_id'),
            scientific_name=data.get('scientific_name', ''),
            common_name=data.get('common_name'),
            family=data.get('family'),
            genus=data.get('genus'),
            species=data.get('species'),
            subspecies=data.get('subspecies'),
            order_name=data.get('order_name'),
            class_name=data.get('class_name'),
            code=data.get('code'),
            rank=data.get('rank'),
            is_custom=bool(data.get('is_custom', False)),
            additional_data=additional_data
        )


class Taxonomy:
    """Model representing a taxonomy"""

    def __init__(self, id: Optional[int] = None, lifelist_id: Optional[int] = None,
                 name: str = "", version: Optional[str] = None, source: Optional[str] = None,
                 description: Optional[str] = None, is_active: bool = True,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.lifelist_id = lifelist_id
        self.name = name
        self.version = version
        self.source = source
        self.description = description
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.entries: List[TaxonomyEntry] = []

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Taxonomy':
        """Create a Taxonomy from a dictionary"""
        return Taxonomy(
            id=data.get('id'),
            lifelist_id=data.get('lifelist_id'),
            name=data.get('name', ''),
            version=data.get('version'),
            source=data.get('source'),
            description=data.get('description'),
            is_active=bool(data.get('is_active', True)),
            created_at=data.get('created_at')
        )