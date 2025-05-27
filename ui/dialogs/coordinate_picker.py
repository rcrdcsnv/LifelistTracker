# ui/dialogs/coordinate_picker.py
import os
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Signal, Slot
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
        # Init coordinates FIRST
        if initial_lat is not None and initial_lon is not None:
            self.selected_lat = initial_lat
            self.selected_lon = initial_lon
        else:
            self.selected_lat = 0.0
            self.selected_lon = 0.0

        # Call parent constructor
        super().__init__(parent, "Select Coordinates")

        # Create our specialized bridge and replace the base class one
        self.coord_bridge = CoordinateBridge()
        self.coord_bridge.coordinatesChanged.connect(self._update_coordinates)
        self.coord_bridge.baseLayerChanged.connect(self._save_preferred_base_layer)

        # Replace the channel from base class with our own
        from PySide6.QtWebChannel import QWebChannel
        self.channel = QWebChannel()
        self.channel.registerObject("coordBridge", self.coord_bridge)

    def _on_load_finished(self, ok):
        """Override to ensure our channel is set properly"""
        if not ok:
            print("Failed to load coordinate picker map")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Failed to load map. Please try again.")
        else:
            print("Coordinate picker map loaded successfully")
            # Set up our custom web channel
            self.map_view.page().setWebChannel(self.channel)
            self.map_loaded.emit()

    def add_controls(self):
        """Add coordinate picker specific controls"""
        from PySide6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QPushButton, QGroupBox
        from PySide6.QtGui import QDoubleValidator

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
        from PySide6.QtWidgets import QDialogButtonBox

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

        # Create map after UI is set up
        self.create_coordinate_picker_map()

    def get_map_config(self):
        """Get map configuration for coordinate picker"""
        return {
            'centerLat': self.selected_lat,
            'centerLon': self.selected_lon,
            'zoom': 13,  # Increased zoom for better detail
        }

    def _create_custom_html_template(self):
        """Create custom HTML template with folium map embedded"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Coordinate Picker</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                html, body {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                }}
                #map {{
                    width: 100%;
                    height: 100%;
                    cursor: crosshair;
                }}
                .coordinate-info {{
                    position: absolute;
                    top: 10px;
                    right: 60px;
                    background: rgba(255, 255, 255, 0.95);
                    padding: 12px;
                    border: 2px solid #007cba;
                    border-radius: 8px;
                    z-index: 1000;
                    font-family: Arial, sans-serif;
                    font-size: 13px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                }}
                .map-help {{
                    position: absolute;
                    bottom: 40px;
                    left: 10px;
                    background: rgba(255, 255, 255, 0.9);
                    padding: 8px 12px;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    z-index: 1000;
                    font-size: 12px;
                    max-width: 280px;
                }}
            </style>
        </head>
        <body>
            <div class="coordinate-info" id="coordinate-display">
                <div style="font-weight: bold; color: #007cba; margin-bottom: 8px;">📍 Selected Coordinates</div>
                <div id="coord-lat">Lat: {self.selected_lat:.6f}</div>
                <div id="coord-lng">Lng: {self.selected_lon:.6f}</div>
            </div>

            <div class="map-help">
                💡 <strong>Tips:</strong> Click anywhere to place marker • Scroll to zoom • Double-click to zoom in
            </div>

            <div id="map"></div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                // Global variables
                let map, marker, coordBridge;
                let bridgeSetupAttempts = 0;
                const maxBridgeAttempts = 20; // 1 second total

                // Initialize when page loads
                window.addEventListener('load', function() {{
                    console.log("Page loaded, initializing map...");
                    initMap();
                    setTimeout(setupBridge, 100); // Small delay to ensure Qt is ready
                }});

                function initMap() {{
                    console.log("Initializing map...");

                    // Create map
                    map = L.map('map', {{
                        center: [{self.selected_lat}, {self.selected_lon}],
                        zoom: 13,
                        zoomControl: true
                    }});

                    // Add base layers
                    const baseMaps = {{
                        "OpenStreetMap": L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                            maxZoom: 19
                        }}),
                        "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                            attribution: 'Tiles &copy; Esri',
                            maxZoom: 18
                        }}),
                        "Terrain": L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
                            attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap',
                            maxZoom: 17
                        }})
                    }};

                    // Add default layer
                    baseMaps["OpenStreetMap"].addTo(map);

                    // Add layer control
                    L.control.layers(baseMaps).addTo(map);

                    // Create initial marker
                    marker = L.marker([{self.selected_lat}, {self.selected_lon}], {{
                        draggable: true
                    }}).addTo(map);

                    marker.bindPopup('Selected Location').openPopup();

                    console.log("Map initialization complete!");
                }}

                function setupBridge() {{
                    bridgeSetupAttempts++;
                    console.log(`Bridge setup attempt ${{bridgeSetupAttempts}}...`);

                    if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                        console.log("Qt WebChannel transport found!");
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            coordBridge = channel.objects.coordBridge;
                            if (coordBridge) {{
                                console.log("✓ CoordBridge established successfully!");
                                setupEventHandlers();
                            }} else {{
                                console.error("❌ CoordBridge object not found in channel");
                            }}
                        }});
                    }} else if (bridgeSetupAttempts < maxBridgeAttempts) {{
                        console.log("Qt WebChannel not ready, retrying...");
                        setTimeout(setupBridge, 50);
                    }} else {{
                        console.error("❌ Failed to establish Qt WebChannel after maximum attempts");
                    }}
                }}

                function setupEventHandlers() {{
                    console.log("Setting up event handlers...");

                    // Handle map clicks
                    map.on('click', function(e) {{
                        console.log("🎯 Map clicked at:", e.latlng.lat, e.latlng.lng);
                        updateCoordinates(e.latlng.lat, e.latlng.lng);
                    }});

                    // Handle marker drag
                    marker.on('dragend', function(e) {{
                        const pos = e.target.getLatLng();
                        console.log("🎯 Marker dragged to:", pos.lat, pos.lng);
                        updateCoordinates(pos.lat, pos.lng);
                    }});

                    console.log("✓ Event handlers attached!");
                }}

                function updateCoordinates(lat, lng) {{
                    console.log("📍 Updating coordinates to:", lat, lng);

                    // Move marker
                    marker.setLatLng([lat, lng]);

                    // Update display
                    document.getElementById('coord-lat').textContent = 'Lat: ' + lat.toFixed(6);
                    document.getElementById('coord-lng').textContent = 'Lng: ' + lng.toFixed(6);

                    // Send to Qt
                    if (coordBridge) {{
                        try {{
                            console.log("📡 Sending to Qt:", lat, lng);
                            coordBridge.updateCoordinates(lat, lng);
                            console.log("✓ Sent to Qt successfully!");
                        }} catch (e) {{
                            console.error("❌ Error sending to Qt:", e);
                        }}
                    }} else {{
                        console.error("❌ Bridge not available");
                    }}
                }}

                // Global function for Qt to call
                window.updateMarkerPosition = function(lat, lng) {{
                    console.log("📥 Qt requested marker update:", lat, lng);
                    if (marker && map) {{
                        marker.setLatLng([lat, lng]);
                        map.setView([lat, lng]);
                        document.getElementById('coord-lat').textContent = 'Lat: ' + lat.toFixed(6);
                        document.getElementById('coord-lng').textContent = 'Lng: ' + lng.toFixed(6);
                        console.log("✓ Marker updated from Qt");
                    }}
                }};
            </script>
        </body>
        </html>
        """

    def _update_coordinates(self, lat, lng):
        """Update coordinates from map click - connected to the bridge signal"""
        print(f"Bridge received coordinates: {lat}, {lng}")
        self.selected_lat = lat
        self.selected_lon = lng

        # Update input fields (without triggering another update)
        self.lat_edit.blockSignals(True)
        self.lon_edit.blockSignals(True)

        self.lat_edit.setText(f"{lat:.6f}")
        self.lon_edit.setText(f"{lng:.6f}")

        self.lat_edit.blockSignals(False)
        self.lon_edit.blockSignals(False)

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
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Latitude",
                                    "Latitude must be between -90 and 90.")
                return

            if not (-180 <= lon <= 180):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Longitude",
                                    "Longitude must be between -180 and 180.")
                return

            # Update internal state
            self.selected_lat = lat
            self.selected_lon = lon

            # Update map marker using JavaScript
            print(f"Updating map to coordinates: {lat}, {lon}")
            self.run_javascript(f"window.updateMarkerPosition({lat}, {lon})")

        except ValueError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input",
                                "Please enter valid numeric coordinates.")

    def accept(self):
        """Override accept to ensure coordinates are up-to-date from fields"""
        try:
            # Get final coordinates from the input fields
            lat = float(self.lat_edit.text())
            lon = float(self.lon_edit.text())

            # Validate ranges one final time
            if not (-90 <= lat <= 90):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Latitude",
                                    "Latitude must be between -90 and 90.")
                return

            if not (-180 <= lon <= 180):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Longitude",
                                    "Longitude must be between -180 and 180.")
                return

            # Update internal state with final values
            self.selected_lat = lat
            self.selected_lon = lon

            print(f"Dialog accepting with coordinates: {self.selected_lat}, {self.selected_lon}")

            # Call parent accept
            super().accept()

        except ValueError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input",
                                "Please enter valid numeric coordinates.")
            return

    def create_coordinate_picker_map(self):
        """Create coordinate picker map using custom HTML template"""
        try:
            # Get the custom HTML template directly
            map_html = self._create_custom_html_template()

            # Clean up previous temp file
            if hasattr(self, 'temp_file_path') and self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except Exception:
                    pass

            # Create new temp file
            import tempfile
            import os
            fd, self.temp_file_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(map_html)

            # Load the HTML file
            from PySide6.QtCore import QUrl
            self.map_view.load(QUrl.fromLocalFile(self.temp_file_path))

        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to create map: {str(e)}")

    def run_javascript(self, js_code: str):
        """Execute JavaScript code in the web view"""
        if self.map_view:
            self.map_view.page().runJavaScript(js_code)

    def get_coordinates(self):
        """Get the selected coordinates"""
        print(f"Returning coordinates: {self.selected_lat}, {self.selected_lon}")
        return self.selected_lat, self.selected_lon

    def closeEvent(self, event):
        """Clean up temporary files when closing"""
        if hasattr(self, 'temp_file_path') and self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                import os
                os.unlink(self.temp_file_path)
            except Exception:
                pass
        super().closeEvent(event)