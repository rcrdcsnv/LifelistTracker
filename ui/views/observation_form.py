# ui/views/observation_form.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QGridLayout,
                               QLineEdit, QDateEdit, QComboBox, QTextEdit,
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPixmap
from pathlib import Path
import json
from datetime import datetime


class ObservationForm(QWidget):
    """Widget for adding or editing an observation"""

    def __init__(self, main_window, photo_manager):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.db_manager
        self.photo_manager = photo_manager

        # State variables
        self.current_lifelist_id = None
        self.current_observation_id = None
        self.entry_term = "item"
        self.observation_term = "entry"

        # Photo management
        self.photos = []  # List of photo info dicts
        self.images = []  # References to QPixmap objects

        # Form fields
        self.entry_name_edit = None
        self.date_edit = None
        self.location_edit = None
        self.latitude_edit = None
        self.longitude_edit = None
        self.tier_combo = None
        self.notes_edit = None
        self.custom_field_widgets = {}  # Maps field_id to widget
        self.tags_container = None
        self.photos_container = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)

        # Header with title and buttons
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)

        self.back_button = QPushButton("Cancel")
        self.back_button.clicked.connect(self._cancel)
        header_layout.addWidget(self.back_button)

        self.title_label = QLabel("Add New Entry")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_observation)
        header_layout.addWidget(self.save_button)

        layout.addWidget(header_frame)

        # Create scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)

        scroll_area.setWidget(self.form_widget)
        layout.addWidget(scroll_area)

        # Create form sections
        self._create_basic_fields()
        self._create_custom_fields_section()
        self._create_tags_section()
        self._create_photos_section()

        # Add some space at the bottom
        self.form_layout.addStretch()

    def _create_basic_fields(self):
        """Create the basic form fields"""
        basic_frame = QFrame()
        basic_layout = QGridLayout(basic_frame)

        # Entry name field
        basic_layout.addWidget(QLabel("Entry Name:"), 0, 0)
        self.entry_name_edit = QLineEdit()
        basic_layout.addWidget(self.entry_name_edit, 0, 1)

        # Date field
        basic_layout.addWidget(QLabel("Observation Date:"), 1, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        basic_layout.addWidget(self.date_edit, 1, 1)

        # Location field
        basic_layout.addWidget(QLabel("Location:"), 2, 0)
        self.location_edit = QLineEdit()
        basic_layout.addWidget(self.location_edit, 2, 1)

        # Coordinates fields
        coords_layout = QHBoxLayout()
        self.latitude_edit = QLineEdit()
        self.latitude_edit.setPlaceholderText("Latitude")
        coords_layout.addWidget(self.latitude_edit)

        self.longitude_edit = QLineEdit()
        self.longitude_edit.setPlaceholderText("Longitude")
        coords_layout.addWidget(self.longitude_edit)

        basic_layout.addWidget(QLabel("Coordinates:"), 3, 0)
        basic_layout.addLayout(coords_layout, 3, 1)

        # Tier field
        basic_layout.addWidget(QLabel("Tier:"), 4, 0)
        self.tier_combo = QComboBox()
        basic_layout.addWidget(self.tier_combo, 4, 1)

        # Notes field
        basic_layout.addWidget(QLabel("Notes:"), 5, 0, Qt.AlignTop)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)
        basic_layout.addWidget(self.notes_edit, 5, 1)

        self.form_layout.addWidget(basic_frame)

    def _create_custom_fields_section(self):
        """Create the custom fields section"""
        self.custom_fields_frame = QFrame()
        self.custom_fields_layout = QVBoxLayout(self.custom_fields_frame)

        self.custom_fields_label = QLabel("Custom Fields")
        self.custom_fields_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.custom_fields_layout.addWidget(self.custom_fields_label)

        # Custom fields will be added dynamically when loading a lifelist

        self.form_layout.addWidget(self.custom_fields_frame)

    def _create_tags_section(self):
        """Create the tags section"""
        self.tags_frame = QFrame()
        self.tags_layout = QVBoxLayout(self.tags_frame)

        self.tags_label = QLabel("Tags")
        self.tags_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.tags_layout.addWidget(self.tags_label)

        # Add tag controls
        tag_controls = QFrame()
        tag_controls_layout = QHBoxLayout(tag_controls)

        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Enter tag")
        tag_controls_layout.addWidget(self.tag_edit)

        self.tag_category_combo = QComboBox()
        self.tag_category_combo.setPlaceholderText("Category (optional)")
        self.tag_category_combo.setEditable(True)
        tag_controls_layout.addWidget(self.tag_category_combo)

        add_tag_button = QPushButton("Add Tag")
        add_tag_button.clicked.connect(self._add_tag)
        tag_controls_layout.addWidget(add_tag_button)

        self.tags_layout.addWidget(tag_controls)

        # Container for tag labels
        self.tags_container = QFrame()
        self.tags_container_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.addWidget(self.tags_container)

        self.form_layout.addWidget(self.tags_frame)

        # Current tags
        self.current_tags = []  # List of (name, category) tuples

    def _create_photos_section(self):
        """Create the photos section"""
        self.photos_frame = QFrame()
        self.photos_layout = QVBoxLayout(self.photos_frame)

        self.photos_label = QLabel("Photos")
        self.photos_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.photos_layout.addWidget(self.photos_label)

        # Add photo button
        add_photo_button = QPushButton("Add Photos")
        add_photo_button.clicked.connect(self._add_photos)
        self.photos_layout.addWidget(add_photo_button)

        # Container for photo thumbnails
        self.photos_container = QFrame()
        self.photos_container_layout = QHBoxLayout(self.photos_container)
        self.photos_layout.addWidget(self.photos_container)

        self.form_layout.addWidget(self.photos_frame)

    def load_form(self, lifelist_id, observation_id=None, entry_name=None):
        """
        Load the form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation to edit (None for new)
            entry_name: Optional entry name to pre-fill
        """
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = observation_id
        self.photos = []
        self.images = []
        self.current_tags = []

        # Get lifelist info to determine terminology
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist = LifelistRepository.get_lifelist(session, lifelist_id)

            if not lifelist:
                QMessageBox.warning(self, "Error", "Lifelist not found")
                return

            lifelist_type = lifelist[4] if lifelist else ""

            # Get terminology
            from config import Config
            config = Config.load()
            self.entry_term = config.get_entry_term(lifelist_type)
            self.observation_term = config.get_observation_term(lifelist_type)

            # Update title
            if observation_id:
                self.title_label.setText(f"Edit {self.observation_term.capitalize()}")
            else:
                self.title_label.setText(f"Add New {self.observation_term.capitalize()}")

            # Update field labels
            self._update_field_labels()

            # Load tiers
            tiers = LifelistRepository.get_lifelist_tiers(session, lifelist_id)
            self.tier_combo.clear()
            self.tier_combo.addItems(tiers)

            # Load tag categories
            self._load_tag_categories(session)

            # Load custom fields
            self._load_custom_fields(session, lifelist_id)

            # If editing an existing observation, load its data
            if observation_id:
                self._load_observation_data(session, observation_id)
            elif entry_name:
                # Pre-fill entry name
                self.entry_name_edit.setText(entry_name)

    def _update_field_labels(self):
        """Update field labels with correct terminology"""
        # Nothing to do here in this stub implementation
        pass

    def _load_tag_categories(self, session):
        """Load available tag categories"""
        # Get all tags
        all_tags = session.query(self.db_manager.engine.models.Tag).all()

        # Extract unique categories
        categories = list(set(tag.category for tag in all_tags if tag.category))

        # Update combobox
        self.tag_category_combo.clear()
        self.tag_category_combo.addItem("")  # Empty option
        self.tag_category_combo.addItems(sorted(categories))

    def _load_custom_fields(self, session, lifelist_id):
        """Load custom fields for the lifelist"""
        # Clear existing custom fields
        for widget in list(self.custom_field_widgets.values()):
            widget.setParent(None)
        self.custom_field_widgets = {}

        # Get custom fields
        custom_fields = session.query(
            self.db_manager.engine.models.CustomField
        ).filter_by(lifelist_id=lifelist_id).order_by(
            self.db_manager.engine.models.CustomField.display_order
        ).all()

        if not custom_fields:
            self.custom_fields_frame.hide()
            return

        self.custom_fields_frame.show()

        # Create field widgets
        for field in custom_fields:
            # Create label
            label = QLabel(f"{field.field_name}:")

            # Create widget based on field type
            if field.field_type == "text":
                widget = QLineEdit()
            elif field.field_type == "number":
                widget = QLineEdit()
                widget.setValidator(QDoubleValidator())
            elif field.field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
            elif field.field_type == "boolean":
                widget = QCheckBox()
            elif field.field_type == "choice":
                widget = QComboBox()
                # Add options
                options = []
                if field.field_options:
                    try:
                        if isinstance(field.field_options, str):
                            options_data = json.loads(field.field_options)
                        else:
                            options_data = field.field_options

                        if isinstance(options_data, dict) and "options" in options_data:
                            options = options_data["options"]
                    except Exception:
                        pass

                widget.addItem("")  # Empty option
                for option in options:
                    if isinstance(option, dict):
                        widget.addItem(option.get("label", option.get("value", "")))
            else:
                # Default to text input for unknown types
                widget = QLineEdit()

            # Create container
            field_frame = QFrame()
            field_layout = QHBoxLayout(field_frame)
            field_layout.addWidget(label)
            field_layout.addWidget(widget)

            # Add to form
            self.custom_fields_layout.addWidget(field_frame)

            # Store widget reference
            self.custom_field_widgets[field.id] = widget

    def _load_observation_data(self, session, observation_id):
        """Load data for an existing observation"""
        # Get the observation
        observation = session.query(
            self.db_manager.engine.models.Observation
        ).filter_by(id=observation_id).first()

        if not observation:
            QMessageBox.warning(self, "Error", "Observation not found")
            return

        # Fill basic fields
        self.entry_name_edit.setText(observation.entry_name)

        if observation.observation_date:
            date = QDate.fromString(observation.observation_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
            self.date_edit.setDate(date)

        if observation.location:
            self.location_edit.setText(observation.location)

        if observation.latitude is not None:
            self.latitude_edit.setText(str(observation.latitude))

        if observation.longitude is not None:
            self.longitude_edit.setText(str(observation.longitude))

        if observation.tier:
            index = self.tier_combo.findText(observation.tier)
            if index >= 0:
                self.tier_combo.setCurrentIndex(index)

        if observation.notes:
            self.notes_edit.setText(observation.notes)

        # Fill custom field values
        for field_value in observation.custom_fields:
            field_id = field_value.field_id
            if field_id in self.custom_field_widgets:
                widget = self.custom_field_widgets[field_id]
                value = field_value.value

                if isinstance(widget, QLineEdit):
                    widget.setText(value or "")
                elif isinstance(widget, QDateEdit) and value:
                    try:
                        date = QDate.fromString(value, "yyyy-MM-dd")
                        widget.setDate(date)
                    except Exception:
                        pass
                elif isinstance(widget, QComboBox) and value:
                    index = widget.findText(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value == "1")

        # Load tags
        for tag in observation.tags:
            self.current_tags.append((tag.name, tag.category))

        self._update_tags_display()

        # Load photos
        for photo in observation.photos:
            self.photos.append({
                "id": photo.id,
                "path": photo.file_path,
                "is_primary": photo.is_primary
            })

        self._update_photos_display()

    def _add_tag(self):
        """Add a tag to the current observation"""
        tag_name = self.tag_edit.text().strip()
        tag_category = self.tag_category_combo.currentText().strip()

        if not tag_name:
            return

        # Check if tag already exists
        for existing_name, existing_category in self.current_tags:
            if existing_name.lower() == tag_name.lower() and existing_category == tag_category:
                return

        # Add the tag
        self.current_tags.append((tag_name, tag_category))

        # Clear the inputs
        self.tag_edit.clear()
        self.tag_category_combo.setCurrentIndex(0)

        # Update display
        self._update_tags_display()

    def _update_tags_display(self):
        """Update the tags display"""
        # Clear existing tags
        while self.tags_container_layout.count():
            item = self.tags_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Group tags by category
        tags_by_category = {}
        for name, category in self.current_tags:
            key = category or "Uncategorized"
            if key not in tags_by_category:
                tags_by_category[key] = []
            tags_by_category[key].append(name)

        # Add each category
        for category, names in tags_by_category.items():
            category_frame = QFrame()
            category_layout = QVBoxLayout(category_frame)

            # Add category header if not uncategorized
            if category != "Uncategorized":
                category_label = QLabel(category)
                category_label.setStyleSheet("font-weight: bold;")
                category_layout.addWidget(category_label)

            # Add tags
            tags_frame = QFrame()
            tags_layout = QHBoxLayout(tags_frame)

            for name in names:
                tag_frame = QFrame()
                tag_layout = QHBoxLayout(tag_frame)
                tag_layout.setContentsMargins(0, 0, 0, 0)

                tag_label = QLabel(name)
                tag_label.setStyleSheet(
                    "background-color: #3498db; color: white; "
                    "padding: 4px 8px; border-radius: 4px;"
                )
                tag_layout.addWidget(tag_label)

                remove_button = QPushButton("✕")
                remove_button.setMaximumWidth(20)
                remove_button.setMaximumHeight(20)
                remove_button.clicked.connect(
                    lambda checked=False, n=name, c=category: self._remove_tag(n, c)
                )
                tag_layout.addWidget(remove_button)

                tags_layout.addWidget(tag_frame)

            tags_layout.addStretch()
            category_layout.addWidget(tags_frame)

            self.tags_container_layout.addWidget(category_frame)

    def _remove_tag(self, name, category):
        """Remove a tag from the current observation"""
        self.current_tags = [(n, c) for n, c in self.current_tags if n != name or c != category]
        self._update_tags_display()

    def _add_photos(self):
        """Add photos to the observation"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Photos",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if not file_paths:
            return

        # Add the photos
        for path in file_paths:
            # Check if this path is already in the list
            if any(p.get("path") == path for p in self.photos):
                continue

            # Extract EXIF data if possible (just for sake of example)
            lat = lon = taken_date = None
            try:
                from utils.image import extract_exif_data
                lat, lon, taken_date = extract_exif_data(Path(path))
            except Exception:
                pass

            # Add to photos list
            self.photos.append({
                "path": path,
                "is_primary": len(self.photos) == 0,  # First photo is primary by default
                "latitude": lat,
                "longitude": lon,
                "taken_date": taken_date
            })

        # Update display
        self._update_photos_display()

    def _update_photos_display(self):
        """Update the photos display"""
        # Clear existing photos and references
        while self.photos_container_layout.count():
            item = self.photos_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.images = []

        # Add photos
        for i, photo in enumerate(self.photos):
            # Create thumbnail
            try:
                pixmap = QPixmap(photo["path"])
                pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.images.append(pixmap)

                # Create photo frame
                photo_frame = QFrame()
                photo_layout = QVBoxLayout(photo_frame)

                # Photo thumbnail
                thumbnail = QLabel()
                thumbnail.setPixmap(pixmap)
                thumbnail.setAlignment(Qt.AlignCenter)
                photo_layout.addWidget(thumbnail)

                # Primary checkbox
                primary_check = QCheckBox("Primary")
                primary_check.setChecked(photo["is_primary"])
                primary_check.clicked.connect(
                    lambda checked, idx=i: self._set_primary_photo(idx)
                )
                photo_layout.addWidget(primary_check)

                # Remove button
                remove_button = QPushButton("Remove")
                remove_button.clicked.connect(
                    lambda checked=False, idx=i: self._remove_photo(idx)
                )
                photo_layout.addWidget(remove_button)

                self.photos_container_layout.addWidget(photo_frame)
            except Exception as e:
                print(f"Error creating thumbnail: {e}")

    def _set_primary_photo(self, index):
        """Set a photo as the primary photo"""
        for i in range(len(self.photos)):
            self.photos[i]["is_primary"] = (i == index)
        self._update_photos_display()

    def _remove_photo(self, index):
        """Remove a photo"""
        if 0 <= index < len(self.photos):
            was_primary = self.photos[index]["is_primary"]
            self.photos.pop(index)

            # If we removed the primary photo, set a new one
            if was_primary and self.photos:
                self.photos[0]["is_primary"] = True

            self._update_photos_display()

    def _cancel(self):
        """Cancel editing and return to lifelist view"""
        self.main_window.open_lifelist(self.current_lifelist_id)

    def _save_observation(self):
        """Save the observation"""
        # Validate fields
        entry_name = self.entry_name_edit.text().strip()
        if not entry_name:
            QMessageBox.warning(self, "Error", f"{self.entry_term.capitalize()} name is required")
            return

        # Collect data
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        observation_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None

        location = self.location_edit.text().strip() or None

        latitude = self.latitude_edit.text().strip() or None
        if latitude:
            try:
                latitude = float(latitude)
            except ValueError:
                QMessageBox.warning(self, "Error", "Latitude must be a number")
                return

        longitude = self.longitude_edit.text().strip() or None
        if longitude:
            try:
                longitude = float(longitude)
            except ValueError:
                QMessageBox.warning(self, "Error", "Longitude must be a number")
                return

        tier = self.tier_combo.currentText() or None
        notes = self.notes_edit.toPlainText().strip() or None

        # Save to database
        with self.db_manager.session_scope() as session:
            if self.current_observation_id:
                # Update existing observation
                observation = session.query(
                    self.db_manager.engine.models.Observation
                ).filter_by(id=self.current_observation_id).first()

                if not observation:
                    QMessageBox.warning(self, "Error", "Observation not found")
                    return

                # Update fields
                observation.entry_name = entry_name
                observation.observation_date = observation_date
                observation.location = location
                observation.latitude = latitude
                observation.longitude = longitude
                observation.tier = tier
                observation.notes = notes
            else:
                # Create new observation
                observation = self.db_manager.engine.models.Observation(
                    lifelist_id=self.current_lifelist_id,
                    entry_name=entry_name,
                    observation_date=observation_date,
                    location=location,
                    latitude=latitude,
                    longitude=longitude,
                    tier=tier,
                    notes=notes
                )
                session.add(observation)
                session.flush()  # To get the ID

            # Save custom fields
            self._save_custom_fields(session, observation)

            # Save tags
            self._save_tags(session, observation)

            # Save photos
            self._save_photos(session, observation)

            # Commit changes
            session.commit()

        # Return to lifelist view
        QMessageBox.information(self, "Success", f"{self.observation_term.capitalize()} saved successfully")
        self.main_window.open_lifelist(self.current_lifelist_id)

    def _save_custom_fields(self, session, observation):
        """Save custom field values"""
        # This is just a stub function for simplicity
        pass

    def _save_tags(self, session, observation):
        """Save observation tags"""
        # Clear existing tags
        observation.tags = []

        # Add current tags
        for name, category in self.current_tags:
            # Find or create tag
            tag = session.query(
                self.db_manager.engine.models.Tag
            ).filter_by(name=name).first()

            if not tag:
                tag = self.db_manager.engine.models.Tag(
                    name=name,
                    category=category
                )
                session.add(tag)
                session.flush()

            # Add to observation
            observation.tags.append(tag)

    def _save_photos(self, session, observation):
        """Save observation photos"""
        # This is just a stub function for simplicity
        # In a real implementation, we would use the photo_manager
        pass