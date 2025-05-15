# ui/dialogs/base_map_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
import tempfile
import os
from typing import Dict, Any

class BaseMapDialog(QDialog):
    """Base class for dialogs that use Leaflet maps"""

    # Signal emitted when map is loaded
    map_loaded = Signal()

    def __init__(self, parent=None, title="Map Dialog"):
        super().__init__(parent)

        self.temp_file_path = None
        self.map_view = None

        self.setWindowTitle(title)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the basic UI structure"""
        layout = QVBoxLayout(self)

        # Add any custom controls (subclasses should override add_controls)
        self.add_controls()

        # Create map view
        self.map_view = QWebEngineView()

        # Enable essential settings for external resource loading
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self.map_view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self.map_view)

        # Add any custom bottom controls
        self.add_bottom_controls()

    def add_controls(self):
        """Add custom controls to the top of the dialog - Override in subclasses"""
        pass

    def add_bottom_controls(self):
        """Add custom controls to the bottom of the dialog (optional override)"""
        pass

    def _on_load_finished(self, ok):
        """Handle web view load finished event"""
        if not ok:
            print("Failed to load map HTML")
            QMessageBox.warning(self, "Warning", "Failed to load map. Please try again.")
        else:
            self.map_loaded.emit()

    def create_and_load_map(self, html_content: str):
        """Create temporary HTML file and load it in the map view"""
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

    def get_base_html_template(self) -> str:
        """Get the base HTML template with common Leaflet setup"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Map</title>
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
                {{custom_styles}}
            </style>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        </head>
        <body>
            <div class="loading-message" id="loading">Loading map, please wait...</div>
            {{custom_content}}
            <div id="map"></div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                // Global variables
                let map, tileLayer;
                const loading = document.getElementById('loading');

                // Initialize map when DOM is ready
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(initMap, 100);
                });

                // Also initialize if DOM is already ready
                if (document.readyState === 'complete' || document.readyState === 'interactive') {
                    setTimeout(initMap, 200);
                }

                function initMap() {
                    if (typeof L === 'undefined') {
                        setTimeout(initMap, 100);
                        return;
                    }

                    try {
                        // Get configuration from template
                        const config = getMapConfig();

                        // Initialize map with configuration
                        map = L.map('map', {
                            center: [config.centerLat, config.centerLon],
                            zoom: config.zoom,
                            zoomControl: true
                        });

                        // Add OpenStreetMap tiles
                        tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                            maxZoom: 19,
                            subdomains: ['a', 'b', 'c']
                        });

                        tileLayer.addTo(map);

                        // Hide loading message when tiles are loaded
                        tileLayer.on('load', function() {
                            loading.style.display = 'none';
                            // Invalidate size to ensure proper centering
                            map.invalidateSize();
                        });

                        // Allow subclasses to initialize their specific features
                        initializeCustomFeatures();

                    } catch (error) {
                        loading.innerHTML = 'Error loading map. Please refresh and try again.';
                        loading.style.background = 'rgba(255, 0, 0, 0.9)';
                        loading.style.color = 'white';
                        console.error('Map initialization error:', error);
                    }
                }

                // Function to be replaced by subclasses
                {{config_javascript}}

                // Function to be replaced by subclasses
                {{features_javascript}}
            </script>
        </body>
        </html>
        """

    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for the template - Override in subclasses"""
        return {'centerLat': 40.0, 'centerLon': -95.0, 'zoom': 5}

    def get_custom_javascript(self) -> str:
        """Get custom JavaScript for the map - Override in subclasses"""
        return ""

    def get_custom_styles(self) -> str:
        """Get custom CSS styles (optional override)"""
        return ""

    def get_custom_content(self) -> str:
        """Get custom HTML content between body and map (optional override)"""
        return ""

    def create_map(self):
        """Create the map using template and configuration"""
        # Get template
        template = self.get_base_html_template()

        # Get configuration
        config = self.get_map_config()

        # Replace custom placeholders
        html_content = template.replace("{{custom_styles}}", self.get_custom_styles())
        html_content = html_content.replace("{{custom_content}}", self.get_custom_content())

        # Create the configuration JavaScript
        config_js = f"""
        function getMapConfig() {{
            return {{
                centerLat: {config.get('centerLat', 40.0)},
                centerLon: {config.get('centerLon', -95.0)},
                zoom: {config.get('zoom', 5)}
            }};
        }}
        """

        # Create the custom features JavaScript
        features_js = f"""
        function initializeCustomFeatures() {{
            {self.get_custom_javascript()}
        }}
        """

        # Replace the placeholders with actual JavaScript
        html_content = html_content.replace("{{config_javascript}}", config_js)
        html_content = html_content.replace("{{features_javascript}}", features_js)

        # Create and load the map
        self.create_and_load_map(html_content)

    def run_javascript(self, js_code: str):
        """Execute JavaScript code in the web view"""
        if self.map_view:
            self.map_view.page().runJavaScript(js_code)

    def showEvent(self, event):
        """Ensure map is properly sized when dialog is shown"""
        super().showEvent(event)
        # Invalidate map size after a short delay
        if self.map_view:
            self.run_javascript("setTimeout(function() { if (map) map.invalidateSize(); }, 100);")

    def closeEvent(self, event):
        """Clean up temporary files when closing"""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.unlink(self.temp_file_path)
            except Exception:
                pass
        super().closeEvent(event)