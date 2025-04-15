# models/custom_field.py
"""
CustomField model - Represents a custom field for a lifelist
"""
from typing import Dict, Any, Optional


class CustomField:
    """Model representing a custom field"""

    def __init__(self, id: Optional[int] = None, lifelist_id: Optional[int] = None,
                 field_name: str = "", field_type: str = "text"):
        self.id = id
        self.lifelist_id = lifelist_id
        self.field_name = field_name
        self.field_type = field_type

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CustomField':
        """Create a CustomField from a dictionary"""
        return CustomField(
            id=data.get('id'),
            lifelist_id=data.get('lifelist_id'),
            field_name=data.get('field_name', ''),
            field_type=data.get('field_type', 'text')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the CustomField to a dictionary"""
        return {
            'id': self.id,
            'lifelist_id': self.lifelist_id,
            'field_name': self.field_name,
            'field_type': self.field_type
        }


class CustomFieldValue:
    """Model representing a value for a custom field"""

    def __init__(self, id: Optional[int] = None, observation_id: Optional[int] = None,
                 field_id: Optional[int] = None, value: str = ""):
        self.id = id
        self.observation_id = observation_id
        self.field_id = field_id
        self.value = value
        self.field_name = ""
        self.field_type = ""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CustomFieldValue':
        """Create a CustomFieldValue from a dictionary"""
        value = CustomFieldValue(
            id=data.get('id'),
            observation_id=data.get('observation_id'),
            field_id=data.get('field_id'),
            value=data.get('value', '')
        )

        value.field_name = data.get('field_name', '')
        value.field_type = data.get('field_type', '')

        return value