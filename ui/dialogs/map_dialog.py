# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QDialogButtonBox,
                               QFileDialog, QMessageBox, QSpinBox)
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import tempfile
import os
from PySide6.QtWebEngineCore import QWebEngineSettings


class MapDialog(QDialog):
    """Dialog for showing observations on a map"""

    def __init__(self, parent, db_manager, lifelist_id, observation_term="observation"):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observation_term = observation_term
        self.temp_file_path = None

        self.setWindowTitle(f"{observation_term.capitalize()} Map")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._load_observations()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Controls
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

        layout.addLayout(controls_layout)

        # Map view with necessary settings
        self.map_view = QWebEngineView()

        # Enable essential settings for external resource loading
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self.map_view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self.map_view)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Load tiers for the lifelist
        self._load_tiers()

        # Load unique entries for the lifelist
        self._load_entries()

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
            observations = ObservationRepository.get_observations_with_coordinates(
                session, self.lifelist_id, tier=tier, entry_name=entry
            )

            if not observations:
                QMessageBox.information(
                    self,
                    "No Coordinates",
                    f"No {self.observation_term}s with coordinates found for the selected filters."
                )
                # Create empty map instead of returning
                self._create_map([])
                return

            # Create map HTML
            self._create_map(observations)

    def _on_load_finished(self, ok):
        """Handle web view load finished event"""
        if not ok:
            print("Failed to load map HTML")
            QMessageBox.warning(self, "Warning", "Failed to load map. Please try again.")

    #def _on_console_message(self, level, message, line, source):
    #    """Handle JavaScript console messages for debugging"""
    #    print(f"JavaScript console [{level}]: {message} (line {line}, source: {source})")

    def _create_map(self, observations):
        """Create HTML for the map"""
        if not self.map_view:
            return

        # Generate markers
        markers = []
        for obs in observations:
            if obs.latitude is not None and obs.longitude is not None:
                marker = {
                    "lat": obs.latitude,
                    "lon": obs.longitude,
                    "title": obs.entry_name,
                    "popup": f"<strong>{obs.entry_name}</strong><br>"
                             f"Date: {obs.observation_date.strftime('%Y-%m-%d') if obs.observation_date else 'Unknown'}<br>"
                             f"Location: {obs.location or 'Unknown'}<br>"
                             f"Tier: {obs.tier or 'Unknown'}"
                }
                markers.append(marker)

        # Calculate center
        if markers:
            lat_sum = sum(m["lat"] for m in markers)
            lon_sum = sum(m["lon"] for m in markers)
            center_lat = lat_sum / len(markers)
            center_lon = lon_sum / len(markers)
        else:
            center_lat = 0
            center_lon = 0

        # Load template
        template = self._get_map_template()

        # Replace placeholders
        html_content = template.replace("{{center_lat}}", str(center_lat))
        html_content = html_content.replace("{{center_lon}}", str(center_lon))
        html_content = html_content.replace("{{zoom}}", str(self.zoom_spin.value()))
        html_content = html_content.replace("{{markers}}", json.dumps(markers))

        # Create temporary HTML file
        try:
            # Clean up previous temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except:
                    pass

            # Create new temp file
            fd, self.temp_file_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Load the HTML file
            self.map_view.load(QUrl.fromLocalFile(self.temp_file_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create map: {str(e)}")

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

    def _get_map_template(self):
        """Get HTML template for the map with extensive debugging"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Lifelist Map</title>
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
                }
                #debug {
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(255, 255, 255, 0.8);
                    padding: 10px;
                    border: 1px solid #ccc;
                    z-index: 1000;
                    max-width: 300px;
                    font-size: 12px;
                }
            </style>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        </head>
        <body>
            <div id="debug">Initializing...</div>
            <div id="map"></div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                const debug = document.getElementById('debug');

                function log(message) {
                    console.log(message);
                    debug.innerHTML += '<br>' + message;
                }

                log('Script started');
                log('Leaflet version: ' + (typeof L !== 'undefined' ? L.version : 'not loaded'));

                // Wait for DOM to be fully loaded
                document.addEventListener('DOMContentLoaded', function() {
                    log('DOM loaded');
                    initMap();
                });

                // Also try immediate initialization in case DOM is already loaded
                if (document.readyState === 'complete' || document.readyState === 'interactive') {
                    log('DOM already ready');
                    setTimeout(initMap, 100);
                }

                function initMap() {
                    log('initMap() called');

                    if (typeof L === 'undefined') {
                        log('ERROR: Leaflet not loaded!');
                        setTimeout(initMap, 100);
                        return;
                    }

                    try {
                        log('Creating map...');

                        const centerLat = {{center_lat}};
                        const centerLon = {{center_lon}};
                        const zoom = {{zoom}};

                        log('Map config: center=[' + centerLat + ',' + centerLon + '], zoom=' + zoom);

                        const map = L.map('map', {
                            center: [centerLat, centerLon],
                            zoom: zoom,
                            zoomControl: true
                        });

                        log('Map object created');

                        // Add tile layer
                        const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                            maxZoom: 19,
                            subdomains: ['a', 'b', 'c']
                        });

                        tileLayer.addTo(map);
                        log('Tile layer added');

                        // Add markers
                        const markers = {{markers}};
                        log('Markers to process: ' + markers.length);

                        if (markers.length > 0) {
                            markers.forEach(function(marker, index) {
                                if (marker.lat !== undefined && marker.lon !== undefined) {
                                    const m = L.marker([marker.lat, marker.lon])
                                        .addTo(map)
                                        .bindPopup(marker.popup);
                                    log('Added marker ' + index + ' at [' + marker.lat + ',' + marker.lon + ']');
                                }
                            });

                            // Fit bounds to markers
                            const group = new L.featureGroup(markers.filter(m => m.lat !== undefined && m.lon !== undefined).map(m => 
                                L.marker([m.lat, m.lon])
                            ));
                            map.fitBounds(group.getBounds().pad(0.1));
                            log('Fitted bounds to markers');
                        }

                        log('Map initialization complete!');
                        debug.style.display = 'none'; // Hide debug info after successful init

                    } catch (error) {
                        log('ERROR: ' + error.message);
                        log('Stack: ' + error.stack);
                    }
                }

                // Error handlers
                window.onerror = function(msg, url, lineNo, columnNo, error) {
                    log('Window Error: ' + msg + ' at line ' + lineNo);
                    return false;
                };

                log('Script setup complete');
            </script>
        </body>
        </html>
        """

    def closeEvent(self, event):
        """Clean up temporary files when closing"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.unlink(self.temp_file_path)
            except:
                pass
        super().closeEvent(event)