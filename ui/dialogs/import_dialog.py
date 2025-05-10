# ui/dialogs/import_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFileDialog, QProgressBar,
                               QDialogButtonBox, QMessageBox, QCheckBox)
from PySide6.QtCore import QDir
from pathlib import Path


class ImportDialog(QDialog):
    """Dialog for importing a lifelist from a file"""

    def __init__(self, parent, db_manager, data_service):
        super().__init__(parent)

        self.db_manager = db_manager
        self.data_service = data_service

        self.setWindowTitle("Import Lifelist")
        self.setMinimumWidth(500)

        self.json_path = None
        self.photos_dir = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # JSON file selection
        json_layout = QHBoxLayout()
        json_layout.addWidget(QLabel("JSON File:"))

        self.json_path_label = QLabel("No file selected")
        self.json_path_label.setStyleSheet("font-style: italic;")
        json_layout.addWidget(self.json_path_label, 1)

        self.browse_json_btn = QPushButton("Browse...")
        self.browse_json_btn.clicked.connect(self._browse_json)
        json_layout.addWidget(self.browse_json_btn)

        layout.addLayout(json_layout)

        # Photos directory selection
        photos_layout = QHBoxLayout()
        photos_layout.addWidget(QLabel("Photos Directory:"))

        self.photos_dir_label = QLabel("No directory selected")
        self.photos_dir_label.setStyleSheet("font-style: italic;")
        photos_layout.addWidget(self.photos_dir_label, 1)

        self.browse_photos_btn = QPushButton("Browse...")
        self.browse_photos_btn.clicked.connect(self._browse_photos_dir)
        photos_layout.addWidget(self.browse_photos_btn)

        layout.addLayout(photos_layout)

        # Auto-detect photos checkbox
        self.auto_detect_check = QCheckBox("Auto-detect photos directory from JSON path")
        self.auto_detect_check.setChecked(True)
        self.auto_detect_check.stateChanged.connect(self._on_auto_detect_changed)
        layout.addWidget(self.auto_detect_check)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._import_lifelist)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Initialize state
        self._on_auto_detect_changed()

    def _browse_json(self):
        """Show file dialog to select JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lifelist JSON File",
            QDir.homePath(),
            "JSON Files (*.json)"
        )

        if file_path:
            self.json_path = file_path
            self.json_path_label.setText(Path(file_path).name)

            # If auto-detect is enabled, update photos directory
            if self.auto_detect_check.isChecked():
                self._auto_detect_photos_dir()

    def _browse_photos_dir(self):
        """Show file dialog to select photos directory"""
        if dir_path := QFileDialog.getExistingDirectory(
            self,
            "Select Photos Directory",
            QDir.homePath(),
            QFileDialog.ShowDirsOnly,
        ):
            self.photos_dir = dir_path
            self.photos_dir_label.setText(Path(dir_path).name)

    def _on_auto_detect_changed(self):
        """Handle auto-detect checkbox state change"""
        auto_detect = self.auto_detect_check.isChecked()

        # Enable/disable manual selection
        self.browse_photos_btn.setEnabled(not auto_detect)
        self.photos_dir_label.setEnabled(not auto_detect)

        # Update photos directory if auto-detect is enabled
        if auto_detect and self.json_path:
            self._auto_detect_photos_dir()

    def _auto_detect_photos_dir(self):
        """Auto-detect photos directory based on JSON path"""
        if not self.json_path:
            return

        # Check if "photos" directory exists alongside JSON file
        json_path = Path(self.json_path)
        potential_photos_dir = json_path.parent / "photos"

        if potential_photos_dir.exists() and potential_photos_dir.is_dir():
            self.photos_dir = str(potential_photos_dir)
            self.photos_dir_label.setText(f"{potential_photos_dir.name} (auto-detected)")
        else:
            self.photos_dir = None
            self.photos_dir_label.setText("No photos directory found")

    def _import_lifelist(self):
        """Import the selected lifelist"""
        if not self.json_path:
            QMessageBox.warning(self, "Error", "Please select a JSON file to import")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Importing lifelist...")

        # Disable buttons during import
        self.button_box.setEnabled(False)
        self.browse_json_btn.setEnabled(False)
        self.browse_photos_btn.setEnabled(False)

        try:
            # Import lifelist
            with self.db_manager.session_scope() as session:
                success, message = self.data_service.import_lifelist(
                    session,
                    self.json_path,
                    self.photos_dir
                )

                if success:
                    QMessageBox.information(self, "Success", message)
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import lifelist: {str(e)}")

        finally:
            # Restore UI state
            self.progress_bar.setVisible(False)
            self.button_box.setEnabled(True)
            self.browse_json_btn.setEnabled(True)
            self.browse_photos_btn.setEnabled(not self.auto_detect_check.isChecked())
            self.status_label.setText("")


def import_lifelist_dialog(parent, db_manager, data_service, on_complete=None):
    """Show the import lifelist dialog"""
    dialog = ImportDialog(parent, db_manager, data_service)
    result = dialog.exec()

    if result == QDialog.Accepted and on_complete:
        on_complete()