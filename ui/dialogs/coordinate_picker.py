# ui/dialogs/coordinate_picker.py

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QLineEdit, \
    QMessageBox, QGroupBox
from PySide6.QtCore import Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QDoubleValidator
from typing import Dict, Any
from .base_map_dialog import BaseMapDialog, MapBridge


# Create a bridge class for JavaScript-Python communication
class CoordinateBridge(MapBridge):
    """Extended bridge for coordinate picker"""
    coordinatesChanged = Signal(float, float)

    @Slot(float, float)
    def updateCoordinates(self, lat, lng):
        """Slot to receive coordinates from JavaScript"""
        self.coordinatesChanged.emit(lat, lng)


class ClickableCoordinateEdit(QLineEdit):
    """Custom QLineEdit that shows a map picker when focused"""
    clicked = Signal()

    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setToolTip(f"Enter {placeholder_text.lower()} or click to select from map")

    def focusInEvent(self, event):
        """Show map picker on focus if field is empty"""
        super().focusInEvent(event)
        if not self.text().strip():
            self.clicked.emit()


class CoordinatePickerDialog(BaseMapDialog):
    """Dialog for selecting coordinates from an interactive map"""

    def __init__(self, parent=None, initial_lat=None, initial_lon=None):
        # Init coordinates
        if initial_lat is not None and initial_lon is not None:
            self.selected_lat = initial_lat
            self.selected_lon = initial_lon
        else:
            self.selected_lat = 0.0
            self.selected_lon = 0.0

        # Call parent constructor first
        super().__init__(parent, "Select Coordinates")

        # Replace the bridge with our specialized version
        self.coord_bridge = CoordinateBridge()
        self.coord_bridge.coordinatesChanged.connect(self._update_coordinates)
        self.coord_bridge.baseLayerChanged.connect(self._save_preferred_base_layer)

        # Update the channel to use our bridge
        self.channel = QWebChannel()
        self.channel.registerObject("coordBridge", self.coord_bridge)

    def add_controls(self):
        """Add coordinate picker specific controls"""
        # Instructions
        instructions = QLabel("Click on the map to select coordinates. The marker will move to your click location.")
        instructions.setWordWrap(True)
        self.layout().addWidget(instructions)

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

    def _on_load_finished(self, ok):
        """When the map is loaded, set up the web channel"""
        super()._on_load_finished(ok)

        if ok:
            # Set the web channel after the page loads
            self.map_view.page().setWebChannel(self.channel)

            # Initialize the bridge
            self.run_javascript("""
                // Set up the bridge to receive coordinates
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.coordBridge = channel.objects.coordBridge;
                    console.log("Bridge established");
                });
            """)

    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for coordinate picker"""
        return {
            'centerLat': self.selected_lat,
            'centerLon': self.selected_lon,
            'zoom': 13,  # Increased zoom for better detail
        }

    def get_custom_javascript(self) -> str:
        """Get custom JavaScript for coordinate picker"""
        return """
        let marker;
        const config = getMapConfig();

        // Create custom marker icon
        const markerIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background: #ff5050; border: 2px solid #fff; border-radius: 50%; width: 10px; height: 10px; box-shadow: 0 0 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [10, 10],
            iconAnchor: [6, 6],
            popupAnchor: [1, -6]
        });

        // Create marker
        marker = L.marker([config.centerLat, config.centerLon], {icon: markerIcon}).addTo(map);

        // Add popup to marker
        marker.bindPopup('Selected Location').openPopup();

        // Get coordinate display element
        const coordDisplay = document.getElementById('coordinate-display');

        // Function to update coordinate display
        function updateCoordinateDisplay(lat, lng) {
            if (coordDisplay) {
                coordDisplay.innerHTML = `
                    <strong>Selected Coordinates:</strong><br>
                    Latitude: ${lat.toFixed(6)}<br>
                    Longitude: ${lng.toFixed(6)}
                `;
            }

            // Send to Qt using the bridge
            if (window.coordBridge) {
                window.coordBridge.updateCoordinates(lat, lng);
                console.log("Sent coordinates to Qt:", lat, lng);
            }
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
            
            // Send to Qt using the coordinate bridge
            if (window.coordBridge) {
                window.coordBridge.updateCoordinates(lat, lng);
            }
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

    def get_custom_styles(self) -> str:
        """Get custom styles for coordinate picker"""
        return """
        #map {
            cursor: crosshair;
        }
        .coordinate-display {
            position: absolute;
            top: 10px;
            right: 50px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            z-index: 1000;
            font-family: monospace;
        }
        .map-help {
            position: absolute;
            bottom: 25px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            z-index: 1000;
            font-size: 12px;
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

    def _update_coordinates(self, lat, lng):
        """Update coordinates from map click - connected to the bridge signal"""
        self.selected_lat = lat
        self.selected_lon = lng

        # Update input fields (without triggering another update)
        self.lat_edit.blockSignals(True)
        self.lon_edit.blockSignals(True)

        self.lat_edit.setText(f"{lat:.6f}")
        self.lon_edit.setText(f"{lng:.6f}")

        self.lat_edit.blockSignals(False)
        self.lon_edit.blockSignals(False)

        print(f"Coordinates updated: {lat}, {lng}")

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
        print(f"Returning coordinates: {self.selected_lat}, {self.selected_lon}")
        return self.selected_lat, self.selected_lon