# ui/dialogs/lifelist_wizard.py
from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QComboBox, QTableWidget,
                               QTableWidgetItem, QPushButton, QHeaderView,
                               QMessageBox, QListWidget, QGroupBox, QAbstractItemView)

from config import Config


class LifelistTypeSelectionPage(QWizardPage):
    """Wizard page for selecting lifelist type"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select Lifelist Type")
        self.setSubTitle("Choose the type of lifelist you want to create")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Type selection combo
        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self.completeChanged)
        layout.addWidget(QLabel("Lifelist Type:"))
        layout.addWidget(self.type_combo)

        # Description label
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_label)

        # Terms group
        terms_group = QGroupBox("Terminology")
        terms_layout = QVBoxLayout(terms_group)

        self.entry_term_label = QLabel("Entry: Item")
        self.observation_term_label = QLabel("Observation: Entry")

        terms_layout.addWidget(self.entry_term_label)
        terms_layout.addWidget(self.observation_term_label)

        layout.addWidget(terms_group)

        # Tier list
        tiers_group = QGroupBox("Default Tiers")
        tiers_layout = QVBoxLayout(tiers_group)

        self.tiers_list = QListWidget()
        tiers_layout.addWidget(self.tiers_list)

        layout.addWidget(tiers_group)

        # Connect signals
        self.type_combo.currentIndexChanged.connect(self._update_type_info)

        # Add spacer
        layout.addStretch()

        # Register fields
        self.registerField("lifelist_type_id*", self.type_combo)

    def initializePage(self):
        """Initialize page contents"""
        self.type_combo.clear()
        self.tiers_list.clear()

        # Get available lifelist types
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist_types = LifelistRepository.get_lifelist_types(session)

            if not lifelist_types:
                # If no types exist, create default types from config
                self._create_default_types(session)
                lifelist_types = LifelistRepository.get_lifelist_types(session)

            # Populate combo box
            for lifelist_type in lifelist_types:
                self.type_combo.addItem(lifelist_type.name, lifelist_type.id)

        if self.type_combo.count() > 0:
            self._update_type_info(0)

    def _create_default_types(self, session):
        """Create default lifelist types from config"""
        from db.models import LifelistType, LifelistTypeTier
        config = Config.load()

        for name, template in config.lifelist_types.templates.items():
            # Check if type already exists
            from db.repositories import LifelistRepository
            existing = LifelistRepository.get_lifelist_type_by_name(session, name)
            if existing:
                continue

            # Create new type
            lifelist_type = LifelistType(
                name=name,
                description=f"A lifelist for tracking {template.entry_term}s",
                icon=""
            )
            session.add(lifelist_type)
            session.flush()  # To get the ID

            # Add tiers
            for i, tier_name in enumerate(template.tiers):
                tier = LifelistTypeTier(
                    lifelist_type_id=lifelist_type.id,
                    tier_name=tier_name,
                    tier_order=i
                )
                session.add(tier)

    def _update_type_info(self, index):
        """Update UI with type information"""
        if index < 0:
            return

        type_id = self.type_combo.itemData(index)

        # Load type details
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist_type = LifelistRepository.get_lifelist_type(session, type_id)

            if not lifelist_type:
                return

            # Update description
            self.description_label.setText(lifelist_type.description or "")

            # Update terminology
            config = Config.load()
            entry_term = config.get_entry_term(lifelist_type.name)
            observation_term = config.get_observation_term(lifelist_type.name)

            self.entry_term_label.setText(f"Entry: {entry_term}")
            self.observation_term_label.setText(f"Observation: {observation_term}")

            # Update tiers list
            self.tiers_list.clear()
            tiers = LifelistRepository.get_default_tiers_for_type(session, type_id)

            for tier in tiers:
                self.tiers_list.addItem(tier)

    def isComplete(self):
        """Check if page input is complete"""
        return self.type_combo.currentIndex() >= 0


class LifelistInfoPage(QWizardPage):
    """Wizard page for entering lifelist basic information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Lifelist Information")
        self.setSubTitle("Enter basic information for your lifelist")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a name for your lifelist")
        self.name_edit.textChanged.connect(self.completeChanged)
        name_layout.addWidget(self.name_edit)

        layout.addLayout(name_layout)

        # Classification field
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Classification (optional):"))
        self.classification_edit = QLineEdit()
        self.classification_edit.setPlaceholderText("E.g., 'eBird', 'Clements', etc.")
        class_layout.addWidget(self.classification_edit)

        layout.addLayout(class_layout)

        # Terminology info
        self.term_label = QLabel("")
        self.term_label.setWordWrap(True)
        layout.addWidget(self.term_label)

        # Add spacer
        layout.addStretch()

        # Register fields
        self.registerField("lifelist_name*", self.name_edit)
        self.registerField("lifelist_classification", self.classification_edit)

    def initializePage(self):
        """Initialize page contents"""
        type_id = self.field("lifelist_type_id")

        # Get type info
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            if lifelist_type := LifelistRepository.get_lifelist_type(
                session, type_id
            ):
                # Get terminology from config
                config = Config.load()
                entry_term = config.get_entry_term(lifelist_type.name)
                observation_term = config.get_observation_term(lifelist_type.name)

                # Update term label
                self.term_label.setText(
                    f"In this lifelist, each entry will be a {entry_term} and "
                    f"each observation will be a {observation_term}."
                )

    def isComplete(self):
        """Check if page input is complete"""
        name = self.name_edit.text().strip()

        # Check if name is not empty
        if not name:
            return False

        # Check if name is unique
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.models import Lifelist
            existing = session.query(Lifelist).filter(Lifelist.name == name).first()

            if existing:
                self.setSubTitle(f"The name '{name}' is already in use. Please choose another name.")
                return False
            else:
                self.setSubTitle("Enter basic information for your lifelist")
                return True


class CustomFieldsPage(QWizardPage):
    """Wizard page for configuring custom fields"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Custom Fields")
        self.setSubTitle("Configure custom fields for your observations")

        # Store custom fields
        self.custom_fields = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Fields table
        self.fields_table = QTableWidget(0, 5)  # rows, columns
        self.fields_table.setHorizontalHeaderLabels(["Name", "Type", "Required", "Order", "Options"])
        self.fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.fields_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(self.fields_table)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Field")
        self.add_btn.clicked.connect(self._add_field)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit Field")
        self.edit_btn.clicked.connect(self._edit_field)
        buttons_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove Field")
        self.remove_btn.clicked.connect(self._remove_field)
        buttons_layout.addWidget(self.remove_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Add spacer
        layout.addStretch()

    def initializePage(self):
        """Initialize page contents"""
        type_id = self.field("lifelist_type_id")

        # Clear existing fields
        self.custom_fields = []
        self.fields_table.setRowCount(0)

        # Load default fields for the type
        config = Config.load()
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist_type = LifelistRepository.get_lifelist_type(session, type_id)

            if lifelist_type:
                default_fields = config.get_default_fields(lifelist_type.name)

                self.custom_fields.extend(
                    {
                        "name": field.name,
                        "type": field.type,
                        "required": field.required,
                        "order": len(self.custom_fields),
                        "options": field.options,
                    }
                    for field in default_fields
                )
        # Update table
        self._update_table()

    def _update_table(self):
        """Update the table with current fields"""
        self.fields_table.setRowCount(len(self.custom_fields))

        for i, field in enumerate(self.custom_fields):
            name_item = QTableWidgetItem(field["name"])
            type_item = QTableWidgetItem(field["type"])
            required_item = QTableWidgetItem("Yes" if field["required"] else "No")
            order_item = QTableWidgetItem(str(field["order"]))

            options = field.get("options")
            options_item = QTableWidgetItem("Yes" if options else "None")

            self.fields_table.setItem(i, 0, name_item)
            self.fields_table.setItem(i, 1, type_item)
            self.fields_table.setItem(i, 2, required_item)
            self.fields_table.setItem(i, 3, order_item)
            self.fields_table.setItem(i, 4, options_item)

    def _add_field(self):
        """Add a new custom field"""
        from ui.dialogs.field_editor import FieldEditorDialog

        dialog = FieldEditorDialog(self)
        if dialog.exec():
            field_data = dialog.get_field_data()
            field_data["order"] = len(self.custom_fields)
            self.custom_fields.append(field_data)
            self._update_table()

    def _edit_field(self):
        """Edit selected custom field"""
        selected_rows = self.fields_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.custom_fields):
            return

        from ui.dialogs.field_editor import FieldEditorDialog

        dialog = FieldEditorDialog(self, self.custom_fields[row])
        if dialog.exec():
            field_data = dialog.get_field_data()
            field_data["order"] = self.custom_fields[row]["order"]
            self.custom_fields[row] = field_data
            self._update_table()

    def _remove_field(self):
        """Remove selected custom field"""
        selected_rows = self.fields_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.custom_fields):
            return

        # Confirm removal
        result = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove the field '{self.custom_fields[row]['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.custom_fields.pop(row)

            # Update orders
            for i, field in enumerate(self.custom_fields):
                field["order"] = i

            self._update_table()


class TiersPage(QWizardPage):
    """Wizard page for configuring lifelist tiers"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Lifelist Tiers")
        self.setSubTitle("Configure tiers for your lifelist")

        # Store tiers
        self.tiers = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Explanation label
        explanation = QLabel(
            "Tiers are categories for your entries that can help you organize them. "
            "For example, in a wildlife lifelist, you might have tiers like 'wild', 'heard', and 'captive'."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # Tiers list
        self.tiers_list = QListWidget()
        self.tiers_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.tiers_list.model().rowsMoved.connect(self._tiers_reordered)
        layout.addWidget(self.tiers_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Tier")
        self.add_btn.clicked.connect(self._add_tier)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit Tier")
        self.edit_btn.clicked.connect(self._edit_tier)
        buttons_layout.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove Tier")
        self.remove_btn.clicked.connect(self._remove_tier)
        buttons_layout.addWidget(self.remove_btn)

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self._reset_tiers)
        buttons_layout.addWidget(self.reset_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Add spacer
        layout.addStretch()

    def initializePage(self):
        """Initialize page contents"""
        type_id = self.field("lifelist_type_id")

        # Clear existing tiers
        self.tiers = []
        self.tiers_list.clear()

        # Load default tiers for the type
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            default_tiers = LifelistRepository.get_default_tiers_for_type(session, type_id)

            self.tiers = default_tiers

        # Update list
        self._update_list()

    def _update_list(self):
        """Update the list with current tiers"""
        self.tiers_list.clear()

        for tier in self.tiers:
            self.tiers_list.addItem(tier)

    def _add_tier(self):
        """Add a new tier"""
        from ui.dialogs.text_input_dialog import TextInputDialog

        dialog = TextInputDialog(self, "Add Tier", "Enter tier name:")
        if dialog.exec():
            tier_name = dialog.get_text().strip()

            if not tier_name:
                return

            # Check if tier already exists
            if tier_name in self.tiers:
                QMessageBox.warning(self, "Duplicate Tier", "This tier already exists.")
                return

            self.tiers.append(tier_name)
            self._update_list()

    def _edit_tier(self):
        """Edit selected tier"""
        selected_items = self.tiers_list.selectedItems()
        if not selected_items:
            return

        index = self.tiers_list.row(selected_items[0])
        if index < 0 or index >= len(self.tiers):
            return

        from ui.dialogs.text_input_dialog import TextInputDialog

        dialog = TextInputDialog(self, "Edit Tier", "Enter tier name:", self.tiers[index])
        if dialog.exec():
            tier_name = dialog.get_text().strip()

            if not tier_name:
                return

            # Check if tier already exists
            if tier_name in self.tiers and tier_name != self.tiers[index]:
                QMessageBox.warning(self, "Duplicate Tier", "This tier already exists.")
                return

            self.tiers[index] = tier_name
            self._update_list()

    def _remove_tier(self):
        """Remove selected tier"""
        selected_items = self.tiers_list.selectedItems()
        if not selected_items:
            return

        index = self.tiers_list.row(selected_items[0])
        if index < 0 or index >= len(self.tiers):
            return

        # Confirm removal
        result = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove the tier '{self.tiers[index]}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.tiers.pop(index)
            self._update_list()

    def _reset_tiers(self):
        """Reset tiers to default"""
        # Confirm reset
        result = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset tiers to default?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.initializePage()

    def _tiers_reordered(self):
        """Handle tiers reordering"""
        # Update tiers list from current order in the list widget
        new_tiers = []
        for i in range(self.tiers_list.count()):
            new_tiers.append(self.tiers_list.item(i).text())

        self.tiers = new_tiers


class SummaryPage(QWizardPage):
    """Wizard page for showing a summary of the lifelist configuration"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Summary")
        self.setSubTitle("Review your lifelist configuration")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Create labels for summary information
        self.type_label = QLabel()
        self.name_label = QLabel()
        self.classification_label = QLabel()
        self.fields_label = QLabel()
        self.tiers_label = QLabel()

        layout.addWidget(self.type_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.classification_label)
        layout.addWidget(self.fields_label)
        layout.addWidget(self.tiers_label)

        # Add spacer
        layout.addStretch()

    def initializePage(self):
        """Initialize page contents"""
        # Get values from previous pages
        type_id = self.field("lifelist_type_id")
        name = self.field("lifelist_name")
        classification = self.field("lifelist_classification")
        custom_fields = self.wizard().page(2).custom_fields
        tiers = self.wizard().page(3).tiers

        # Get type information
        db_manager = self.wizard().db_manager
        with db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist_type = LifelistRepository.get_lifelist_type(session, type_id)

            if lifelist_type:
                self.type_label.setText(f"<b>Type:</b> {lifelist_type.name}")

        # Update summary labels
        self.name_label.setText(f"<b>Name:</b> {name}")

        if classification:
            self.classification_label.setText(f"<b>Classification:</b> {classification}")
        else:
            self.classification_label.setText("<b>Classification:</b> None")

        fields_text = "<b>Custom Fields:</b>"
        if custom_fields:
            for field in custom_fields:
                required = "Required" if field["required"] else "Optional"
                fields_text += f"<br>- {field['name']} ({field['type']}, {required})"
        else:
            fields_text += " None"

        self.fields_label.setText(fields_text)

        tiers_text = "<b>Tiers:</b>"
        if tiers:
            tiers_text += "<br>" + "<br>".join([f"- {tier}" for tier in tiers])
        else:
            tiers_text += " None"

        self.tiers_label.setText(tiers_text)


class LifelistWizard(QWizard):
    """Wizard for creating a new lifelist"""

    def __init__(self, parent, db_manager):
        super().__init__(parent)

        self.db_manager = db_manager
        self.lifelist_id = None

        self.setWindowTitle("Create New Lifelist")
        self.setWizardStyle(QWizard.ModernStyle)

        # Add pages
        self.addPage(LifelistTypeSelectionPage())
        self.addPage(LifelistInfoPage())
        self.addPage(CustomFieldsPage())
        self.addPage(TiersPage())
        self.addPage(SummaryPage())

        # Set minimum size
        self.setMinimumSize(650, 500)

        # Connect signals
        self.finished.connect(self._on_finished)

    def _on_finished(self, result):
        """Handle wizard completion"""
        if result == QWizard.Accepted:
            self._create_lifelist()

    def _create_lifelist(self):
        """Create the lifelist based on wizard inputs"""
        # Get values
        type_id = self.field("lifelist_type_id")
        name = self.field("lifelist_name")
        classification = self.field("lifelist_classification")
        custom_fields = self.page(2).custom_fields
        tiers = self.page(3).tiers

        try:
            # Create lifelist
            with self.db_manager.session_scope() as session:
                from db.repositories import LifelistRepository
                from db.models import CustomField

                # Create lifelist
                lifelist_id = LifelistRepository.create_lifelist(
                    session,
                    name,
                    type_id,
                    classification
                )

                if not lifelist_id:
                    raise Exception("Failed to create lifelist")

                # Set custom tiers if they differ from default
                default_tiers = LifelistRepository.get_default_tiers_for_type(session, type_id)
                if tiers != default_tiers:
                    LifelistRepository.set_lifelist_tiers(session, lifelist_id, tiers)

                # Add custom fields
                for field in custom_fields:
                    custom_field = CustomField(
                        lifelist_id=lifelist_id,
                        field_name=field["name"],
                        field_type=field["type"],
                        field_options=field["options"],
                        is_required=bool(field["required"]),
                        display_order=field["order"]
                    )
                    session.add(custom_field)

                # Save and store the ID
                session.commit()
                self.lifelist_id = lifelist_id

            QMessageBox.information(
                self,
                "Success",
                f"Lifelist '{name}' created successfully"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create lifelist: {str(e)}"
            )

    def get_lifelist_id(self):
        """Get the ID of the created lifelist"""
        return self.lifelist_id