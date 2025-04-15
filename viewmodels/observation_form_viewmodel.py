# viewmodels/observation_form_viewmodel.py
"""
Observation Form ViewModel - Provides data and commands for the Observation Form
"""
from typing import List, Optional, Dict, Any, Callable
from LifelistTracker.models.observation import Observation
from LifelistTracker.models.photo import Photo
from LifelistTracker.models.tag import Tag
from LifelistTracker.services.observation_service import IObservationService
from LifelistTracker.services.lifelist_service import ILifelistService
from LifelistTracker.services.taxonomy_service import ITaxonomyService
from LifelistTracker.services.photo_service import IPhotoService
from LifelistTracker.utils.photo_utils import PhotoUtils


class ObservationFormViewModel:
    """ViewModel for the Observation Form"""

    def __init__(self, observation_service: IObservationService,
                 lifelist_service: ILifelistService,
                 taxonomy_service: ITaxonomyService,
                 photo_service: IPhotoService):
        self.observation_service = observation_service
        self.lifelist_service = lifelist_service
        self.taxonomy_service = taxonomy_service
        self.photo_service = photo_service

        self.observation: Optional[Observation] = None
        self.editing_mode = False
        self.lifelist_id = None
        self.species_name = ""
        self.tier_options: List[str] = []
        self.custom_fields: List[Dict[str, Any]] = []
        self.photos: List[Dict[str, Any]] = []
        self.tags: List[str] = []
        self.suggestions: List[Dict[str, str]] = []
        self.showing_suggestions = False

        self.on_state_changed: List[Callable] = []

    def initialize_form(self, lifelist_id: int, observation_id: Optional[int] = None,
                        species_name: Optional[str] = None) -> bool:
        """
        Initialize the form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation to edit (None for new)
            species_name: Optional species name to pre-fill

        Returns:
            True if initialization succeeded, False otherwise
        """
        self.lifelist_id = lifelist_id
        self.editing_mode = observation_id is not None

        # Load tier options
        self.tier_options = self.lifelist_service.get_lifelist_tiers(lifelist_id)

        # Load custom fields
        lifelist = self.lifelist_service.get_lifelist(lifelist_id)
        if lifelist:
            self.custom_fields = lifelist.custom_fields

        # Reset state
        self.photos = []
        self.tags = []

        if observation_id:
            # Load existing observation
            observation = self.observation_service.get_observation(observation_id)
            if not observation:
                return False

            self.observation = observation
            self.species_name = observation.species_name

            # Convert photos to the format expected by the UI
            for photo in observation.photos:
                thumbnail = PhotoUtils.resize_image_for_thumbnail(photo.file_path)

                photo_data = {
                    "id": photo.id,
                    "path": photo.file_path,
                    "is_primary": photo.is_primary,
                    "thumbnail": thumbnail,
                    "latitude": photo.latitude,
                    "longitude": photo.longitude,
                    "taken_date": photo.taken_date
                }

                self.photos.append(photo_data)

            # Extract tag names
            self.tags = [tag.name for tag in observation.tags]

        elif species_name:
            # New observation with pre-filled species name
            self.species_name = species_name
            self.observation = Observation(lifelist_id=lifelist_id, species_name=species_name)
        else:
            # New blank observation
            self.species_name = ""
            self.observation = Observation(lifelist_id=lifelist_id)

        # Notify state change
        self._notify_state_changed()

        return True

    def update_species_suggestions(self, text: str) -> None:
        """
        Update species name suggestions based on input

        Args:
            text: Current text in the species field
        """
        self.suggestions = []
        self.showing_suggestions = False

        if not text or len(text) < 2:
            self._notify_state_changed()
            return

        # Get active taxonomy
        active_taxonomy = self.taxonomy_service.get_active_taxonomy(self.lifelist_id)
        if not active_taxonomy:
            self._notify_state_changed()
            return

        # Search the taxonomy
        results = self.taxonomy_service.search_taxonomy(active_taxonomy.id, text)

        if results:
            for entry in results:
                display_name = entry.scientific_name
                if entry.common_name:
                    display_name = f"{entry.common_name} ({entry.scientific_name})"

                self.suggestions.append({
                    "scientific_name": entry.scientific_name,
                    "common_name": entry.common_name,
                    "display_name": display_name
                })

            self.showing_suggestions = True

        self._notify_state_changed()

    def select_suggestion(self, index: int) -> None:
        """
        Select a suggestion from the suggestion list

        Args:
            index: Index of the suggestion to select
        """
        if not self.showing_suggestions or index >= len(self.suggestions):
            return

        suggestion = self.suggestions[index]

        if suggestion["common_name"]:
            self.species_name = suggestion["common_name"]
        else:
            self.species_name = suggestion["scientific_name"]

        self.showing_suggestions = False
        self._notify_state_changed()

    def add_tag(self, tag_name: str) -> None:
        """
        Add a tag to the current tags list

        Args:
            tag_name: Name of the tag to add
        """
        if tag_name and tag_name not in self.tags:
            self.tags.append(tag_name)
            self._notify_state_changed()

    def remove_tag(self, tag_name: str) -> None:
        """
        Remove a tag from the current tags list

        Args:
            tag_name: Name of the tag to remove
        """
        if tag_name in self.tags:
            self.tags.remove(tag_name)
            self._notify_state_changed()

    def add_photos(self, file_paths: List[str]) -> None:
        """
        Add photos to the observation

        Args:
            file_paths: List of photo file paths to add
        """
        has_primary = any(p.get("is_primary", False) for p in self.photos)

        # Also check if this species already has a primary photo
        if self.lifelist_id and self.species_name and not has_primary:
            has_primary = self.photo_service.species_has_primary_photo(self.lifelist_id, self.species_name)

        for path in file_paths:
            # Ensure the path is not already in the list
            if any(p["path"] == path for p in self.photos):
                continue

            # Extract EXIF data if available
            lat, lon, taken_date = PhotoUtils.extract_exif_data(path)

            # Create thumbnail
            thumbnail = PhotoUtils.resize_image_for_thumbnail(path)

            # Add to photos list - only set as primary if there's no existing primary
            # for this species and no primary in the current list
            self.photos.append({
                "path": path,
                "is_primary": not has_primary and len(self.photos) == 0,
                "thumbnail": thumbnail,
                "latitude": lat,
                "longitude": lon,
                "taken_date": taken_date
            })

            # Only the first photo can be primary if none existed before
            has_primary = True

        self._notify_state_changed()

    def set_primary_photo(self, index: int) -> None:
        """
        Set a photo as the primary photo

        Args:
            index: Index of the photo in the photos list
        """
        for i in range(len(self.photos)):
            self.photos[i]["is_primary"] = (i == index)

        self._notify_state_changed()

    def remove_photo(self, index: int) -> None:
        """
        Remove a photo from the photos list

        Args:
            index: Index of the photo to remove
        """
        self.photos.pop(index)

        # If we removed the primary photo, set a new one
        if not any(p["is_primary"] for p in self.photos) and self.photos:
            self.photos[0]["is_primary"] = True

        self._notify_state_changed()

    def save_observation(self, observation_data: Dict[str, Any],
                         custom_field_values: Dict[int, str]) -> bool:
        """
        Save the observation

        Args:
            observation_data: Basic observation data
            custom_field_values: Custom field values by field ID

        Returns:
            True if saving succeeded, False otherwise
        """
        # Create or update the observation object
        if not self.observation:
            self.observation = Observation(lifelist_id=self.lifelist_id)

        # Update observation with form data
        self.observation.species_name = observation_data.get("species_name", "")
        self.observation.observation_date = observation_data.get("observation_date")
        self.observation.location = observation_data.get("location")
        self.observation.latitude = observation_data.get("latitude")
        self.observation.longitude = observation_data.get("longitude")
        self.observation.tier = observation_data.get("tier", "wild")
        self.observation.notes = observation_data.get("notes")

        # Update custom field values
        self.observation.custom_field_values = []
        for field_id, value in custom_field_values.items():
            # Find the field type
            field_type = ""
            for field in self.custom_fields:
                if field["id"] == field_id:
                    field_type = field["field_type"]
                    break

            self.observation.custom_field_values.append({
                "field_id": field_id,
                "value": value,
                "field_name": field["field_name"],
                "field_type": field_type
            })

        # Update tags
        self.observation.tags = [Tag(name=tag_name) for tag_name in self.tags]

        # Update photos
        self.observation.photos = []
        for photo_data in self.photos:
            photo = Photo(
                id=photo_data.get("id"),
                observation_id=self.observation.id,
                file_path=photo_data.get("path", ""),
                is_primary=photo_data.get("is_primary", False),
                latitude=photo_data.get("latitude"),
                longitude=photo_data.get("longitude"),
                taken_date=photo_data.get("taken_date")
            )
            self.observation.photos.append(photo)

        # Save to database
        if self.editing_mode:
            success = self.observation_service.update_observation(self.observation)
        else:
            observation_id = self.observation_service.add_observation(self.observation)
            success = observation_id is not None
            if success:
                self.observation.id = observation_id

        return success

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