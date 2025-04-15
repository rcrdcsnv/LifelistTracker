# models/photo.py
"""
Photo model - Represents a photo associated with an observation
"""
from typing import Dict, Any, Optional
from datetime import datetime


class Photo:
    """Model representing a photo"""

    def __init__(self, id: Optional[int] = None, observation_id: Optional[int] = None,
                 file_path: str = "", is_primary: bool = False, latitude: Optional[float] = None,
                 longitude: Optional[float] = None, taken_date: Optional[datetime] = None):
        self.id = id
        self.observation_id = observation_id
        self.file_path = file_path
        self.is_primary = is_primary
        self.latitude = latitude
        self.longitude = longitude
        self.taken_date = taken_date
        self.thumbnail = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Photo':
        """
        Create a Photo from a dictionary

        Args:
            data: Dictionary with photo data

        Returns:
            A Photo instance
        """
        return Photo(
            id=data.get('id'),
            observation_id=data.get('observation_id'),
            file_path=data.get('file_path', ''),
            is_primary=bool(data.get('is_primary', False)),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            taken_date=data.get('taken_date')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Photo to a dictionary

        Returns:
            Dictionary representation of the Photo
        """
        return {
            'id': self.id,
            'observation_id': self.observation_id,
            'file_path': self.file_path,
            'is_primary': self.is_primary,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'taken_date': self.taken_date
        }