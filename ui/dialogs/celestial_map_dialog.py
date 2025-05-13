from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QDialogButtonBox)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u


class CelestialMapDialog(QDialog):
    """Dialog for displaying celestial objects on star chart"""

    def __init__(self, parent=None, db_manager=None, lifelist_id=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.observations = []

        self.setWindowTitle("Celestial Map")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._load_observations()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Control panel
        controls = QHBoxLayout()

        controls.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["All Sky", "Northern Hemisphere", "Southern Hemisphere"])
        self.view_combo.currentIndexChanged.connect(self._update_map)
        controls.addWidget(self.view_combo)

        controls.addStretch()

        # Export button
        self.export_btn = QPushButton("Save Map")
        self.export_btn.clicked.connect(self._save_map)
        controls.addWidget(self.export_btn)

        layout.addLayout(controls)

        # Map figure
        self.figure = plt.figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_observations(self):
        """Load astronomical observations with coordinates"""
        if not self.lifelist_id:
            return

        with self.db_manager.session_scope() as session:
            from db.repositories import ObservationRepository

            # Get all observations for this lifelist
            all_observations = ObservationRepository.get_observations(session, self.lifelist_id)

            # Filter for those with RA/Dec coordinates
            for obs in all_observations:
                # Look for Right Ascension and Declination in custom fields
                ra = dec = None
                for cf in obs.custom_fields:
                    if cf.field.field_name == "Right Ascension":
                        ra = cf.value
                    elif cf.field.field_name == "Declination":
                        dec = cf.value

                if ra and dec:
                    try:
                        # Parse coordinates
                        coord = SkyCoord(ra=ra, dec=dec, unit=(u.hourangle, u.deg))

                        # Add to list with key info
                        self.observations.append({
                            'name': obs.entry_name,
                            'ra': coord.ra.degree,  # Store as degrees for plotting
                            'dec': coord.dec.degree,
                            'tier': obs.tier
                        })
                    except Exception as e:
                        print(f"Error parsing coordinates for {obs.entry_name}: {e}")

        # Update the map
        self._update_map()

    def _update_map(self):
        """Update the star map"""
        self.figure.clear()

        # Get selected view
        view = self.view_combo.currentText()

        ax = self.figure.add_subplot(111, projection='aitoff')

        # Convert RA from degrees to radians and shift range from [0, 360] to [-π, π]
        if self.observations:
            ra_rad = np.array([(obs['ra'] / 180.0 * np.pi) - np.pi for obs in self.observations])
            dec_rad = np.array([obs['dec'] / 180.0 * np.pi for obs in self.observations])

            # Plot points
            ax.grid(True)
            ax.scatter(ra_rad, dec_rad, s=50, c='red', alpha=0.7)

            # Add labels for each point
            for i, obs in enumerate(self.observations):
                ax.text(ra_rad[i], dec_rad[i], obs['name'], fontsize=8,
                        ha='right', va='bottom', alpha=0.8)

        # Set labels and title
        ax.set_xticklabels(['14h', '16h', '18h', '20h', '22h', '0h', '2h', '4h', '6h', '8h', '10h'])
        ax.set_title(f"Celestial Map - {view}")

        self.canvas.draw()

    def _save_map(self):
        """Save the map as an image file"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Celestial Map",
            "",
            "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)"
        )

        if file_path:
            self.figure.savefig(file_path, bbox_inches='tight')