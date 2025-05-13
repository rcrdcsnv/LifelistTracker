from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QDialogButtonBox)


class SkyCoordinatesDialog(QDialog):
    """Dialog for entering celestial coordinates (RA/Dec)"""

    def __init__(self, parent=None, ra=None, dec=None):
        super().__init__(parent)

        self.ra = ra
        self.dec = dec

        self.setWindowTitle("Enter Sky Coordinates")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Enter the Right Ascension (RA) and Declination (Dec) coordinates.\n"
            "RA format: HH:MM:SS.S (hours, minutes, seconds)\n"
            "Dec format: +/-DD:MM:SS.S (degrees, minutes, seconds)"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # RA input
        ra_layout = QHBoxLayout()
        ra_layout.addWidget(QLabel("RA:"))
        self.ra_edit = QLineEdit()
        self.ra_edit.setPlaceholderText("HH:MM:SS.S")
        if self.ra:
            self.ra_edit.setText(self.ra)
        ra_layout.addWidget(self.ra_edit)
        layout.addLayout(ra_layout)

        # Dec input
        dec_layout = QHBoxLayout()
        dec_layout.addWidget(QLabel("Dec:"))
        self.dec_edit = QLineEdit()
        self.dec_edit.setPlaceholderText("+/-DD:MM:SS.S")
        if self.dec:
            self.dec_edit.setText(self.dec)
        dec_layout.addWidget(self.dec_edit)
        layout.addLayout(dec_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_coordinates(self):
        """Get the entered coordinates"""
        return self.ra_edit.text().strip(), self.dec_edit.text().strip()