# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QComboBox, QDialogButtonBox, QFileDialog,
                               QMessageBox, QSpinBox)
from typing import Dict, Any, List
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
        self.zoom_spin = None
        self.apply_btn = None
        self.save_btn = None

        # Map data
        self.observations = []

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

        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))

        self.zoom_spin = QSpinBox()
        self.zoom_spin.setMinimum(1)
        self.zoom_spin.setMaximum(18)
        self.zoom_spin.setValue(5)
        self.zoom_spin.valueChanged.connect(self._update_map_zoom)
        zoom_layout.addWidget(self.zoom_spin)

        controls_layout.addLayout(zoom_layout)

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
            valid_coords = [(obs.latitude, obs.longitude) for obs in self.observations
                            if obs.latitude is not None and obs.longitude is not None]

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

    def get_custom_javascript(self) -> str:
        """Get custom JavaScript for observation map"""
        # Generate markers data
        markers = []
        for obs in self.observations:
            if obs.latitude is not None and obs.longitude is not None:
                marker = {
                    "lat": obs.latitude,
                    "lon": obs.longitude,
                    "title": obs.entry_name,
                    "popup": f"<strong>{obs.entry_name}</strong><br>" +
                             f"Date: {obs.observation_date.strftime('%Y-%m-%d') if obs.observation_date else 'Unknown'}<br>" +
                             f"Location: {obs.location or 'Unknown'}<br>" +
                             f"Tier: {obs.tier or 'Unknown'}"
                }
                markers.append(marker)

        markers_json = json.dumps(markers)
        # Get user's selected zoom if available, otherwise use calculated zoom
        use_fit_bounds = len(markers) > 1  # Only use fitBounds for multiple markers

        return f"""
        
        // Add markers
        const markers = {markers_json};
        const useFitBounds = {json.dumps(use_fit_bounds)};
        console.log('Markers to process: ' + markers.length);

        if (markers.length > 0) {{
            const markerLayer = L.layerGroup();
            
            markers.forEach(function(marker, index) {{
                if (marker.lat !== undefined && marker.lon !== undefined) {{
                    const m = L.marker([marker.lat, marker.lon])
                        .addTo(markerLayer)
                        .bindPopup(marker.popup);
                    console.log('Added marker ' + index + ' at [' + marker.lat + ',' + marker.lon + ']');
                }}
            }});
            
            markerLayer.addTo(map);

            // Use fitBounds only for multiple markers, otherwise the map config zoom is used
            if (useFitBounds) {{
                // Add some padding around the markers
                map.fitBounds(markerLayer.getBounds().pad(0.1));
                console.log('Fitted bounds to markers');
            }}
        }}

        console.log('Map initialization complete!');
        """

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

            # Get observations with coordinates
            self.observations = ObservationRepository.get_observations_with_coordinates(
                session, self.lifelist_id, tier=tier, entry_name=entry
            )

            if not self.observations:
                QMessageBox.information(
                    self,
                    "No Coordinates",
                    f"No {self.observation_term}s with coordinates found for the selected filters."
                )
                # Create empty map
                self.observations = []

            # Create/recreate the map with current observations
            self.create_map()

    def _update_map_zoom(self):
        """Update map zoom level"""
        # Reload map with current filters but new zoom
        self._load_observations()

    def _save_map(self):
        """Save map as HTML file"""
        if not self.map_view:
            QMessageBox.warning(self, "Error", "Map view not available")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Map",
            "",
            "HTML Files (*.html)"
        )

        if file_path:
            try:
                # Get current page HTML with a callback
                def save_callback(html):
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(html)
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

                self.map_view.page().toHtml(save_callback)

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save map: {str(e)}"
                )