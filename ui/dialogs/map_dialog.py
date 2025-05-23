# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                               QComboBox, QDialogButtonBox, QFileDialog,
                               QMessageBox)
from typing import Dict, Any, List
import folium
from folium import plugins
import json
from .base_map_dialog import BaseMapDialog


class MapDialog(BaseMapDialog):
    """Dialog for showing observations on a map"""

    def __init__(self, parent, db_manager, lifelist_id, observation_term="observation"):
        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observation_term = observation_term

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

        # Create marker cluster for better performance with many markers
        if len(self.observations) > 10:
            self.marker_cluster = plugins.MarkerCluster(
                name="Observations",
                overlay=True,
                control=True,
                show=True
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

                # Create marker with custom icon and popup
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

            m.get_root().html.add_child(folium.Element(f"""
            <script>
            map.whenReady(function() {{
                setTimeout(function() {{
                    {bounds_js}
                }}, 100);
            }});
            </script>
            """))

        # Add a legend for tier colors
        self._add_tier_legend(m)

    def _add_tier_legend(self, m: folium.Map):
        """Add a legend showing tier colors"""
        # Get unique tiers from current observations
        tiers = list(set(obs.get('tier') for obs in self.observations if obs.get('tier')))

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
            from db.repositories import ObservationRepository

            # Get observations with coordinates as DTOs (dictionaries)
            self.observations = ObservationRepository.get_observations_with_coordinates_for_display(
                session, self.lifelist_id, tier=tier, entry_name=entry
            )

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