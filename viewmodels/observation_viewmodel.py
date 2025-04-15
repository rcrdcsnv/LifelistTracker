# viewmodels/observation_viewmodel.py
"""
Observation ViewModel - Provides data and commands for the Observation View
"""
from typing import Optional, Callable, List, Dict, Any
from LifelistTracker.models.observation import Observation
from LifelistTracker.services.observation_service import IObservationService
from LifelistTracker.services.photo_service import IPhotoService
from LifelistTracker.utils.photo_utils import PhotoUtils


class ObservationViewModel:
    """ViewModel for the Observation View"""

    def __init__(self, observation_service: IObservationService, photo_service: IPhotoService):
        self.observation_service = observation_service
        self.photo_service = photo_service
        self.current_observation: Optional[Observation] = None
        self.photo_thumbnails = []
        self.photo_images = []
        self.on_state_changed: List[Callable] = []

    def load_observation(self, observation_id: int) -> bool:
        """
        Load an observation by ID

        Args:
            observation_id: ID of the observation to load

        Returns:
            True if loading succeeded, False otherwise
        """
        observation = self.observation_service.get_observation(observation_id)
        if not observation:
            return False

        self.current_observation = observation

        # Load photo thumbnails
        self._load_photo_thumbnails()

        # Notify state change
        self._notify_state_changed()

        return True

    def _load_photo_thumbnails(self) -> None:
        """Load thumbnails for observation photos"""
        if not self.current_observation:
            return

        self.photo_thumbnails = []
        self.photo_images = []

        for photo in self.current_observation.photos:
            # Use PhotoUtils to create thumbnails
            thumbnail = PhotoUtils.resize_image_for_thumbnail(photo.file_path)
            photo_img = PhotoUtils.resize_image_for_thumbnail(photo.file_path, (600, 400))

            if thumbnail:
                self.photo_thumbnails.append((photo, thumbnail))

            if photo_img:
                self.photo_images.append((photo, photo_img))

    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Get formatted custom field values

        Returns:
            List of formatted custom field dictionaries
        """
        if not self.current_observation:
            return []

        formatted_fields = []
        for field in self.current_observation.custom_field_values:
            formatted_value = field.get('value', '')

            # Format the value based on field type
            if field.get('field_type') == 'boolean':
                formatted_value = "Yes" if formatted_value == "1" else "No"

            formatted_fields.append({
                'field_name': field.get('field_name', ''),
                'field_type': field.get('field_type', ''),
                'value': formatted_value
            })

        return formatted_fields

    def register_state_change_callback(self, callback: Callable) -> None:
        """
        Register a callback for state changes

        Args:
            callback: Function to call on state change
        """
        if callback not in self.on_state_changed:
            self.on_state_changed.append(callback)

    def unregister_state_change_callback(self, callback: Callable) -> None:
        """
        Unregister a previously registered callback

        Args:
            callback: Function to remove from callback list
        """
        if callback in self.on_state_changed:
            self.on_state_changed.remove(callback)

    def _notify_state_changed(self) -> None:
        """Notify all registered callbacks of a state change"""
        for callback in self.on_state_changed:
            callback()