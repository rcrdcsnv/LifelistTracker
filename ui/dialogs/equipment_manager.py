from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QComboBox, QLineEdit, QDateEdit, QFormLayout,
                               QTabWidget, QMessageBox, QDoubleSpinBox,
                               QCheckBox, QHeaderView, QDialogButtonBox, QWidget)
from PySide6.QtCore import Qt, QDate


class EquipmentDialog(QDialog):
    """Dialog for adding or editing equipment"""

    def __init__(self, parent=None, db_manager=None, equipment_id=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.equipment_id = equipment_id

        self.setWindowTitle("Equipment Details")
        self.setMinimumWidth(500)

        self._setup_ui()
        self._load_equipment()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Basic information
        form_layout = QFormLayout()

        # Name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)

        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Telescope", "Camera", "Mount", "Eyepiece",
            "Filter", "Barlow/Reducer", "Focuser", "Other"
        ])
        self.type_combo.setEditable(True)
        self.type_combo.currentTextChanged.connect(self._type_changed)
        form_layout.addRow("Type:", self.type_combo)

        # Dynamic type-specific fields section
        self.type_fields_widget = QTabWidget()

        # Telescope tab
        telescope_widget = QWidget()
        telescope_layout = QFormLayout(telescope_widget)

        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(0, 10000)
        self.aperture_spin.setSuffix(" mm")
        telescope_layout.addRow("Aperture:", self.aperture_spin)

        self.focal_length_spin = QDoubleSpinBox()
        self.focal_length_spin.setRange(0, 100000)
        self.focal_length_spin.setSuffix(" mm")
        telescope_layout.addRow("Focal Length:", self.focal_length_spin)

        self.focal_ratio_spin = QDoubleSpinBox()
        self.focal_ratio_spin.setRange(0, 100)
        self.focal_ratio_spin.setDecimals(1)
        self.focal_ratio_spin.setSingleStep(0.1)
        telescope_layout.addRow("Focal Ratio (f/):", self.focal_ratio_spin)

        self.type_fields_widget.addTab(telescope_widget, "Telescope Details")

        # Camera tab
        camera_widget = QWidget()
        camera_layout = QFormLayout(camera_widget)

        self.sensor_type_edit = QLineEdit()
        camera_layout.addRow("Sensor Type:", self.sensor_type_edit)

        self.pixel_size_spin = QDoubleSpinBox()
        self.pixel_size_spin.setRange(0, 100)
        self.pixel_size_spin.setDecimals(2)
        self.pixel_size_spin.setSingleStep(0.1)
        self.pixel_size_spin.setSuffix(" µm")
        camera_layout.addRow("Pixel Size:", self.pixel_size_spin)

        self.resolution_edit = QLineEdit()
        self.resolution_edit.setPlaceholderText("e.g., 4656 x 3520")
        camera_layout.addRow("Resolution:", self.resolution_edit)

        self.type_fields_widget.addTab(camera_widget, "Camera Details")

        # General tab
        general_widget = QWidget()
        general_layout = QFormLayout(general_widget)

        self.details_edit = QLineEdit()
        general_layout.addRow("Details:", self.details_edit)

        self.purchase_date_edit = QDateEdit()
        self.purchase_date_edit.setCalendarPopup(True)
        general_layout.addRow("Purchase Date:", self.purchase_date_edit)

        self.type_fields_widget.addTab(general_widget, "General Info")

        form_layout.addRow(self.type_fields_widget)

        # Notes
        self.notes_edit = QLineEdit()
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._save_equipment)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _type_changed(self, type_text):
        """Update visible tabs based on equipment type"""
        if type_text == "Telescope":
            self.type_fields_widget.setCurrentIndex(0)
        elif type_text == "Camera":
            self.type_fields_widget.setCurrentIndex(1)
        else:
            self.type_fields_widget.setCurrentIndex(2)

    def _load_equipment(self):
        """Load equipment data if editing"""
        if not self.equipment_id:
            return

        with self.db_manager.session_scope() as session:
            from db.repositories import EquipmentRepository
            equipment = EquipmentRepository.get_equipment(session, self.equipment_id)

            if not equipment:
                return

            # Set basic fields
            self.name_edit.setText(equipment.name)

            if equipment.type:
                # Find or add type
                index = self.type_combo.findText(equipment.type)
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                else:
                    self.type_combo.setCurrentText(equipment.type)

            # Set type-specific fields
            if equipment.aperture:
                self.aperture_spin.setValue(equipment.aperture)

            if equipment.focal_length:
                self.focal_length_spin.setValue(equipment.focal_length)

            if equipment.focal_ratio:
                self.focal_ratio_spin.setValue(equipment.focal_ratio)

            if equipment.sensor_type:
                self.sensor_type_edit.setText(equipment.sensor_type)

            if equipment.pixel_size:
                self.pixel_size_spin.setValue(equipment.pixel_size)

            if equipment.resolution:
                self.resolution_edit.setText(equipment.resolution)

            if equipment.details:
                self.details_edit.setText(equipment.details)

            if equipment.purchase_date:
                date = QDate.fromString(equipment.purchase_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                self.purchase_date_edit.setDate(date)

            if equipment.notes:
                self.notes_edit.setText(equipment.notes)

    def _save_equipment(self):
        """Save equipment data"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Equipment name is required")
            return

        equipment_type = self.type_combo.currentText().strip()

        # Collect data
        data = {
            'name': name,
            'type': equipment_type,
            'notes': self.notes_edit.text().strip() or None
        }

        # Add type-specific data
        if equipment_type == "Telescope":
            data.update({
                'aperture': self.aperture_spin.value() if self.aperture_spin.value() > 0 else None,
                'focal_length': self.focal_length_spin.value() if self.focal_length_spin.value() > 0 else None,
                'focal_ratio': self.focal_ratio_spin.value() if self.focal_ratio_spin.value() > 0 else None
            })
        elif equipment_type == "Camera":
            data.update({
                'sensor_type': self.sensor_type_edit.text().strip() or None,
                'pixel_size': self.pixel_size_spin.value() if self.pixel_size_spin.value() > 0 else None,
                'resolution': self.resolution_edit.text().strip() or None
            })

        # Add general data
        data.update({
            'details': self.details_edit.text().strip() or None,
            'purchase_date': None if self.purchase_date_edit.date().isNull() else self.purchase_date_edit.date().toPython()
        })

        # Save to database
        with self.db_manager.session_scope() as session:
            from db.repositories import EquipmentRepository

            if self.equipment_id:
                # Update existing
                if EquipmentRepository.update_equipment(session, self.equipment_id, **data):
                    session.commit()
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Failed to update equipment")
            else:
                # Create new
                if equipment_id := EquipmentRepository.create_equipment(session, **data):
                    session.commit()
                    self.equipment_id = equipment_id
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Failed to create equipment")


class EquipmentManagerDialog(QDialog):
    """Dialog for managing equipment"""

    def __init__(self, parent=None, db_manager=None, for_selection=False, observation_id=None):
        super().__init__(parent)

        self.db_manager = db_manager
        self.for_selection = for_selection
        self.observation_id = observation_id
        self.selected_equipment = []

        self.setWindowTitle("Equipment Manager")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_equipment()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Filter controls
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Filter by type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types")
        self.type_filter.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.type_filter)

        filter_layout.addStretch()

        # Add equipment button
        self.add_btn = QPushButton("Add Equipment")
        self.add_btn.clicked.connect(self._add_equipment)
        filter_layout.addWidget(self.add_btn)

        layout.addLayout(filter_layout)

        # Equipment table
        self.equipment_table = QTableWidget(0, 6)  # rows, columns
        self.equipment_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Details", "Purchase Date", "Notes", ""]
        )
        self.equipment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.equipment_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.equipment_table.setColumnWidth(5, 80)
        layout.addWidget(self.equipment_table)

        # Buttons
        buttons_layout = QHBoxLayout()

        if self.for_selection:
            # Selection mode - show select/cancel
            select_button = QPushButton("Select Equipment")
            select_button.clicked.connect(self._select_equipment)
            buttons_layout.addWidget(select_button)

            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(self.reject)
            buttons_layout.addWidget(cancel_button)
        else:
            # Management mode - show close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(self.accept)
            buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)

    def _load_equipment(self):
        """Load equipment data using repository pattern"""
        with self.db_manager.session_scope() as session:
            from db.repositories import EquipmentRepository

            # Get all equipment as dictionaries
            all_equipment = EquipmentRepository.get_all_equipment_for_display(session)

            # Populate type filter
            self.type_filter.clear()
            self.type_filter.addItem("All Types")

            equipment_types = sorted(set(e['type'] for e in all_equipment if e['type']))
            self.type_filter.addItems(equipment_types)

            # Get selected equipment for observation if applicable
            if self.observation_id:
                equipment_data = EquipmentRepository.get_observation_equipment_for_display(
                    session, self.observation_id
                )
                self.selected_equipment = [e['id'] for e in equipment_data]

            # Display equipment
            self._populate_table(all_equipment)

    def _populate_table(self, equipment_list):
        """Populate the equipment table with dictionaries instead of ORM objects"""
        self.equipment_table.setRowCount(0)

        # Convert to dictionaries if equipment_list contains ORM objects
        equipment_data = []
        for equipment in equipment_list:
            if hasattr(equipment, '__dict__'):
                # It's an ORM object, convert to dict
                data = {
                    'id': equipment.id,
                    'name': equipment.name,
                    'type': equipment.type or "",
                    'aperture': equipment.aperture,
                    'focal_length': equipment.focal_length,
                    'focal_ratio': equipment.focal_ratio,
                    'sensor_type': equipment.sensor_type,
                    'pixel_size': equipment.pixel_size,
                    'resolution': equipment.resolution,
                    'details': equipment.details or "",
                    'purchase_date': equipment.purchase_date,
                    'notes': equipment.notes or ""
                }
                equipment_data.append(data)
            else:
                # Already a dict
                equipment_data.append(equipment)

        for row, equipment in enumerate(equipment_data):
            self.equipment_table.insertRow(row)

            # Set data
            name_item = QTableWidgetItem(equipment['name'])
            name_item.setData(Qt.UserRole, equipment['id'])
            self.equipment_table.setItem(row, 0, name_item)

            self.equipment_table.setItem(row, 1, QTableWidgetItem(equipment['type']))

            # Create details text based on equipment type
            details = ""
            if equipment['type'] == "Telescope":
                if equipment['aperture']:
                    details += f"{equipment['aperture']}mm aperture, "
                if equipment['focal_length']:
                    details += f"{equipment['focal_length']}mm FL, "
                if equipment['focal_ratio']:
                    details += f"f/{equipment['focal_ratio']}"
            elif equipment['type'] == "Camera":
                if equipment['sensor_type']:
                    details += f"{equipment['sensor_type']}, "
                if equipment['resolution']:
                    details += f"{equipment['resolution']}, "
                if equipment['pixel_size']:
                    details += f"{equipment['pixel_size']}µm pixels"
            else:
                details = equipment['details'] or ""

            self.equipment_table.setItem(row, 2, QTableWidgetItem(details.strip(", ")))

            # Purchase date
            date_text = ""
            if equipment['purchase_date']:
                if hasattr(equipment['purchase_date'], 'strftime'):
                    date_text = equipment['purchase_date'].strftime("%Y-%m-%d")
                else:
                    date_text = str(equipment['purchase_date'])
            self.equipment_table.setItem(row, 3, QTableWidgetItem(date_text))

            # Notes
            self.equipment_table.setItem(row, 4, QTableWidgetItem(equipment['notes']))

            # Action buttons container
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)

            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(60)
            edit_btn.clicked.connect(lambda checked=False, eq_id=equipment.id: self._edit_equipment(eq_id))
            btn_layout.addWidget(edit_btn)

            if self.for_selection:
                # Checkbox for selection
                select_check = QCheckBox()
                select_check.setChecked(equipment.id in self.selected_equipment)
                select_check.stateChanged.connect(
                    lambda state, eq_id=equipment.id: self._toggle_selection(eq_id, state)
                )
                btn_layout.addWidget(select_check)
            else:
                # Delete button
                delete_btn = QPushButton("X")
                delete_btn.setFixedWidth(20)
                delete_btn.clicked.connect(lambda checked=False, eq_id=equipment.id: self._delete_equipment(eq_id))
                btn_layout.addWidget(delete_btn)

            self.equipment_table.setCellWidget(row, 5, btn_widget)

    def _apply_filter(self):
        """Apply type filter"""
        selected_type = self.type_filter.currentText()

        with self.db_manager.session_scope() as session:
            from db.repositories import EquipmentRepository

            if selected_type == "All Types":
                equipment = EquipmentRepository.get_all_equipment(session)
            else:
                equipment = EquipmentRepository.get_equipment_by_type(session, selected_type)

            self._populate_table(equipment)

    def _add_equipment(self):
        """Show dialog to add new equipment"""
        dialog = EquipmentDialog(self, self.db_manager)
        if dialog.exec():
            self._load_equipment()

    def _edit_equipment(self, equipment_id):
        """Show dialog to edit equipment"""
        dialog = EquipmentDialog(self, self.db_manager, equipment_id)
        if dialog.exec():
            self._load_equipment()

    def _delete_equipment(self, equipment_id):
        """Delete an equipment item"""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this equipment?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            with self.db_manager.session_scope() as session:
                from db.repositories import EquipmentRepository
                if EquipmentRepository.delete_equipment(session, equipment_id):
                    session.commit()
                    self._load_equipment()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete equipment")

    def _toggle_selection(self, equipment_id, state):
        """Toggle equipment selection"""
        if state == Qt.Checked:
            if equipment_id not in self.selected_equipment:
                self.selected_equipment.append(equipment_id)
        else:
            if equipment_id in self.selected_equipment:
                self.selected_equipment.remove(equipment_id)

    def _select_equipment(self):
        """Finish selection and return selected equipment IDs"""
        self.accept()

    def get_selected_equipment(self):
        """Get the selected equipment IDs"""
        return self.selected_equipment