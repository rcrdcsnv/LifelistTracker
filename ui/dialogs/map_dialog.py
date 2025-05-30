# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                               QComboBox, QDialogButtonBox, QFileDialog,
                               QMessageBox)
from typing import Dict, Any, List
import folium
from folium import plugins
import json
import base64
from pathlib import Path
from PIL import Image
import io
from .base_map_dialog import BaseMapDialog


class MapDialog(BaseMapDialog):
    """Dialog for showing observations on a map"""

    def __init__(self, parent, db_manager, lifelist_id, observation_term="observation"):
        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observation_term = observation_term

        # Get photo manager from parent (should be main window or lifelist view)
        self.photo_manager = None
        if hasattr(parent, 'photo_manager'):
            self.photo_manager = parent.photo_manager
        elif hasattr(parent, 'main_window') and hasattr(parent.main_window, 'photo_manager'):
            self.photo_manager = parent.main_window.photo_manager

        # UI Controls
        self.tier_combo = None
        self.entry_combo = None
        self.apply_btn = None
        self.save_btn = None

        # Map data
        self.observations = []
        self.marker_cluster = None

        super().__init__(parent, f"{observation_term.capitalize()} Map")

    def add_controls(self):
        """Add map dialog specific controls"""
        controls_layout = QHBoxLayout()

        # Filter by tier
        tier_layout = QHBoxLayout()
        tier_layout.addWidget(QLabel("Tier:"))

        self.tier_combo = QComboBox()
        self.tier_combo.addItem("All")
        tier_layout.addWidget(self.tier_combo)

        controls_layout.addLayout(tier_layout)

        # Filter by entry
        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel("Entry:"))

        self.entry_combo = QComboBox()
        self.entry_combo.addItem("All")
        entry_layout.addWidget(self.entry_combo)

        controls_layout.addLayout(entry_layout)

        # Map controls
        controls_layout.addStretch()

        # Apply button
        self.apply_btn = QPushButton("Apply Filters")
        self.apply_btn.clicked.connect(self._load_observations)
        controls_layout.addWidget(self.apply_btn)

        # Save map button
        self.save_btn = QPushButton("Save Map")
        self.save_btn.clicked.connect(self._save_map)
        controls_layout.addWidget(self.save_btn)

        self.layout().addLayout(controls_layout)

    def add_bottom_controls(self):
        """Add dialog buttons at the bottom"""
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

        # Load initial data
        self._load_tiers()
        self._load_entries()
        self._load_observations()

    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for observation map"""
        # Calculate center from observations
        if self.observations:
            valid_coords = [(obs['latitude'], obs['longitude']) for obs in self.observations
                            if obs['latitude'] is not None and obs['longitude'] is not None]

            if valid_coords:
                lat_sum = sum(lat for lat, _ in valid_coords)
                lon_sum = sum(lon for _, lon in valid_coords)
                count = len(valid_coords)

                center_lat = lat_sum / count
                center_lon = lon_sum / count

                # Calculate appropriate zoom level based on spread of observations
                if count > 1:
                    # Calculate bounds
                    min_lat = min(lat for lat, _ in valid_coords)
                    max_lat = max(lat for lat, _ in valid_coords)
                    min_lon = min(lon for _, lon in valid_coords)
                    max_lon = max(lon for _, lon in valid_coords)

                    # Estimate zoom based on coordinate range
                    lat_range = max_lat - min_lat
                    lon_range = max_lon - min_lon
                    max_range = max(lat_range, lon_range)

                    if max_range > 100:
                        zoom = 3
                    elif max_range > 50:
                        zoom = 4
                    elif max_range > 20:
                        zoom = 5
                    elif max_range > 10:
                        zoom = 6
                    elif max_range > 5:
                        zoom = 7
                    elif max_range > 2:
                        zoom = 8
                    elif max_range > 1:
                        zoom = 9
                    elif max_range > 0.5:
                        zoom = 10
                    else:
                        zoom = 11
                else:
                    # Single observation, zoom in more
                    zoom = 13
            else:
                # No valid coordinates, use default
                center_lat = 0.0
                center_lon = 0.0
                zoom = 5
        else:
            # No observations, use default
            center_lat = 0.0
            center_lon = 0.0
            zoom = 5

        return {
            'centerLat': center_lat,
            'centerLon': center_lon,
            'zoom': zoom
        }

    def customize_folium_map(self, m: folium.Map):
        """Customize the folium map for observations"""
        if not self.observations:
            # Add a message when no observations are found
            folium.Marker(
                location=[0, 0],
                popup=folium.Popup(f'No {self.observation_term}s with coordinates found for the selected filters.',
                                   max_width=300),
                icon=folium.Icon(color='gray', icon='info-sign')
            ).add_to(m)
            return

        # Add custom CSS for photo markers
        css = """
        <style>
        .photo-marker-container {
            background: none !important;
            border: none !important;
        }

        .photo-marker {
            width: 56px !important;
            height: 56px !important;
            position: relative;
            cursor: pointer;
            transform: translateZ(0);
            will-change: transform;
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .photo-marker:hover {
            transform: translateZ(0) scale(1.1);
            z-index: 1000 !important;
        }

        .photo-marker-inner {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            overflow: hidden;
            position: absolute;
            top: 0;
            left: 0;
            background-color: white;
            transition: box-shadow 0.2s;
        }

        .photo-marker:hover .photo-marker-inner {
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }

        .photo-marker img {
            width: 75px !important;
            height: 75px !important;
            object-fit: cover;
            display: block;
            position: absolute;
            top: -12.5px;
            left: -12.5px;
            transform: scale(0.667);
            transform-origin: center;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* Tier-specific border colors */
        .tier-wild .photo-marker-inner { border-color: #27ae60; }
        .tier-heard .photo-marker-inner { border-color: #3498db; }
        .tier-captive .photo-marker-inner { border-color: #e67e22; }
        .tier-visual .photo-marker-inner { border-color: #27ae60; }
        .tier-imaged .photo-marker-inner { border-color: #9b59b6; }
        .tier-sketched .photo-marker-inner { border-color: #3498db; }
        .tier-read .photo-marker-inner { border-color: #27ae60; }
        .tier-currently-reading .photo-marker-inner { border-color: #e67e22; }
        .tier-want-to-read .photo-marker-inner { border-color: #e74c3c; }
        .tier-visited .photo-marker-inner { border-color: #27ae60; }
        .tier-stayed-overnight .photo-marker-inner { border-color: #3498db; }
        .tier-want-to-visit .photo-marker-inner { border-color: #e74c3c; }
        .tier-tried .photo-marker-inner { border-color: #27ae60; }
        .tier-cooked .photo-marker-inner { border-color: #3498db; }
        .tier-want-to-try .photo-marker-inner { border-color: #e74c3c; }
        .tier-default .photo-marker-inner { border-color: #7f8c8d; }

        /* Ensure clusters are above photo markers */
        .marker-cluster {
            z-index: 500 !important;
        }
        </style>
        """
        m.get_root().html.add_child(folium.Element(css))

        # Create marker cluster for better performance with many markers
        if len(self.observations) > 5:
            self.marker_cluster = plugins.MarkerCluster(
                name="Observations",
                overlay=True,
                control=True,
                show=True,
                disableClusteringAtZoom=15  # Ensure photos show at reasonable zoom
            )
            self.marker_cluster.add_to(m)
        else:
            self.marker_cluster = m

        # Color mapping for tiers
        tier_colors = {
            'wild': 'green',
            'heard': 'blue',
            'captive': 'orange',
            'visual': 'green',
            'imaged': 'purple',
            'sketched': 'blue',
            'read': 'green',
            'currently reading': 'orange',
            'want to read': 'red',
            'visited': 'green',
            'stayed overnight': 'blue',
            'want to visit': 'red',
            'tried': 'green',
            'cooked': 'blue',
            'want to try': 'red'
        }

        # Add markers for each observation
        for obs in self.observations:
            if obs['latitude'] is not None and obs['longitude'] is not None:
                # Determine marker color based on tier
                tier = obs.get('tier', '').lower()
                color = tier_colors.get(tier, 'gray')
                tier_class = f"tier-{tier.replace(' ', '-')}" if tier else "tier-default"

                # Create popup content
                popup_content = f"""
                <div style="min-width: 200px;">
                    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">{obs['entry_name']}</h4>
                    <table style="width: 100%; font-size: 12px;">
                        <tr><td><strong>Date:</strong></td><td>{obs['observation_date'].strftime('%Y-%m-%d') if obs['observation_date'] else 'Unknown'}</td></tr>
                        <tr><td><strong>Location:</strong></td><td>{obs['location'] or 'Unknown'}</td></tr>
                        <tr><td><strong>Tier:</strong></td><td><span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{obs['tier'] or 'Unknown'}</span></td></tr>
                        <tr><td><strong>Coordinates:</strong></td><td>{obs['latitude']:.6f}, {obs['longitude']:.6f}</td></tr>
                    </table>
                    {f'<p style="margin: 10px 0 0 0; font-size: 11px; font-style: italic;">{obs["notes"][:100]}{"..." if len(obs.get("notes", "")) > 100 else ""}</p>' if obs.get('notes') else ''}
                </div>
                """

                # Create marker - use photo if available, otherwise use standard icon
                if obs.get('marker_thumbnail'):
                    # Create custom HTML icon with photo
                    icon_html = f"""
                    <div class="photo-marker {tier_class}">
                        <div class="photo-marker-inner">
                            <img src="{obs['marker_thumbnail']}" alt="{obs['entry_name']}">
                        </div>
                    </div>
                    """

                    marker = folium.Marker(
                        location=[obs['latitude'], obs['longitude']],
                        popup=folium.Popup(popup_content, max_width=300),
                        tooltip=f"{obs['entry_name']} ({obs['tier'] or 'Unknown'})",
                        icon=folium.DivIcon(
                            html=icon_html,
                            icon_size=(56, 56),  # Account for border
                            icon_anchor=(28, 28),  # Center the circular marker
                        )
                    )
                else:
                    # Use standard colored icon for observations without photos
                    marker = folium.Marker(
                        location=[obs['latitude'], obs['longitude']],
                        popup=folium.Popup(popup_content, max_width=300),
                        tooltip=f"{obs['entry_name']} ({obs['tier'] or 'Unknown'})",
                        icon=folium.Icon(
                            color=color,
                            icon='info-sign',
                            prefix='glyphicon'
                        )
                    )

                marker.add_to(self.marker_cluster)

        # Auto-fit map to markers if we have observations with coordinates
        valid_coords = [(obs['latitude'], obs['longitude']) for obs in self.observations
                        if obs['latitude'] is not None and obs['longitude'] is not None]

        if valid_coords:
            # Add JavaScript to fit bounds after map loads
            bounds_js = f"""
            var bounds = {json.dumps([[lat, lon] for lat, lon in valid_coords])};
            if (bounds.length > 0) {{
                var group = new L.featureGroup();
                bounds.forEach(function(coord) {{
                    group.addLayer(L.marker(coord));
                }});

                if (bounds.length === 1) {{
                    // For single observation, center on it with reasonable zoom
                    map.setView(bounds[0], 13);
                }} else {{
                    // For multiple observations, fit all in view
                    map.fitBounds(group.getBounds(), {{
                        padding: [20, 20],
                        maxZoom: 15
                    }});
                }}
            }}
            """

            # Add JavaScript for handling photo markers and cluster events
            photo_marker_js = """
            // Ensure photo markers display correctly when clusters expand
            map.on('layeradd', function(e) {
                if (e.layer instanceof L.Marker && !e.layer._icon) {
                    // Force icon creation for custom markers
                    setTimeout(function() {
                        if (e.layer.options.icon && e.layer.options.icon.options.html) {
                            e.layer.setIcon(e.layer.options.icon);
                        }
                    }, 10);
                }
            });

            // Add click handler for photo markers
            document.addEventListener('click', function(e) {
                if (e.target.closest('.photo-marker')) {
                    // Let the marker's popup handle the click
                    e.stopPropagation();
                }
            });
            """

            m.get_root().html.add_child(folium.Element(f"""
            <script>
            map.whenReady(function() {{
                setTimeout(function() {{
                    {bounds_js}
                    {photo_marker_js}
                }}, 100);
            }});
            </script>
            """))

        # Add a legend for tier colors
        self._add_tier_legend(m)

    def _add_tier_legend(self, m: folium.Map):
        """Add a legend showing tier colors"""
        # Get unique tiers from current observations
        tiers = list({obs.get('tier') for obs in self.observations if obs.get('tier')})

        if not tiers:
            return

        tier_colors = {
            'wild': 'green',
            'heard': 'blue',
            'captive': 'orange',
            'visual': 'green',
            'imaged': 'purple',
            'sketched': 'blue',
            'read': 'green',
            'currently reading': 'orange',
            'want to read': 'red',
            'visited': 'green',
            'stayed overnight': 'blue',
            'want to visit': 'red',
            'tried': 'green',
            'cooked': 'blue',
            'want to try': 'red'
        }

        # Create legend HTML
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px;">
        <h4 style="margin: 0 0 10px 0;">Tier Legend</h4>
        """

        for tier in sorted(tiers):
            color = tier_colors.get(tier.lower(), 'gray')
            legend_html += f"""
            <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:{color}"></i> {tier}</p>
            """

        legend_html += "</div>"

        m.get_root().html.add_child(folium.Element(legend_html))

    def _load_tiers(self):
        """Load tiers for the lifelist"""
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository

            tiers = LifelistRepository.get_lifelist_tiers(session, self.lifelist_id)

            # Update combo box
            current_text = self.tier_combo.currentText()
            self.tier_combo.clear()
            self.tier_combo.addItem("All")

            for tier in tiers:
                self.tier_combo.addItem(tier)

            # Restore selection if possible
            index = self.tier_combo.findText(current_text)
            if index >= 0:
                self.tier_combo.setCurrentIndex(index)

    def _load_entries(self):
        """Load unique entries for the lifelist"""
        with self.db_manager.session_scope() as session:
            from db.repositories import ObservationRepository

            entries = ObservationRepository.get_unique_entries(session, self.lifelist_id)

            # Update combo box
            current_text = self.entry_combo.currentText()
            self.entry_combo.clear()
            self.entry_combo.addItem("All")

            for entry in entries:
                self.entry_combo.addItem(entry)

            # Restore selection if possible
            index = self.entry_combo.findText(current_text)
            if index >= 0:
                self.entry_combo.setCurrentIndex(index)

    def _load_observations(self):
        """Load observations with coordinates and display on map"""
        tier = self.tier_combo.currentText()
        entry = self.entry_combo.currentText()

        if tier == "All":
            tier = None

        if entry == "All":
            entry = None

        with self.db_manager.session_scope() as session:
            from db.repositories import ObservationRepository, PhotoRepository

            # Get observations with coordinates as DTOs (dictionaries)
            self.observations = ObservationRepository.get_observations_with_coordinates_for_display(
                session, self.lifelist_id, tier=tier, entry_name=entry
            )

            # Load primary photos for observations
            for obs in self.observations:
                # Get primary photo for this specific observation
                obs_photos = PhotoRepository.get_observation_photos(
                    session, obs['id']
                )

                # Find primary photo or use first photo
                primary_photo = None
                for photo in obs_photos:
                    if photo.is_primary:
                        primary_photo = photo
                        break

                # If no primary photo but there are photos, use the first one
                if not primary_photo and obs_photos:
                    primary_photo = obs_photos[0]

                if primary_photo:
                    # Generate thumbnail for marker
                    thumbnail = self._create_marker_thumbnail(
                        obs['lifelist_id'],
                        obs['id'],  # Use observation ID from the observation data
                        primary_photo.id
                    )
                    obs['marker_thumbnail'] = thumbnail
                else:
                    obs['marker_thumbnail'] = None

            if not self.observations:
                QMessageBox.information(
                    self,
                    "No Coordinates",
                    f"No {self.observation_term}s with coordinates found for the selected filters."
                )
                # Create empty observations list for map
                self.observations = []

            # Create/recreate the map with current observations
            self.create_map()

    def _create_marker_thumbnail(self, lifelist_id, observation_id, photo_id):
        """Create a base64 encoded image for map marker from original photo"""
        if not self.photo_manager:
            return None

        try:
            # Get the photo path from database
            with self.db_manager.session_scope() as session:
                from db.models import Photo
                photo = session.query(Photo).filter_by(id=photo_id).first()
                if not photo or not photo.file_path:
                    return None

                photo_path = photo.file_path

            # Load the original image
            from pathlib import Path
            if not Path(photo_path).exists():
                return None

            # Open and process the original image
            with Image.open(photo_path) as img:
                # Convert to RGB if necessary (removes alpha channel issues)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create RGB image with white background
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        rgb_img.paste(img, mask=img.split()[-1])
                    else:
                        rgb_img.paste(img)
                    img = rgb_img

                # Find the smaller dimension for square crop
                width, height = img.size
                min_dimension = min(width, height)

                # Calculate center crop
                left = (width - min_dimension) // 2
                top = (height - min_dimension) // 2
                right = left + min_dimension
                bottom = top + min_dimension

                # Crop to square
                square_img = img.crop((left, top, right, bottom))

                # Resize to a reasonable size for web display (200x200)
                # This gives us good quality even when scaled
                square_img = square_img.resize((200, 200), Image.Resampling.NEAREST)

                # Convert to base64 PNG for smaller file size
                buffer = io.BytesIO()
                square_img.save(buffer, format='PNG', quality=100, optimize=True)
                base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

                return f"data:image/jpeg;base64,{base64_image}"

        except Exception as e:
            print(f"Error creating marker image: {e}")
            return None

    def _save_map(self):
        """Save map as HTML file"""
        if not self.folium_map:
            QMessageBox.warning(self, "Error", "Map not available")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Map",
            "",
            "HTML Files (*.html)"
        )

        if file_path:
            try:
                # Save the folium map directly
                self.folium_map.save(file_path)
                QMessageBox.information(
                    self,
                    "Map Saved",
                    f"Map has been saved to {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save map: {str(e)}"
                )