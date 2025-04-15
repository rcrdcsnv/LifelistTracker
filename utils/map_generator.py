# utils/map_generator.py
"""
Map Generator - Creates maps of observations with location data
"""
import folium
import os
from LifelistTracker.utils.photo_utils import PhotoUtils
from LifelistTracker.services.observation_service import IObservationService
from LifelistTracker.services.photo_service import IPhotoService
from typing import List, Tuple, Dict, Any, Optional, Set

class MapGenerator:
    """
    Utility class to generate interactive maps of observations
    """

    @staticmethod
    def create_observation_map(observations: List[Dict[str, Any]],
                              observation_service: IObservationService,
                              photo_service: IPhotoService,
                              output_path: str = "observation_map.html") -> Tuple[Optional[str], str]:
        """
        Create a map showing all observation locations

        Args:
            observations: List of observation dictionaries
            observation_service: Service for observation operations
            photo_service: Service for photo operations
            output_path: Path to save the HTML map file

        Returns:
            tuple: (map_path, message) if successful, (None, error_message) if failed
        """
        # Create a map centered on the first observation with coordinates
        map_center = [0, 0]
        has_coords = False
        processed_locations = set()

        # First find any coordinates to center the map
        for obs_dict in observations:
            obs_id = obs_dict['id']
            observation = observation_service.get_observation(obs_id)

            if not observation:
                continue

            # Check observation coordinates
            if observation.latitude is not None and observation.longitude is not None:
                map_center = [observation.latitude, observation.longitude]
                has_coords = True
                break

            # Check photo coordinates
            photos = photo_service.get_observation_photos(obs_id)
            for photo in photos:
                if photo.latitude is not None and photo.longitude is not None:
                    map_center = [photo.latitude, photo.longitude]
                    has_coords = True
                    break

            if has_coords:
                break

        # If no coordinates found, return error
        if not has_coords:
            return None, "No coordinates available in any observations or photos"

        # Create map
        m = folium.Map(location=map_center, zoom_start=5)

        # Add markers for all observations
        valid_markers = MapGenerator._add_observation_markers(
            m, observations, observation_service, photo_service, processed_locations)

        # Save the map using with context
        try:
            m.save(output_path)
            return output_path, f"{valid_markers} location(s) plotted on map"
        except Exception as e:
            print(f"Error saving map: {e}")
            return None, f"Error creating map: {str(e)}"

    @staticmethod
    def _add_observation_markers(map_obj: folium.Map,
                                observations: List[Dict[str, Any]],
                                observation_service: IObservationService,
                                photo_service: IPhotoService,
                                processed_locations: Set[str]) -> int:
        """
        Add observation markers to the map

        Args:
            map_obj: Folium map object
            observations: List of observations
            observation_service: Service for observation operations
            photo_service: Service for photo operations
            processed_locations: Set of already processed locations to avoid duplicates

        Returns:
            int: Number of valid markers added
        """
        valid_markers = 0

        for obs_dict in observations:
            obs_id = obs_dict['id']
            species_name = obs_dict['species_name']
            obs_date = obs_dict.get('observation_date')
            location = obs_dict.get('location')
            tier = obs_dict.get('tier')

            # Get observation details
            observation = observation_service.get_observation(obs_id)

            if not observation:
                continue

            # Add marker for observation coordinates if available
            if observation.latitude is not None and observation.longitude is not None:
                lat, lon = observation.latitude, observation.longitude
                location_key = f"{lat:.6f},{lon:.6f}"

                # Only add if we haven't added this exact location before
                if location_key not in processed_locations:
                    processed_locations.add(location_key)

                    # Add marker to map
                    if MapGenerator._add_marker_for_location(
                        map_obj, lat, lon, species_name, obs_date, location, tier,
                        photo_service, observation.lifelist_id, processed_locations
                    ):
                        valid_markers += 1

            # Add markers for all photos with coordinates
            photos = photo_service.get_observation_photos(obs_id)
            for photo in photos:
                if photo.latitude is not None and photo.longitude is not None:
                    lat, lon = photo.latitude, photo.longitude
                    location_key = f"{lat:.6f},{lon:.6f}"

                    # Only add if we haven't added this exact location before
                    if location_key not in processed_locations:
                        processed_locations.add(location_key)

                        # Create popup content with photo
                        if MapGenerator._add_photo_marker(
                            map_obj, lat, lon, species_name, obs_date, location, tier, photo
                        ):
                            valid_markers += 1

        return valid_markers

    @staticmethod
    def _add_marker_for_location(map_obj: folium.Map,
                                lat: float, lon: float,
                                species_name: str, obs_date: Any, location: Optional[str], tier: Optional[str],
                                photo_service: IPhotoService,
                                lifelist_id: int,
                                processed_locations: Set[str]) -> bool:
        """
        Add a marker for an observation location

        Args:
            map_obj: Folium map object
            lat, lon: Coordinates
            species_name, obs_date, location, tier: Observation details
            photo_service: Service for photo operations
            lifelist_id: ID of the lifelist
            processed_locations: Set of processed locations

        Returns:
            bool: True if marker was added, False otherwise
        """
        try:
            # Try to get primary photo for this species
            species_primary_photo = photo_service.get_primary_photo_for_species(lifelist_id, species_name)
            img_base64 = None
            img_format = "jpeg"

            if species_primary_photo and species_primary_photo.file_path:
                img_base64, img_format = PhotoUtils.image_to_base64(
                    species_primary_photo.file_path, max_size=(60, 60), is_pin=True)

            # Create popup content with larger image
            if species_primary_photo and species_primary_photo.file_path:
                popup_img_base64, _ = PhotoUtils.image_to_base64(
                    species_primary_photo.file_path, max_size=(200, 150))
                popup_content = f"""
                <strong>{species_name}</strong><br>
                <img src="data:image/jpeg;base64,{popup_img_base64}" style="max-width:200px;"><br>
                Date: {obs_date or 'Unknown'}<br>
                Location: {location or 'Unknown'}<br>
                Tier: {tier or 'Unknown'}<br>
                """
            else:
                popup_content = f"""
                <strong>{species_name}</strong><br>
                Date: {obs_date or 'Unknown'}<br>
                Location: {location or 'Unknown'}<br>
                Tier: {tier or 'Unknown'}
                """

            # Create a marker with the image if available
            if img_base64:
                # Create a custom div icon with the thumbnail image and a pin-like appearance
                icon_html = f"""
                <div style="position: relative; width: 100px; height: 110px;">
                    <div style="position: absolute; top: 0; width: 100px; height: 100px; border-radius: 50px; 
                        border: 3px solid #3388ff; overflow: hidden; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                        <img src="data:image/{img_format};base64,{img_base64}" 
                            style="width: 100%; height: 100%; image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;">
                    </div>
                    <div style="position: absolute; bottom: 0; left: 42px; width: 0; height: 0; 
                        border-left: 8px solid transparent; border-right: 8px solid transparent; 
                        border-top: 15px solid #3388ff;">
                    </div>
                </div>
                """

                # Create the custom icon
                icon = folium.DivIcon(
                    icon_size=(100, 110),
                    icon_anchor=(50, 110),  # Center bottom of the icon
                    html=icon_html
                )

                # Add marker with custom icon
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=species_name,
                    icon=icon
                ).add_to(map_obj)
            else:
                # Fallback to regular marker if no image
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=species_name
                ).add_to(map_obj)

            return True
        except Exception as e:
            print(f"Error adding marker: {e}")
            return False

    @staticmethod
    def _add_photo_marker(map_obj: folium.Map,
                         lat: float, lon: float,
                         species_name: str, obs_date: Any, location: Optional[str], tier: Optional[str],
                         photo) -> bool:
        """
        Add a marker for a photo with coordinates

        Args:
            map_obj: Folium map object
            lat, lon: Coordinates
            species_name, obs_date, location, tier: Observation details
            photo: Photo object

        Returns:
            bool: True if marker was added, False otherwise
        """
        try:
            # Get thumbnail for icon with improved quality
            img_base64, img_format = PhotoUtils.image_to_base64(photo.file_path, max_size=(100, 100), is_pin=True)

            # Get larger image for popup
            popup_img_base64, popup_format = PhotoUtils.image_to_base64(photo.file_path, max_size=(300, 200))

            # Create popup content
            if popup_img_base64:
                popup_content = f"""
                <strong>{species_name}</strong><br>
                <img src="data:image/jpeg;base64,{popup_img_base64}" style="max-width:200px;"><br>
                Date: {obs_date or 'Unknown'}<br>
                Location: {location or 'Unknown'}<br>
                Tier: {tier or 'Unknown'}<br>
                """
            else:
                # Fallback if image can't be encoded
                popup_content = f"""
                <strong>{species_name}</strong><br>
                Date: {obs_date or 'Unknown'}<br>
                Location: {location or 'Unknown'}<br>
                Tier: {tier or 'Unknown'}<br>
                Photo: {os.path.basename(photo.file_path)}
                """

            # Create a marker with the image if available
            if img_base64:
                # Create a custom div icon with the thumbnail image
                icon_html = f"""
                <div style="position: relative; width: 100px; height: 110px;">
                    <div style="position: absolute; top: 0; width: 100px; height: 100px; border-radius: 50px; 
                        border: 3px solid #3388ff; overflow: hidden; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                        <img src="data:image/{img_format};base64,{img_base64}" 
                            style="width: 100%; height: 100%; image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;">
                    </div>
                    <div style="position: absolute; bottom: 0; left: 42px; width: 0; height: 0; 
                        border-left: 8px solid transparent; border-right: 8px solid transparent; 
                        border-top: 15px solid #3388ff;">
                    </div>
                </div>
                """

                # Create the custom icon
                icon = folium.DivIcon(
                    icon_size=(100, 110),
                    icon_anchor=(50, 110),  # Center bottom of the icon
                    html=icon_html
                )

                # Add marker with custom icon
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=species_name,
                    icon=icon
                ).add_to(map_obj)
            else:
                # Fallback to regular marker if no image
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=species_name
                ).add_to(map_obj)

            return True
        except Exception as e:
            print(f"Error adding photo marker: {e}")
            return False