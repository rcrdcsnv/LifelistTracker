# ui/dialogs/export_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFileDialog, QProgressBar,
                               QDialogButtonBox, QMessageBox, QCheckBox,
                               QGroupBox)
from PySide6.QtCore import QDir
from pathlib import Path


class ExportDialog(QDialog):
    """Dialog for exporting a lifelist to a file"""

    def __init__(self, parent, db_manager, data_service, lifelist_id):
        super().__init__(parent)

        self.db_manager = db_manager
        self.data_service = data_service
        self.lifelist_id = lifelist_id

        self.setWindowTitle("Export Lifelist")
        self.setMinimumWidth(500)

        self.export_dir = None
        self.lifelist_name = ""

        self._setup_ui()
        self._load_lifelist_info()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Lifelist info
        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        # Export directory selection
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Export Directory:"))

        self.dir_label = QLabel("No directory selected")
        self.dir_label.setStyleSheet("font-style: italic;")
        dir_layout.addWidget(self.dir_label, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.browse_btn)

        layout.addLayout(dir_layout)

        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)

        # Include photos
        self.photos_check = QCheckBox("Include photos")
        self.photos_check.setChecked(True)
        options_layout.addWidget(self.photos_check)

        layout.addWidget(options_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._export_lifelist)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Disable OK button until directory is selected
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def _load_lifelist_info(self):
        """Load information about the lifelist"""
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            if lifelist := LifelistRepository.get_lifelist(
                session, self.lifelist_id
            ):
                self.lifelist_name = lifelist[1]
                lifelist_type = lifelist[4] or "Unknown"

                self.info_label.setText(f"Exporting <b>{self.lifelist_name}</b> (Type: {lifelist_type})")

    def _browse_dir(self):
        """Show file dialog to select export directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            QDir.homePath(),
            QFileDialog.ShowDirsOnly
        )

        if dir_path:
            self.export_dir = dir_path
            self.dir_label.setText(str(Path(dir_path)))

            # Enable OK button
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def _export_lifelist(self):
        """Export the lifelist"""
        if not self.export_dir:
            QMessageBox.warning(self, "Error", "Please select an export directory")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Exporting lifelist...")

        # Disable buttons during export
        self.button_box.setEnabled(False)
        self.browse_btn.setEnabled(False)

        try:
            # Export lifelist
            with self.db_manager.session_scope() as session:
                success = self.data_service.export_lifelist(
                    session,
                    self.lifelist_id,
                    self.export_dir,
                    self.photos_check.isChecked()
                )

                if success:
                    # Construct exported path for display
                    export_path = Path(self.export_dir) / f"{self.lifelist_name}"

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Lifelist exported successfully to:\n{export_path}"
                    )
                    self.accept()
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Failed to export lifelist"
                    )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to export lifelist: {str(e)}"
            )

        finally:
            # Restore UI state
            self.progress_bar.setVisible(False)
            self.button_box.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.status_label.setText("")


def export_lifelist_dialog(parent, db_manager, data_service, lifelist_id):
    """Show the export lifelist dialog"""
    dialog = ExportDialog(parent, db_manager, data_service, lifelist_id)
    dialog.exec()