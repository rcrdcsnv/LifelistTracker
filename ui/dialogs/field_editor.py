# ui/dialogs/field_editor.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QComboBox, QCheckBox, QDialogButtonBox,
                               QGridLayout, QSpinBox, QFrame, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QMessageBox)


class FieldEditorDialog(QDialog):
    """Dialog for creating or editing a custom field"""

    def __init__(self, parent=None, field_data=None):
        super().__init__(parent)

        self.field_data = field_data or {}
        self.setWindowTitle("Custom Field Editor")

        self._setup_ui()
        self._load_field_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Create grid layout for form
        form_layout = QGridLayout()

        # Field name
        form_layout.addWidget(QLabel("Field Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter field name")
        form_layout.addWidget(self.name_edit, 0, 1)

        # Field type
        form_layout.addWidget(QLabel("Field Type:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["text", "number", "date", "boolean", "choice", "rating"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form_layout.addWidget(self.type_combo, 1, 1)

        # Required checkbox
        form_layout.addWidget(QLabel("Required:"), 2, 0)
        self.required_check = QCheckBox()
        form_layout.addWidget(self.required_check, 2, 1)

        layout.addLayout(form_layout)

        # Options container (shown only for certain types)
        self.options_frame = QFrame()
        self.options_layout = QVBoxLayout(self.options_frame)

        # Choice options
        self.choice_frame = QFrame()
        choice_layout = QVBoxLayout(self.choice_frame)

        choice_layout.addWidget(QLabel("Options:"))

        self.options_table = QTableWidget(0, 2)
        self.options_table.setHorizontalHeaderLabels(["Label", "Value"])
        self.options_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.options_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        choice_layout.addWidget(self.options_table)

        choice_buttons = QHBoxLayout()

        self.add_option_btn = QPushButton("Add Option")
        self.add_option_btn.clicked.connect(self._add_option)
        choice_buttons.addWidget(self.add_option_btn)

        self.remove_option_btn = QPushButton("Remove Option")
        self.remove_option_btn.clicked.connect(self._remove_option)
        choice_buttons.addWidget(self.remove_option_btn)

        choice_layout.addLayout(choice_buttons)

        # Rating options
        self.rating_frame = QFrame()
        rating_layout = QGridLayout(self.rating_frame)

        rating_layout.addWidget(QLabel("Maximum Rating:"), 0, 0)
        self.max_rating_spin = QSpinBox()
        self.max_rating_spin.setMinimum(1)
        self.max_rating_spin.setMaximum(10)
        self.max_rating_spin.setValue(5)
        rating_layout.addWidget(self.max_rating_spin, 0, 1)

        # Add options containers to layout
        self.options_layout.addWidget(self.choice_frame)
        self.options_layout.addWidget(self.rating_frame)

        layout.addWidget(self.options_frame)

        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # Initially hide options
        self.options_frame.hide()
        self.choice_frame.hide()
        self.rating_frame.hide()

    def _load_field_data(self):
        """Load existing field data if editing"""
        if not self.field_data:
            return

        # Set basic fields
        self.name_edit.setText(self.field_data.get("name", ""))

        type_index = self.type_combo.findText(self.field_data.get("type", "text"))
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)

        self.required_check.setChecked(bool(self.field_data.get("required", False)))

        # Load options if present
        options = self.field_data.get("options", {})
        if options and isinstance(options, dict):
            field_type = self.field_data.get("type", "")

            if field_type == "choice":
                # Load choice options
                choice_options = options.get("options", [])
                self.options_table.setRowCount(len(choice_options))

                for i, option in enumerate(choice_options):
                    if isinstance(option, dict):
                        label_item = QTableWidgetItem(option.get("label", ""))
                        value_item = QTableWidgetItem(option.get("value", ""))
                    else:
                        label_item = QTableWidgetItem(str(option))
                        value_item = QTableWidgetItem(str(option))

                    self.options_table.setItem(i, 0, label_item)
                    self.options_table.setItem(i, 1, value_item)

            elif field_type == "rating":
                # Load rating options
                max_rating = options.get("max", 5)
                self.max_rating_spin.setValue(max_rating)

    def _on_type_changed(self, field_type):
        """Handle field type change"""
        # Show/hide options based on type
        if field_type in ["choice", "rating"]:
            self.options_frame.show()
            self.choice_frame.setVisible(field_type == "choice")
            self.rating_frame.setVisible(field_type == "rating")
        else:
            self.options_frame.hide()

    def _add_option(self):
        """Add a new choice option"""
        row = self.options_table.rowCount()
        self.options_table.insertRow(row)

        label_item = QTableWidgetItem(f"Option {row + 1}")
        value_item = QTableWidgetItem(f"option_{row + 1}")

        self.options_table.setItem(row, 0, label_item)
        self.options_table.setItem(row, 1, value_item)

        # Select the newly added item for editing
        self.options_table.selectRow(row)
        self.options_table.editItem(label_item)

    def _remove_option(self):
        """Remove selected choice option"""
        selected_rows = self.options_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        self.options_table.removeRow(row)

    def accept(self):
        """Handle dialog acceptance"""
        # Validate input
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Field name is required.")
            return

        field_type = self.type_combo.currentText()

        # Validate options for choice type
        if field_type == "choice" and self.options_table.rowCount() == 0:
            QMessageBox.warning(self, "Validation Error", "Choice fields must have at least one option.")
            return

        super().accept()

    def get_field_data(self):
        """Get the field data from the dialog"""
        field_data = {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "required": 1 if self.required_check.isChecked() else 0,
            "options": None
        }

        # Add type-specific options
        if field_data["type"] == "choice":
            options = []
            for row in range(self.options_table.rowCount()):
                label = self.options_table.item(row, 0).text().strip()
                value = self.options_table.item(row, 1).text().strip() or label.lower().replace(" ", "_")

                options.append({
                    "label": label,
                    "value": value
                })

            field_data["options"] = {"options": options}

        elif field_data["type"] == "rating":
            field_data["options"] = {"max": self.max_rating_spin.value()}

        return field_data