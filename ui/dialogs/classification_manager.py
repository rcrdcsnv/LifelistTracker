# ui/dialogs/classification_manager.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QListWidget, QListWidgetItem,
                               QDialogButtonBox, QComboBox, QFileDialog,
                               QTreeWidget, QTreeWidgetItem, QTabWidget,
                               QGroupBox, QGridLayout, QMessageBox,
                               QProgressBar, QTableWidget,
                               QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from pathlib import Path
import csv


class FieldMappingDialog(QDialog):
    """Dialog for mapping CSV fields to database fields"""

    def __init__(self, parent, csv_headers):
        super().__init__(parent)

        self.csv_headers = csv_headers
        self.field_mappings = {}

        self.setWindowTitle("Map CSV Fields")
        self.setMinimumWidth(500)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Explanation label
        explanation = QLabel(
            "Map CSV fields to database fields. For each database field, "
            "select the corresponding CSV field."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # Create grid layout for mapping fields
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("<b>Database Field</b>"), 0, 0)
        grid_layout.addWidget(QLabel("<b>CSV Field</b>"), 0, 1)

        # Database fields and their descriptions
        db_fields = [
            ("name", "Name (required)"),
            ("alternate_name", "Alternate Name"),
            ("category", "Category"),
            ("code", "Code"),
            ("rank", "Rank"),
            ("parent_id", "Parent ID")
        ]

        self.mapping_combos = {}

        for i, (field_key, field_desc) in enumerate(db_fields):
            # Add field label
            grid_layout.addWidget(QLabel(field_desc), i + 1, 0)

            # Add combo box for CSV field
            combo = QComboBox()
            combo.addItem("-- Not Mapped --", None)
            for header in self.csv_headers:
                combo.addItem(header, header)

            # Pre-select if CSV field matches database field
            for j, header in enumerate(self.csv_headers):
                if header.lower() == field_key.lower():
                    combo.setCurrentIndex(j + 1)
                    break

            grid_layout.addWidget(combo, i + 1, 1)

            self.mapping_combos[field_key] = combo

        layout.addLayout(grid_layout)

        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        """Handle dialog acceptance"""
        # Check if name field is mapped
        name_combo = self.mapping_combos["name"]
        if name_combo.currentData() is None:
            QMessageBox.warning(
                self,
                "Missing Required Field",
                "The 'Name' field must be mapped to a CSV field."
            )
            return

        # Save mappings
        for field_key, combo in self.mapping_combos.items():
            csv_field = combo.currentData()
            if csv_field:
                self.field_mappings[field_key] = csv_field

        super().accept()

    def get_field_mappings(self):
        """Get the field mappings"""
        return self.field_mappings


class ClassificationEntryModel:
    """Model for storing classification entries"""

    def __init__(self, name, category=None, parent=None):
        self.name = name
        self.category = category
        self.parent = parent
        self.children = []


class ClassificationImportDialog(QDialog):
    """Dialog for importing a classification from a CSV file"""

    def __init__(self, parent, db_manager, lifelist_id, entry_term="entry"):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.entry_term = entry_term

        self.csv_path = None
        self.csv_headers = []
        self.field_mappings = {}
        self.csv_preview = None

        self.setWindowTitle("Import Classification")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("CSV File:"))

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-style: italic;")
        file_layout.addWidget(self.file_label, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_csv)
        file_layout.addWidget(self.browse_btn)

        layout.addLayout(file_layout)

        # Classification details
        details_group = QGroupBox("Classification Details")
        details_layout = QGridLayout(details_group)

        details_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QComboBox()
        self.name_edit.setEditable(True)
        self.name_edit.addItems(["Clements", "IOC", "ABA", "AOS", "eBird", "Custom"])
        details_layout.addWidget(self.name_edit, 0, 1)

        details_layout.addWidget(QLabel("Version:"), 1, 0)
        self.version_edit = QComboBox()
        self.version_edit.setEditable(True)
        self.version_edit.addItems(["2023", "2022", "2021", "2020"])
        details_layout.addWidget(self.version_edit, 1, 1)

        details_layout.addWidget(QLabel("Source:"), 2, 0)
        self.source_edit = QComboBox()
        self.source_edit.setEditable(True)
        self.source_edit.addItems(["Official", "Custom", "Web"])
        details_layout.addWidget(self.source_edit, 2, 1)

        layout.addWidget(details_group)

        # CSV preview
        preview_group = QGroupBox("CSV Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        preview_layout.addWidget(self.preview_table)

        # Field mapping button
        self.mapping_btn = QPushButton("Map Fields...")
        self.mapping_btn.clicked.connect(self._show_field_mapping)
        self.mapping_btn.setEnabled(False)
        preview_layout.addWidget(self.mapping_btn)

        layout.addWidget(preview_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._import_classification)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        layout.addWidget(self.button_box)

    def _browse_csv(self):
        """Show file dialog to select CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Classification CSV File",
            "",
            "CSV Files (*.csv)"
        )

        if file_path:
            self.csv_path = file_path
            self.file_label.setText(Path(file_path).name)

            # Load CSV preview
            self._load_csv_preview()

    def _load_csv_preview(self):
        """Load CSV file preview"""
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                self.csv_headers = headers

                # Show up to 10 rows in preview
                rows = []
                for i, row in enumerate(reader):
                    rows.append(row)
                    if i >= 9:  # 10 rows including header
                        break

            # Update preview table
            self.preview_table.clear()
            self.preview_table.setRowCount(len(rows))
            self.preview_table.setColumnCount(len(headers))
            self.preview_table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    if j < len(headers):  # Protect against malformed rows
                        self.preview_table.setItem(i, j, QTableWidgetItem(cell))

            # Adjust column widths
            for j in range(len(headers)):
                self.preview_table.horizontalHeader().setSectionResizeMode(j, QHeaderView.ResizeToContents)

            # Enable field mapping
            self.mapping_btn.setEnabled(True)

            # Try to automatically detect some field mappings
            self._detect_field_mappings()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")

            # Reset state
            self.csv_path = None
            self.file_label.setText("No file selected")
            self.preview_table.clear()
            self.mapping_btn.setEnabled(False)
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def _detect_field_mappings(self):
        """Try to automatically detect field mappings based on headers"""
        # Common column names for each field
        field_patterns = {
            "name": ["name", "species", "scientific name", "scientific_name", "taxon", "entry"],
            "alternate_name": ["common name", "common_name", "alternate", "alt name", "alt_name", "vernacular"],
            "category": ["category", "family", "order", "class", "group", "taxon"],
            "code": ["code", "id", "identifier", "species code", "species_code", "alpha code"],
            "rank": ["rank", "taxonomic rank", "level", "tax_rank"],
            "parent_id": ["parent", "parent_id", "parent id", "parent code"]
        }

        # Detect mappings
        mappings = {}

        for field, patterns in field_patterns.items():
            for header in self.csv_headers:
                header_lower = header.lower()

                for pattern in patterns:
                    if pattern in header_lower:
                        mappings[field] = header
                        break

                if field in mappings:
                    break

        self.field_mappings = mappings

        # Enable import if name is mapped
        self.button_box.button(QDialogButtonBox.Ok).setEnabled("name" in mappings)

    def _show_field_mapping(self):
        """Show dialog to map CSV fields to database fields"""
        dialog = FieldMappingDialog(self, self.csv_headers)

        # Pre-fill with detected mappings
        if dialog.exec():
            self.field_mappings = dialog.get_field_mappings()

            # Enable import if name is mapped
            self.button_box.button(QDialogButtonBox.Ok).setEnabled("name" in self.field_mappings)

    def _import_classification(self):
        """Import the classification"""
        if not self.csv_path or not self.field_mappings or "name" not in self.field_mappings:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select a CSV file and map at least the 'Name' field."
            )
            return

        # Get classification details
        name = self.name_edit.currentText().strip()
        version = self.version_edit.currentText().strip()
        source = self.source_edit.currentText().strip()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Please enter a classification name.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Disable controls during import
        self.button_box.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.mapping_btn.setEnabled(False)

        try:
            # Import classification
            from services.data_service import DataService

            with self.db_manager.session_scope() as session:
                data_service = self.parent().main_window.data_service

                success, count = data_service.import_classification(
                    session,
                    self.lifelist_id,
                    name,
                    self.csv_path,
                    self.field_mappings,
                    version,
                    source
                )

                if success:
                    QMessageBox.information(
                        self,
                        "Import Successful",
                        f"Successfully imported {count} {self.entry_term}s."
                    )
                    self.accept()
                else:
                    QMessageBox.critical(
                        self,
                        "Import Failed",
                        "Failed to import classification."
                    )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import classification: {str(e)}")

        finally:
            # Restore controls
            self.progress_bar.setVisible(False)
            self.button_box.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.mapping_btn.setEnabled(True)


class ClassificationManagerDialog(QDialog):
    """Dialog for managing classifications"""

    def __init__(self, parent, db_manager, lifelist_id, entry_term="entry"):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = lifelist_id
        self.entry_term = entry_term

        self.classifications = []
        self.current_classification = None

        self.setWindowTitle("Classification Manager")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._load_classifications()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.classifications_tab = QWidget()
        self.entries_tab = QWidget()

        self.tab_widget.addTab(self.classifications_tab, "Classifications")
        self.tab_widget.addTab(self.entries_tab, "Browse Entries")

        layout.addWidget(self.tab_widget)

        # Classifications tab
        self._setup_classifications_tab()

        # Entries tab
        self._setup_entries_tab()

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _setup_classifications_tab(self):
        """Set up the classifications tab"""
        layout = QVBoxLayout(self.classifications_tab)

        # Classifications list
        list_layout = QHBoxLayout()

        list_frame = QVBoxLayout()
        list_frame.addWidget(QLabel("Available Classifications:"))

        self.classifications_list = QListWidget()
        self.classifications_list.setMinimumWidth(300)
        self.classifications_list.itemSelectionChanged.connect(self._on_classification_selected)
        list_frame.addWidget(self.classifications_list)

        list_layout.addLayout(list_frame)

        # Classification details
        details_frame = QVBoxLayout()
        details_frame.addWidget(QLabel("Classification Details:"))

        self.details_tree = QTreeWidget()
        self.details_tree.setHeaderLabels(["Property", "Value"])
        self.details_tree.setMinimumWidth(300)
        self.details_tree.setRootIsDecorated(False)
        self.details_tree.setColumnWidth(0, 150)
        details_frame.addWidget(self.details_tree)

        list_layout.addLayout(details_frame)

        layout.addLayout(list_layout)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import Classification...")
        self.import_btn.clicked.connect(self._import_classification)
        buttons_layout.addWidget(self.import_btn)

        self.set_active_btn = QPushButton("Set as Active")
        self.set_active_btn.clicked.connect(self._set_active_classification)
        self.set_active_btn.setEnabled(False)
        buttons_layout.addWidget(self.set_active_btn)

        self.delete_btn = QPushButton("Delete Classification")
        self.delete_btn.clicked.connect(self._delete_classification)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    def _setup_entries_tab(self):
        """Set up the entries tab"""
        layout = QVBoxLayout(self.entries_tab)

        # Classification selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Classification:"))

        self.classification_combo = QComboBox()
        self.classification_combo.currentIndexChanged.connect(self._load_classification_entries)
        selector_layout.addWidget(self.classification_combo)

        selector_layout.addStretch()

        # Search field
        selector_layout.addWidget(QLabel("Search:"))

        self.search_edit = QComboBox()
        self.search_edit.setEditable(True)
        self.search_edit.setMinimumWidth(200)
        selector_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._search_entries)
        selector_layout.addWidget(self.search_btn)

        layout.addLayout(selector_layout)

        # Entries tree
        self.entries_tree = QTreeWidget()
        self.entries_tree.setHeaderLabels([f"{self.entry_term.capitalize()} Name", "Category", "Code"])
        self.entries_tree.setAlternatingRowColors(True)
        self.entries_tree.setColumnWidth(0, 300)
        self.entries_tree.setColumnWidth(1, 200)
        layout.addWidget(self.entries_tree)

    def _load_classifications(self):
        """Load classifications from database"""
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            # Get classifications for this lifelist
            self.classifications = ClassificationRepository.get_classifications(session, self.lifelist_id)

            # Update classifications list
            self.classifications_list.clear()
            self.classification_combo.clear()

            for classification in self.classifications:
                item = QListWidgetItem(classification.name)
                item.setData(Qt.UserRole, classification.id)

                if classification.is_active:
                    item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
                    item.setText(f"{classification.name} (Active)")
                    self.current_classification = classification

                self.classifications_list.addItem(item)
                self.classification_combo.addItem(classification.name, classification.id)

            # Select active classification in combo
            if self.current_classification:
                index = self.classification_combo.findData(self.current_classification.id)
                if index >= 0:
                    self.classification_combo.setCurrentIndex(index)

            # Load entries for selected classification
            self._load_classification_entries()

    def _on_classification_selected(self):
        """Handle classification selection"""
        selected_items = self.classifications_list.selectedItems()

        if not selected_items:
            self.details_tree.clear()
            self.set_active_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        classification_id = selected_items[0].data(Qt.UserRole)

        # Get classification details
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            classification = ClassificationRepository.get_classification(session, classification_id)

            if not classification:
                return

            # Update details tree
            self.details_tree.clear()

            # Add details
            details = [
                ("Name", classification.name),
                ("Version", classification.version or "N/A"),
                ("Source", classification.source or "N/A"),
                ("Active", "Yes" if classification.is_active else "No"),
                ("Created", classification.created_at.strftime("%Y-%m-%d") if classification.created_at else "Unknown"),
                ("Entries", str(ClassificationRepository.count_entries(session, classification_id)))
            ]

            for key, value in details:
                item = QTreeWidgetItem([key, value])
                self.details_tree.addTopLevelItem(item)

            # Enable/disable buttons
            self.set_active_btn.setEnabled(not classification.is_active)
            self.delete_btn.setEnabled(not classification.is_active)

    def _load_classification_entries(self):
        """Load entries for the selected classification"""
        classification_id = self.classification_combo.currentData()

        if not classification_id:
            self.entries_tree.clear()
            return

        # Get entries
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            entries = ClassificationRepository.get_entries(session, classification_id)

            # Create entry models
            entry_models = {}
            root_entries = []

            for entry in entries:
                model = ClassificationEntryModel(
                    entry.name,
                    entry.category
                )
                entry_models[entry.id] = model

                if entry.parent_id and entry.parent_id in entry_models:
                    model.parent = entry_models[entry.parent_id]
                    entry_models[entry.parent_id].children.append(model)
                else:
                    root_entries.append(model)

            # Build tree
            self.entries_tree.clear()

            for model in root_entries:
                self._add_entry_to_tree(model, None)

            # Expand top-level items
            for i in range(min(10, self.entries_tree.topLevelItemCount())):
                self.entries_tree.topLevelItem(i).setExpanded(True)

            # Add recent searches
            self.search_edit.clear()
            recent_searches = ["", "Eagle", "Owl", "Warbler", "Thrush", "Hawk", "Sparrow"]  # Example recent searches
            self.search_edit.addItems(recent_searches)

    def _add_entry_to_tree(self, model, parent_item):
        """Add an entry model to the tree"""
        if parent_item:
            item = QTreeWidgetItem(parent_item)
        else:
            item = QTreeWidgetItem(self.entries_tree)

        item.setText(0, model.name)
        item.setText(1, model.category or "")

        # Add children
        for child in model.children:
            self._add_entry_to_tree(child, item)

        return item

    def _search_entries(self):
        """Search entries in the current classification"""
        search_text = self.search_edit.currentText().strip().lower()

        if not search_text:
            self._load_classification_entries()
            return

        classification_id = self.classification_combo.currentData()

        if not classification_id:
            return

        # Search entries
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            entries = ClassificationRepository.search_entries(session, classification_id, search_text)

            # Display results
            self.entries_tree.clear()

            for entry in entries:
                item = QTreeWidgetItem(self.entries_tree)
                item.setText(0, entry.name)
                item.setText(1, entry.category or "")
                item.setText(2, entry.code or "")

        # Add to recent searches if not already there
        if search_text and self.search_edit.findText(search_text) < 0:
            self.search_edit.addItem(search_text)

    def _import_classification(self):
        """Show dialog to import a classification"""
        dialog = ClassificationImportDialog(self, self.db_manager, self.lifelist_id, self.entry_term)

        if dialog.exec() == QDialog.Accepted:
            # Reload classifications
            self._load_classifications()

    def _set_active_classification(self):
        """Set the selected classification as active"""
        selected_items = self.classifications_list.selectedItems()

        if not selected_items:
            return

        classification_id = selected_items[0].data(Qt.UserRole)

        # Set as active
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            success = ClassificationRepository.set_active_classification(
                session, self.lifelist_id, classification_id
            )

            if success:
                session.commit()

                # Reload classifications
                self._load_classifications()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to set classification as active."
                )

    def _delete_classification(self):
        """Delete the selected classification"""
        selected_items = self.classifications_list.selectedItems()

        if not selected_items:
            return

        classification_id = selected_items[0].data(Qt.UserRole)
        classification_name = selected_items[0].text()

        # Check if active
        if "Active" in classification_name:
            QMessageBox.warning(
                self,
                "Cannot Delete Active Classification",
                "The active classification cannot be deleted."
            )
            return

        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the classification '{classification_name}'?\n\n"
            "This will permanently delete all entries in this classification.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result != QMessageBox.Yes:
            return

        # Delete classification
        with self.db_manager.session_scope() as session:
            from db.repositories import ClassificationRepository

            success = ClassificationRepository.delete_classification(session, classification_id)

            if success:
                session.commit()

                # Reload classifications
                self._load_classifications()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to delete classification."
                )