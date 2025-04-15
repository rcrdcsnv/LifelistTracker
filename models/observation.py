# models/observation.py
"""
Observation model - Represents an observation of a species
"""
from typing import Dict, Any, Optional
from datetime import datetime


class Observation:
    """Model representing an observation"""

    def __init__(self, id: Optional[int] = None, lifelist_id: Optional[int] = None,
                 species_name: str = "", observation_date: Optional[datetime] = None,
                 location: Optional[str] = None, latitude: Optional[float] = None,
                 longitude: Optional[float] = None, tier: str = "wild",
                 notes: Optional[str] = None, created_at: Optional[datetime] = None):
        self.id = id
        self.lifelist_id = lifelist_id
        self.species_name = species_name
        self.observation_date = observation_date
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.tier = tier
        self.notes = notes
        self.created_at = created_at or datetime.now()
        self.custom_field_values = []
        self.tags = []
        self.photos = []

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Observation':
        """
        Create an Observation from a dictionary

        Args:
            data: Dictionary with observation data

        Returns:
            An Observation instance
        """
        return Observation(
            id=data.get('id'),
            lifelist_id=data.get('lifelist_id'),
            species_name=data.get('species_name', ''),
            observation_date=data.get('observation_date'),
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            tier=data.get('tier', 'wild'),
            notes=data.get('notes'),
            created_at=data.get('created_at')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Observation to a dictionary

        Returns:
            Dictionary representation of the Observation
        """
        return {
            'id': self.id,
            'lifelist_id': self.lifelist_id,
            'species_name': self.species_name,
            'observation_date': self.observation_date,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'tier': self.tier,
            'notes': self.notes,
            'created_at': self.created_at,
            'custom_field_values': self.custom_field_values,
            'tags': self.tags,
            'photos': self.photos
        }