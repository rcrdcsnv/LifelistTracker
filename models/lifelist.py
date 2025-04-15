# models/lifelist.py
"""
Lifelist model - Represents a lifelist
"""
from typing import List, Optional, Dict, Any
from datetime import datetime


class Lifelist:
    """Model representing a lifelist"""

    def __init__(self, id: Optional[int] = None, name: str = "", taxonomy: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.name = name
        self.taxonomy = taxonomy
        self.created_at = created_at or datetime.now()
        self.tiers: List[str] = []
        self.custom_fields: List[Dict[str, Any]] = []

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Lifelist':
        """
        Create a Lifelist from a dictionary

        Args:
            data: Dictionary with lifelist data

        Returns:
            A Lifelist instance
        """
        lifelist = Lifelist(
            id=data.get('id'),
            name=data.get('name', ''),
            taxonomy=data.get('taxonomy'),
            created_at=data.get('created_at')
        )
        return lifelist

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Lifelist to a dictionary

        Returns:
            Dictionary representation of the Lifelist
        """
        return {
            'id': self.id,
            'name': self.name,
            'taxonomy': self.taxonomy,
            'created_at': self.created_at,
            'tiers': self.tiers,
            'custom_fields': self.custom_fields
        }