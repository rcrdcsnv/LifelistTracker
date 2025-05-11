# ui/dialogs/coordinate_picker.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QDialogButtonBox, QLineEdit,
                               QMessageBox, QGroupBox)
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtGui import QDoubleValidator
import tempfile
import os


class CoordinatePickerDialog(QDialog):
    """Dialog for selecting coordinates from an interactive map"""

    def __init__(self, parent=None, initial_lat=None, initial_lon=None):
        super().__init__(parent)

        self.selected_lat = initial_lat or 40.0
        self.selected_lon = initial_lon or -95.0
        self.temp_file_path = None

        self.setWindowTitle("Select Coordinates")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._create_map()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Click on the map to select coordinates. The marker will move to your click location.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

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

        layout.addWidget(search_group)

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

        layout.addWidget(coords_group)

        # Map view
        self.map_view = QWebEngineView()

        # Enable essential settings for external resource loading
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self.map_view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self.map_view)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_load_finished(self, ok):
        """Handle web view load finished event"""
        if not ok:
            print("Failed to load map HTML")
            QMessageBox.warning(self, "Warning", "Failed to load map. Please try again.")

    def _create_map(self):
        """Create the interactive map HTML"""
        # Load template
        template = self._get_map_template()

        # Replace placeholders
        html_content = template.replace("{{selected_lat}}", str(self.selected_lat))
        html_content = html_content.replace("{{selected_lon}}", str(self.selected_lon))

        # Create temporary HTML file
        try:
            # Clean up previous temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except Exception:
                    pass

            # Create new temp file
            fd, self.temp_file_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Load the HTML file
            self.map_view.load(QUrl.fromLocalFile(self.temp_file_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create map: {str(e)}")

    def _get_map_template(self):
        """Get HTML template for the coordinate picker map"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Coordinate Picker</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                html, body {
                    height: 100%;
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                }
                #map {
                    width: 100%;
                    height: 100%;
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
                .loading-message {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(255, 255, 255, 0.9);
                    padding: 20px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    z-index: 1000;
                    font-size: 18px;
                }
            </style>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        </head>
        <body>
            <div class="loading-message" id="loading">Loading map, please wait...</div>
            <div id="coordinate-display" class="coordinate-display">
                Click on the map to select coordinates
            </div>
            <div class="map-help">
                💡 <strong>Tips:</strong> Scroll to zoom • Hold Shift and drag to zoom area • Double-click to zoom in
            </div>
            <div id="map"></div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                const loading = document.getElementById('loading');

                // Initialize map when DOM is ready
                document.addEventListener('DOMContentLoaded', function() {
                    initMap();
                });

                // Also initialize if DOM is already ready
                if (document.readyState === 'complete' || document.readyState === 'interactive') {
                    setTimeout(initMap, 100);
                }

                let map, marker;

                function initMap() {
                    if (typeof L === 'undefined') {
                        setTimeout(initMap, 100);
                        return;
                    }

                    try {
                        const centerLat = {{selected_lat}};
                        const centerLon = {{selected_lon}};

                        // Initialize map
                        map = L.map('map', {
                            center: [centerLat, centerLon],
                            zoom: 10,
                            zoomControl: true
                        });

                        // Add OpenStreetMap tiles
                        const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                            maxZoom: 19,
                            subdomains: ['a', 'b', 'c']
                        });

                        tileLayer.addTo(map);

                        // Hide loading message when tiles are loaded
                        tileLayer.on('load', function() {
                            loading.style.display = 'none';
                        });

                        // Create custom marker icon
                        const markerIcon = L.divIcon({
                            className: 'custom-marker',
                            html: '<div style="background: #ff0000; border: 2px solid #fff; border-radius: 50%; width: 20px; height: 20px; box-shadow: 0 0 4px rgba(0,0,0,0.3);"></div>',
                            iconSize: [20, 20],
                            iconAnchor: [10, 20],
                            popupAnchor: [0, -20]
                        });

                        // Create marker
                        marker = L.marker([centerLat, centerLon], {icon: markerIcon}).addTo(map);

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
                        updateCoordinateDisplay(centerLat, centerLon);

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

                    } catch (error) {
                        loading.innerHTML = 'Error loading map. Please refresh and try again.';
                        loading.style.background = 'rgba(255, 0, 0, 0.9)';
                        loading.style.color = 'white';
                        console.error('Map initialization error:', error);
                    }
                }
            </script>
        </body>
        </html>
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
            self.map_view.page().runJavaScript(f"window.updateMarker({lat}, {lon})")

        except ValueError:
            QMessageBox.warning(self, "Invalid Input",
                                "Please enter valid numeric coordinates.")

    def get_coordinates(self):
        """Get the selected coordinates"""
        return self.selected_lat, self.selected_lon

    def closeEvent(self, event):
        """Clean up temporary files when closing"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.unlink(self.temp_file_path)
            except Exception:
                pass
        super().closeEvent(event)