"""
Map Generator - Creates maps of observations with location data
"""
import folium
import os
from models.photo_utils import PhotoUtils


class MapGenerator:
    """
    Utility class to generate interactive maps of observations
    """

    @staticmethod
    def create_observation_map(observations, db, output_path="observation_map.html"):
        """
        Create a map showing all observation locations

        Args:
            observations (list): List of observation tuples from database
            db (Database): Database instance
            output_path (str): Path to save the HTML map file

        Returns:
            tuple: (map_path, message) if successful, (None, error_message) if failed
        """
        # Create a map centered on the first observation with coordinates
        map_center = [0, 0]
        has_coords = False
        valid_markers = 0

        # First find any coordinates to center the map
        for obs in observations:
            obs_id = obs[0]
            obs_details = db.get_observation_details(obs_id)[0]

            # Check observation coordinates
            if obs_details and obs_details[5] is not None and obs_details[6] is not None:
                map_center = [obs_details[5], obs_details[6]]
                has_coords = True
                break

            # Check photo coordinates
            photos = db.get_photos(obs_id)
            for photo in photos:
                if photo[3] is not None and photo[4] is not None:  # lat and lon
                    map_center = [photo[3], photo[4]]
                    has_coords = True
                    break

            if has_coords:
                break

        # If no coordinates found, return error
        if not has_coords:
            return None, "No coordinates available in any observations or photos"

        # Create map
        m = folium.Map(location=map_center, zoom_start=5)

        # Track which photos we've already created markers for to avoid duplicates
        processed_locations = set()

        for obs in observations:
            obs_id, species_name, obs_date, location, tier = obs

            # Get observation details
            obs_details = db.get_observation_details(obs_id)[0]

            # Add marker for observation coordinates if available
            if obs_details and obs_details[5] is not None and obs_details[6] is not None:
                lat, lon = obs_details[5], obs_details[6]
                location_key = f"{lat:.6f},{lon:.6f}"

                # Only add if we haven't added this exact location before
                if location_key not in processed_locations:
                    processed_locations.add(location_key)

                    # Try to get primary photo for this species
                    species_primary = db.get_species_primary_photo(obs_details[1], species_name)
                    img_base64 = None
                    img_format = "jpeg"

                    if species_primary:
                        img_base64, img_format = PhotoUtils.image_to_base64(species_primary[1], max_size=(60, 60),
                                                                            is_pin=True)

                    # Create popup content with larger image
                    if species_primary:
                        popup_img_base64, _ = PhotoUtils.image_to_base64(species_primary[1], max_size=(200, 150))
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
                        ).add_to(m)
                    else:
                        # Fallback to regular marker if no image
                        folium.Marker(
                            [lat, lon],
                            popup=folium.Popup(popup_content, max_width=300),
                            tooltip=species_name
                        ).add_to(m)

                    valid_markers += 1

            # Add markers for all photos with coordinates
            photos = db.get_photos(obs_id)
            for photo in photos:
                if photo[3] is not None and photo[4] is not None:  # lat and lon
                    lat, lon = photo[3], photo[4]
                    location_key = f"{lat:.6f},{lon:.6f}"

                    # Only add if we haven't added this exact location before
                    if location_key not in processed_locations:
                        processed_locations.add(location_key)

                        # Get thumbnail for icon with improved quality
                        img_base64, img_format = PhotoUtils.image_to_base64(photo[1], max_size=(100, 100), is_pin=True)

                        # Get larger image for popup
                        popup_img_base64, popup_format = PhotoUtils.image_to_base64(photo[1], max_size=(300, 200))

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
                            Photo: {os.path.basename(photo[1])}
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
                            ).add_to(m)
                        else:
                            # Fallback to regular marker if no image
                            folium.Marker(
                                [lat, lon],
                                popup=folium.Popup(popup_content, max_width=300),
                                tooltip=species_name
                            ).add_to(m)

                        valid_markers += 1

        # Save the map
        m.save(output_path)
        return output_path, f"{valid_markers} location(s) plotted on map"