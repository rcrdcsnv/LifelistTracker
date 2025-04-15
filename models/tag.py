# models/tag.py
"""
Tag model - Represents a tag for categorizing observations
"""
from typing import Dict, Any, Optional


class Tag:
    """Model representing a tag"""

    def __init__(self, id: Optional[int] = None, name: str = ""):
        self.id = id
        self.name = name

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Tag':
        """
        Create a Tag from a dictionary

        Args:
            data: Dictionary with tag data

        Returns:
            A Tag instance
        """
        return Tag(
            id=data.get('id'),
            name=data.get('name', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Tag to a dictionary

        Returns:
            Dictionary representation of the Tag
        """
        return {
            'id': self.id,
            'name': self.name
        }