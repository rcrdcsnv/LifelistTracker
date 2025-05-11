# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QDialogButtonBox,
                               QFileDialog, QMessageBox, QSpinBox)
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import tempfile
import os
from pathlib import Path
from config import Config


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

        # Map view with error handling
        try:
            self.map_view = QWebEngineView()
            self.map_view.loadFinished.connect(self._on_load_finished)

            # Add console message handler for debugging
            page = self.map_view.page()
            page.javaScriptConsoleMessage.connect(self._on_console_message)

            layout.addWidget(self.map_view)
        except Exception as e:
            error_label = QLabel(f"Error initializing map view: {str(e)}")
            layout.addWidget(error_label)
            self.map_view = None
            print(f"Map initialization error: {e}")

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

    def _on_console_message(self, level, message, line, source):
        """Handle JavaScript console messages for debugging"""
        print(f"JavaScript console [{level}]: {message} (line {line}, source: {source})")

    def _create_map(self, observations):
        """Create HTML for the map"""
        if not self.map_view:
            return

        # Generate markers
        markers = []
        bounds = []

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
                bounds.append([obs.latitude, obs.longitude])

        # Load map template
        template = self._get_map_template()

        # Replace placeholders
        config = Config.load()
        zoom = self.zoom_spin.value()

        # Calculate center if we have markers
        if bounds:
            lat_sum = sum(b[0] for b in bounds)
            lon_sum = sum(b[1] for b in bounds)
            center_lat = lat_sum / len(bounds)
            center_lon = lon_sum / len(bounds)
        else:
            # Default center (0, 0)
            center_lat = 0
            center_lon = 0

        # Replace placeholders
        template = template.replace("{{center_lat}}", str(center_lat))
        template = template.replace("{{center_lon}}", str(center_lon))
        template = template.replace("{{zoom}}", str(zoom))
        template = template.replace("{{markers}}", json.dumps(markers))

        # Create temporary HTML file with better error handling
        try:
            # Clean up previous temp file if it exists
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except:
                    pass

            # Create new temp file
            fd, self.temp_file_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(template)

            # Load HTML into WebView
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
        """Get HTML template for the map"""
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
                }
                #map {
                    width: 100%;
                    height: 100%;
                }
                .loading {
                    text-align: center;
                    padding: 50px;
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    color: #333;
                }
                .error {
                    color: #d32f2f;
                    background-color: #ffebee;
                    border: 1px solid #ffcdd2;
                    padding: 10px;
                    margin: 10px;
                    border-radius: 4px;
                }
            </style>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        </head>
        <body>
            <div id="map"></div>
            <div id="loading" class="loading">Loading map...</div>
            <script>
                window.onerror = function(msg, url, lineNo, columnNo, error) {
                    var errorDiv = document.createElement('div');
                    errorDiv.className = 'error';
                    errorDiv.innerHTML = '<h3>Map Error</h3><p>' + msg + '</p>';
                    document.body.appendChild(errorDiv);
                    console.error('Window error:', msg, 'Line:', lineNo, 'Column:', columnNo, error);
                    return false;
                };

                try {
                    console.log('Starting map initialization...');

                    // Hide loading message
                    document.getElementById('loading').style.display = 'none';

                    var center_lat = {{center_lat}};
                    var center_lon = {{center_lon}};
                    var zoom = {{zoom}};

                    console.log('Creating map at:', center_lat, center_lon, 'zoom:', zoom);

                    var map = L.map('map').setView([center_lat, center_lon], zoom);

                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                        maxZoom: 19,
                        errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAACXBIWXMAAAsTAAALEwEAmpwYAAAKTWlDQ1BQaG90b3Nob3AgSUNDIHByb2ZpbGUAAHjanVN3WJP3Fj7f92UPVkLY8LGXbIEAIiOsCMgQWaIQkgBhhBASQMWFiApWFBURnEhVxILVCkidiOKgKLhnQYqIWotVXDjuH9yntX167+3t+9f7vOec5/zOec8PgBESJpHmomoAOVKFPDrYH49PSMTJvYACFUjgBCAQ5svCZwXFAADwA3l4fnSwP/wBr28AAgBw1S4kEsfh/4O6UCZXACCRAOAiEucLAZBSAMguVMgUAMgYALBTs2QKAJQAAGx5fEIiAKoNAOz0ST4FANipk9wXANiiHKkIAI0BAJkoRyQCQLsAYFWBUiwCwMIAoKxAIi4EwK4BgFm2MkcCgL0FAHaOWJAPQGAAgJlCLMwAIDgCAEMeE80DIEwDoDDSv+CpX3CFuEgBAMDLlc2XS9IzFLiV0Bp38vDg4iHiwmyxQmEXKRBmCeQinJebIxNI5wNMzgwAABr50cH+OD+Q5+bk4eZm52zv9MWi/mvwbyI+IfHf/ryMAgQAEE7P79pf5eXWA3DHAbB1v2upWwDaVgBo3/ldM9sJoFoK0Hr5i3k4/EAenqFQyDwdHAoLC+0lYqG9MOOLPv8z4W/gi372/EAe/tt68ABxmkCZrcCjg/1xYW52rlKO58sEQjFu9+cj/seFf/2OKdHiNLFcLBWK8ViJuFAiTcd5uVKRRCHJleIS6X8y8R+W/QmTdw0ArIZPwE62B7XLbMB+7gECiw5Y0nYAQH7zLYwaC5EAEGc0Mnn3AACTv/mPQCsBAM2XpOMAALzoGFyolBdMxggAAESggSqwQQcMwRSswA6cwR28wBcCYQZEQAwkwDwQQgbkgBwKoRiWQRlUwDrYBLWwAxqgEZrhELTBMTgN5+ASXIHrcBcGYBiewhi8hgkEQcgIE2EhOogRYo7YIs4IF5mOBCJhSDSSgKQg6YgUUSLFyHKkAqlCapFdSCPyLXIUOY1cQPqQ28ggMor8irxHMZSBslED1AJ1QLmoHxqKxqBz0XQ0D12AlqJr0Rq0Hj2AtqKn0UvodXQAfYqOY4DRMQ5mjNlhXIyHRWCJWBomxxZj5Vg1Vo81Yx1YN3YVG8CeYe8IJAKLgBPsCF6EEMJsgpCQR1hMWEOoJewjtBK6CFcJg4Qxwicik6hPtCV6EvnEeGI6sZBYRqwm7iEeIZ4lXicOE1+TSCQOyZLkTgohJZAySQtJa0jbSC2kU6Q+0hBpnEwm65Btyd7kCLKArCCXkbeQD5BPkvvJw+S3FDrFiOJMCaIkUqSUEko1ZT/lBKWfMkKZoKpRzame1AiqiDqfWkltoHZQL1OHqRM0dZolzZsWQ8ukLaPV0JppZ2n3aC/pdLoJ3YMeRZfQl9Jr6Afp5+mD9HcMDYYNg8dIYigZaxl7GacYtxkvmUymBdOXmchUMNcyG5lnmA+Yb1VYKvYqfBWRyhKVOpVWlX6V56pUVXNVP9V5qgtUq1UPq15WfaZGVbNQ46kJ1Bar1akdVbupNq7OUndSj1DPUV+jvl/9gvpjDbKGhUaghkijVGO3xhmNIRbGMmXxWELWclYD6yxrmE1iW7L5rLWsS6xFrOusum1N2zpN2rVTN"'},
                    ]).addTo(map);

                    var markers = {{markers}};
                    console.log('Markers to add:', markers.length);

                    var markerInstances = [];
                    markers.forEach(function(marker, index) {
                        if (marker.lat !== undefined && marker.lon !== undefined) {
                            console.log('Adding marker', index, 'at', marker.lat, marker.lon);
                            var m = L.marker([marker.lat, marker.lon])
                                .addTo(map)
                                .bindPopup(marker.popup);
                            markerInstances.push(m);
                        } else {
                            console.warn('Skipping marker', index, 'due to missing coordinates');
                        }
                    });

                    // Fit map to markers if any exist
                    if (markerInstances.length > 0) {
                        console.log('Fitting bounds to', markerInstances.length, 'markers');
                        var group = new L.featureGroup(markerInstances);
                        map.fitBounds(group.getBounds().pad(0.1));
                    } else {
                        console.log('No markers to fit bounds to, using default view');
                    }

                    console.log('Map initialization complete');

                } catch (error) {
                    console.error('Error loading map:', error);
                    var errorDiv = document.createElement('div');
                    errorDiv.className = 'error';
                    errorDiv.innerHTML = '<h3>Error loading map</h3><p>' + error.message + '</p><p>Please check the browser console for more details.</p>';
                    document.body.appendChild(errorDiv);
                    document.getElementById('loading').innerHTML = 'Error: ' + error.message;
                }
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