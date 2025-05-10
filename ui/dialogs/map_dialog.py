# ui/dialogs/map_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QDialogButtonBox,
                               QFileDialog, QMessageBox, QSpinBox)
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import tempfile
from config import Config


class MapDialog(QDialog):
    """Dialog for showing observations on a map"""

    def __init__(self, parent, db_manager, lifelist_id, observation_term="observation"):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observation_term = observation_term

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

        # Map view
        self.map_view = QWebEngineView()
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
                return

            # Create map HTML
            self._create_map(observations)

    def _create_map(self, observations):
        """Create HTML for the map"""
        # Generate markers
        markers = []
        bounds = []

        for obs in observations:
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

        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            f.write(template.encode("utf-8"))
            temp_path = f.name

        # Load HTML into WebView
        self.map_view.load(QUrl.fromLocalFile(temp_path))

    def _update_map_zoom(self):
        """Update map zoom level"""
        # Reload map with current filters but new zoom
        self._load_observations()

    def _save_map(self):
        """Save map as HTML file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Map",
            "",
            "HTML Files (*.html)"
        )

        if file_path:
            try:
                # Get current page HTML
                self.map_view.page().toHtml(lambda html: self._write_html_to_file(html, file_path))

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

    def _write_html_to_file(self, html, file_path):
        """Write HTML to file (callback for page().toHtml())"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)
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
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.css" />
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.js"></script>
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
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{{center_lat}}, {{center_lon}}], {{zoom}});

                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(map);

                var markers = {{markers}};

                markers.forEach(function(marker) {
                    L.marker([marker.lat, marker.lon])
                        .addTo(map)
                        .bindPopup(marker.popup);
                });
            </script>
        </body>
        </html>
        """