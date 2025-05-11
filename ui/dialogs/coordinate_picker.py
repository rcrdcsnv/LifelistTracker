# ui/dialogs/coordinate_picker.py
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QDialogButtonBox, QLineEdit, QMessageBox, QGroupBox)
from PySide6.QtGui import QDoubleValidator
from typing import Dict, Any
from .base_map_dialog import BaseMapDialog


class CoordinatePickerDialog(BaseMapDialog):
    """Dialog for selecting coordinates from an interactive map"""

    def __init__(self, parent=None, initial_lat=None, initial_lon=None):
        # Only use defaults if no coordinates are provided
        if initial_lat is not None and initial_lon is not None:
            self.selected_lat = initial_lat
            self.selected_lon = initial_lon
        else:
            # Default to user's location or a reasonable fallback
            self.selected_lat = 40.0
            self.selected_lon = -95.0

        self.lat_edit = None
        self.lon_edit = None
        self.update_map_btn = None

        super().__init__(parent, "Select Coordinates")

    def add_controls(self):
        """Add coordinate picker specific controls"""
        # Instructions
        instructions = QLabel("Click on the map to select coordinates. The marker will move to your click location.")
        instructions.setWordWrap(True)
        self.layout().addWidget(instructions)

        # Search group (future enhancement)
        search_group = QGroupBox("Search Location")
        search_layout = QHBoxLayout(search_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search for a place (Coming Soon)")
        self.search_edit.setEnabled(False)  # Disabled for now
        search_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.setEnabled(False)  # Disabled for now
        search_layout.addWidget(self.search_btn)

        self.layout().addWidget(search_group)

        # Coordinate display group
        coords_group = QGroupBox("Selected Coordinates")
        coords_layout = QHBoxLayout(coords_group)

        coords_layout.addWidget(QLabel("Latitude:"))
        self.lat_edit = QLineEdit()
        self.lat_edit.setValidator(QDoubleValidator(-90.0, 90.0, 6))
        self.lat_edit.setText(str(self.selected_lat))
        self.lat_edit.textChanged.connect(self._on_manual_coordinate_change)
        coords_layout.addWidget(self.lat_edit)

        coords_layout.addWidget(QLabel("Longitude:"))
        self.lon_edit = QLineEdit()
        self.lon_edit.setValidator(QDoubleValidator(-180.0, 180.0, 6))
        self.lon_edit.setText(str(self.selected_lon))
        self.lon_edit.textChanged.connect(self._on_manual_coordinate_change)
        coords_layout.addWidget(self.lon_edit)

        self.update_map_btn = QPushButton("Update Map")
        self.update_map_btn.clicked.connect(self._update_map_from_fields)
        coords_layout.addWidget(self.update_map_btn)

        self.layout().addWidget(coords_group)

    def add_bottom_controls(self):
        """Add dialog buttons at the bottom"""
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

        # Create map after UI is set up
        self.create_map()

    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for coordinate picker"""
        config = {
            'centerLat': self.selected_lat,
            'centerLon': self.selected_lon,
            'zoom': 13  # Increased zoom for better detail when we have specific coordinates
        }
        print(f"CoordinatePickerDialog: map config = {config}")  # Debug
        return config

    def get_custom_styles(self) -> str:
        """Get custom styles for coordinate picker"""
        return """
        #map {
            cursor: crosshair;
        }
        .coordinate-display {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            z-index: 1000;
            font-family: monospace;
        }
        .map-help {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            z-index: 1000;
            font-size: 12px;
        }
        .custom-marker {
            position: absolute;
            transform: translate(-50%, -100%);
        }
        """

    def get_custom_content(self) -> str:
        """Get custom HTML content for coordinate picker"""
        return """
        <div id="coordinate-display" class="coordinate-display">
            Click on the map to select coordinates
        </div>
        <div class="map-help">
            💡 <strong>Tips:</strong> Scroll to zoom • Hold Shift and drag to zoom area • Double-click to zoom in
        </div>
        """

    def get_custom_javascript(self) -> str:
        """Get custom JavaScript for coordinate picker"""
        return """
        let marker;
        const config = getMapConfig();

        // Create custom marker icon
        const markerIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background: #ff0000; border: 2px solid #fff; border-radius: 50%; width: 20px; height: 20px; box-shadow: 0 0 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 20],
            popupAnchor: [0, -20]
        });

        // Create marker
        marker = L.marker([config.centerLat, config.centerLon], {icon: markerIcon}).addTo(map);

        // Add popup to marker
        marker.bindPopup('Selected Location').openPopup();

        // Get coordinate display element
        const coordDisplay = document.getElementById('coordinate-display');

        // Function to update coordinate display
        function updateCoordinateDisplay(lat, lng) {
            coordDisplay.innerHTML = `
                <strong>Selected Coordinates:</strong><br>
                Latitude: ${lat.toFixed(6)}<br>
                Longitude: ${lng.toFixed(6)}
            `;
        }

        // Show initial coordinates
        updateCoordinateDisplay(config.centerLat, config.centerLon);

        // Handle map clicks
        map.on('click', function(e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;

            // Move marker to clicked location
            marker.setLatLng([lat, lng]);

            // Update coordinate display
            updateCoordinateDisplay(lat, lng);

            // Send coordinates to Qt application
            console.log('COORDINATES:' + JSON.stringify({lat: lat, lng: lng}));
        });

        // Handle coordinate updates from Qt
        window.updateMarker = function(lat, lng) {
            if (marker && map) {
                marker.setLatLng([lat, lng]);
                map.setView([lat, lng]);
                updateCoordinateDisplay(lat, lng);
            }
        };
        """

    def _update_coordinates(self, lat, lng):
        """Update coordinates from map click"""
        self.selected_lat = lat
        self.selected_lon = lng

        # Update input fields
        self.lat_edit.setText(f"{lat:.6f}")
        self.lon_edit.setText(f"{lng:.6f}")

    def _on_manual_coordinate_change(self):
        """Handle manual coordinate input changes"""
        # Don't update immediately - wait for user to finish typing
        pass

    def _update_map_from_fields(self):
        """Update map marker based on manually entered coordinates"""
        try:
            lat = float(self.lat_edit.text())
            lon = float(self.lon_edit.text())

            # Validate ranges
            if not (-90 <= lat <= 90):
                QMessageBox.warning(self, "Invalid Latitude",
                                    "Latitude must be between -90 and 90.")
                return

            if not (-180 <= lon <= 180):
                QMessageBox.warning(self, "Invalid Longitude",
                                    "Longitude must be between -180 and 180.")
                return

            self.selected_lat = lat
            self.selected_lon = lon

            # Update map marker using JavaScript
            self.run_javascript(f"window.updateMarker({lat}, {lon})")

        except ValueError:
            QMessageBox.warning(self, "Invalid Input",
                                "Please enter valid numeric coordinates.")

    def get_coordinates(self):
        """Get the selected coordinates"""
        return self.selected_lat, self.selected_lon