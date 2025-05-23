# ui/dialogs/base_map_dialog.py
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PySide6.QtCore import QUrl, Signal, QObject, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
import tempfile
import os
import folium
from folium import plugins
from typing import Dict, Any
from config import Config


class MapBridge(QObject):
    """Bridge object for general map interactions"""
    baseLayerChanged = Signal(str)
    fullscreenToggled = Signal(bool)

    @Slot(str)
    def onBaseLayerChanged(self, layer_name):
        """Called when base layer changes in the map"""
        self.baseLayerChanged.emit(layer_name)

    @Slot(bool)
    def toggleFullscreen(self, fullscreen):
        """Called when fullscreen mode should be toggled"""
        self.fullscreenToggled.emit(fullscreen)


class BaseMapDialog(QDialog):
    """Base class for dialogs that use folium maps"""

    # Signal emitted when map is loaded
    map_loaded = Signal()

    def __init__(self, parent=None, title="Map Dialog"):
        super().__init__(parent)

        self.temp_file_path = None
        self.map_view = None
        self.folium_map = None

        # Set up bridge for map interactions
        self.map_bridge = MapBridge()
        self.map_bridge.baseLayerChanged.connect(self._save_preferred_base_layer)
        self.map_bridge.fullscreenToggled.connect(self._toggle_dialog_fullscreen)

        # Create web channel
        self.channel = QWebChannel()
        self.channel.registerObject("mapBridge", self.map_bridge)

        self.setWindowTitle(title)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()

    def _toggle_dialog_fullscreen(self, fullscreen):
        """Toggle fullscreen mode for the dialog"""
        if fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

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

        # Enable fullscreen support
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        self.map_view.page().fullScreenRequested.connect(lambda request: request.accept())

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
            # Set up web channel
            self.map_view.page().setWebChannel(self.channel)
            self.map_loaded.emit()

    def _save_preferred_base_layer(self, layer_name):
        """Save the preferred base layer to config"""
        config = Config.load()
        config.map.preferred_base_layer = layer_name
        config.save()

    def _create_folium_map(self) -> folium.Map:
        """Create a folium map with standard configuration"""
        # Get configuration
        config_data = self.get_map_config()
        config = Config.load()

        # Create base map
        m = folium.Map(
            location=[config_data.get('centerLat', 0.0), config_data.get('centerLon', 0.0)],
            zoom_start=config_data.get('zoom', 5),
            tiles=None  # We'll add tiles manually for better control
        )

        # Add multiple tile layers
        base_layers = self._get_base_layers()
        preferred_layer = getattr(config.map, 'preferred_base_layer', 'OpenStreetMap')

        # Add base layers to map
        layer_added = False
        for layer_name, layer_config in base_layers.items():
            tile_layer = folium.TileLayer(
                tiles=layer_config['url'],
                attr=layer_config['attribution'],
                name=layer_name,
                overlay=False,
                control=True,
                max_zoom=layer_config.get('max_zoom', 19)
            )

            # Add the preferred layer as default, or first one if preferred not found
            if layer_name == preferred_layer or (not layer_added and layer_name == 'OpenStreetMap'):
                layer_added = True
            tile_layer.add_to(m)
        # Add plugins
        plugins.Fullscreen(
            position='topleft',
            title='Toggle fullscreen',
            title_cancel='Exit fullscreen',
            force_separate_button=True
        ).add_to(m)

        # Add measure control for distance/area measurement
        plugins.MeasureControl(
            position='topright',
            primary_length_unit='kilometers',
            secondary_length_unit='miles',
            primary_area_unit='sqkilometers',
            secondary_area_unit='acres'
        ).add_to(m)

        # Add layer control
        folium.LayerControl(
            position='topright',
            collapsed=True
        ).add_to(m)

        # Add scale control
        plugins.LocateControl(
            position='topleft',
            strings={
                'title': 'See current location',
                'popup': 'Your current location'
            }
        ).add_to(m)

        return m

    def _get_base_layers(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for base layers"""
        return {
            'OpenStreetMap': {
                'url': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                'max_zoom': 19
            },
            'Satellite': {
                'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                'attribution': 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                'max_zoom': 18
            },
            'Terrain': {
                'url': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                'attribution': 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
                'max_zoom': 17
            },
            'CartoDB Positron': {
                'url': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                'max_zoom': 19
            },
            'CartoDB Dark': {
                'url': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                'max_zoom': 19
            }
        }

    def _add_custom_javascript(self, m: folium.Map) -> str:
        """Add custom JavaScript for Qt integration"""
        # Base JavaScript for layer change detection and fullscreen handling
        return """
        <script>
        // Set up Qt WebChannel bridge
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.mapBridge = channel.objects.mapBridge;

            // Monitor layer changes
            map.on('baselayerchange', function(e) {
                if (window.mapBridge) {
                    window.mapBridge.onBaseLayerChanged(e.name);
                }
            });

            // Monitor fullscreen changes
            map.on('enterFullscreen', function() {
                if (window.mapBridge) {
                    window.mapBridge.toggleFullscreen(true);
                }
            });

            map.on('exitFullscreen', function() {
                if (window.mapBridge) {
                    window.mapBridge.toggleFullscreen(false);
                }
            });

            // Allow subclasses to add custom initialization
            if (typeof initializeCustomFeatures === 'function') {
                initializeCustomFeatures();
            }
        });

        // Custom features from subclasses
        function initializeCustomFeatures() {
            """ + self.get_custom_javascript() + """
        }
        </script>
        """

    def create_and_load_map(self):
        """Create folium map and load it in the web view"""
        try:
            # Create folium map
            self.folium_map = self._create_folium_map()

            # Add custom features from subclasses
            self.customize_folium_map(self.folium_map)

            # Get HTML representation
            map_html = self.folium_map._repr_html_()

            # Add custom JavaScript for Qt integration
            custom_js = self._add_custom_javascript(self.folium_map)

            # Insert the custom JavaScript before closing body tag
            if '</body>' in map_html:
                map_html = map_html.replace('</body>', custom_js + '\n</body>')
            else:
                map_html += custom_js

            # Clean up previous temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except Exception:
                    pass

            # Create new temp file
            fd, self.temp_file_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(map_html)

            # Load the HTML file
            self.map_view.load(QUrl.fromLocalFile(self.temp_file_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create map: {str(e)}")

    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for the template - Override in subclasses"""
        # Get preferred base layer from config
        config = Config.load()
        preferred_layer = getattr(config.map, "preferred_base_layer", "OpenStreetMap")

        return {
            'centerLat': 0.0,
            'centerLon': 0.0,
            'zoom': 5,
            'preferredBaseLayer': preferred_layer
        }

    def customize_folium_map(self, m: folium.Map):
        """Customize the folium map - Override in subclasses"""
        pass

    def get_custom_javascript(self) -> str:
        """Get custom JavaScript for the map - Override in subclasses"""
        return ""

    def create_map(self):
        """Create the map using folium"""
        self.create_and_load_map()

    def run_javascript(self, js_code: str):
        """Execute JavaScript code in the web view"""
        if self.map_view:
            self.map_view.page().runJavaScript(js_code)

    def set_base_layer(self, layer_name: str):
        """Set the active base layer by name"""
        if self.map_view:
            js = f"""
            // Find and activate the layer
            map.eachLayer(function(layer) {{
                if (layer.options && layer.options.name === '{layer_name}') {{
                    map.addLayer(layer);
                }} else if (layer.options && layer.options.name && !layer.options.overlay) {{
                    map.removeLayer(layer);
                }}
            }});
            """
            self.run_javascript(js)

    def get_current_base_layer(self, callback):
        """Get the current base layer name"""
        if self.map_view:
            js = """
            var activeLayer = null;
            map.eachLayer(function(layer) {
                if (layer.options && layer.options.name && !layer.options.overlay && map.hasLayer(layer)) {
                    activeLayer = layer.options.name;
                }
            });
            activeLayer;
            """
            self.map_view.page().runJavaScript(js, callback)

    def save_preferred_base_layer(self, layer_name: str):
        """Save the preferred base layer to application config"""
        config = Config.load()
        if not hasattr(config.map, 'preferred_base_layer'):
            # Add the attribute if it doesn't exist
            setattr(config.map, 'preferred_base_layer', layer_name)
        else:
            # Update the existing attribute
            config.map.preferred_base_layer = layer_name
        config.save()

    def load_preferred_base_layer(self):
        """Load the preferred base layer from application config"""
        config = Config.load()
        preferred_layer = getattr(config.map, 'preferred_base_layer', 'OpenStreetMap')
        self.set_base_layer(preferred_layer)

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