# ui/views/observation_form.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QGridLayout,
                               QLineEdit, QDateEdit, QDateTimeEdit, QComboBox, QTextEdit,
                               QFileDialog, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, QDate, QDateTime, Signal
from PySide6.QtGui import QPixmap, QDoubleValidator, QTransform
from pathlib import Path
import json
from datetime import datetime
from PIL import Image


# Add the ClickableCoordinateEdit class
class ClickableCoordinateEdit(QLineEdit):
    """Custom QLineEdit that shows a map picker when focused"""

    clicked = Signal()

    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setToolTip(f"Enter {placeholder_text.lower()} or click to select from map")

    def focusInEvent(self, event):
        """Show map picker on focus if field is empty"""
        super().focusInEvent(event)
        if not self.text().strip():
            self.clicked.emit()


class ObservationForm(QWidget):
    """Widget for adding or editing an observation"""

    def __init__(self, main_window, photo_manager):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.db_manager
        self.photo_manager = photo_manager
        self.session_manager = main_window.session_manager

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
        self.ra_edit = None
        self.dec_edit = None
        self.tier_combo = None
        self.notes_edit = None
        self.custom_field_widgets = {}  # Maps field_id to widget
        self.tags_container = None
        self.photos_container = None
        self.selected_equipment_ids = []

        # UI containers that will be shown/hidden based on lifelist type
        self.earth_coords_container = None
        self.sky_coords_container = None
        self.equipment_container = None

        # Current tags
        self.current_tags = []  # List of (name, category) tuples

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
        self.date_edit = QDateTimeEdit()  # Use date time instead of just date
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        basic_layout.addWidget(self.date_edit, 1, 1)

        # Location field
        basic_layout.addWidget(QLabel("Location:"), 2, 0)
        self.location_edit = QLineEdit()
        basic_layout.addWidget(self.location_edit, 2, 1)

        # Create both coordinate sections, but only show the appropriate one
        self._create_earth_coordinates(basic_layout)
        self._create_sky_coordinates(basic_layout)

        # Equipment section (always create it, but only show for astronomy)
        self._create_equipment_section(basic_layout)

        # Tier field
        basic_layout.addWidget(QLabel("Tier:"), 6, 0)
        self.tier_combo = QComboBox()
        basic_layout.addWidget(self.tier_combo, 6, 1)

        # Notes field
        basic_layout.addWidget(QLabel("Notes:"), 7, 0, Qt.AlignTop)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)
        basic_layout.addWidget(self.notes_edit, 7, 1)

        self.form_layout.addWidget(basic_frame)

    def _create_earth_coordinates(self, basic_layout):
        """Create earth coordinate widgets"""
        # Coordinates fields with enhanced UI
        coords_label = QLabel("Earth Coordinates:")
        basic_layout.addWidget(coords_label, 3, 0)

        self.earth_coords_container = QWidget()
        coords_layout = QHBoxLayout(self.earth_coords_container)
        coords_layout.setContentsMargins(0, 0, 0, 0)

        # Use custom clickable coordinate fields
        self.latitude_edit = ClickableCoordinateEdit("Latitude")
        self.latitude_edit.setValidator(QDoubleValidator(-90.0, 90.0, 6))
        self.latitude_edit.clicked.connect(self._get_coordinates_from_map)
        coords_layout.addWidget(self.latitude_edit)

        self.longitude_edit = ClickableCoordinateEdit("Longitude")
        self.longitude_edit.setValidator(QDoubleValidator(-180.0, 180.0, 6))
        self.longitude_edit.clicked.connect(self._get_coordinates_from_map)
        coords_layout.addWidget(self.longitude_edit)

        # Add "Get from map" button
        self.get_from_map_btn = QPushButton("📍 Pick on Map")
        self.get_from_map_btn.clicked.connect(self._get_coordinates_from_map)
        coords_layout.addWidget(self.get_from_map_btn)

        # Add "Clear" button
        self.clear_coords_btn = QPushButton("Clear")
        self.clear_coords_btn.clicked.connect(self._clear_coordinates)
        coords_layout.addWidget(self.clear_coords_btn)

        basic_layout.addWidget(self.earth_coords_container, 3, 1)

    def _create_sky_coordinates(self, basic_layout):
        """Create sky coordinate widgets for astronomy"""
        # Sky coordinates section
        sky_coords_label = QLabel("Sky Coordinates:")
        basic_layout.addWidget(sky_coords_label, 3, 0)

        self.sky_coords_container = QWidget()
        sky_coords_layout = QHBoxLayout(self.sky_coords_container)
        sky_coords_layout.setContentsMargins(0, 0, 0, 0)

        # RA field
        self.ra_edit = QLineEdit()
        self.ra_edit.setPlaceholderText("RA (HH:MM:SS.S)")
        sky_coords_layout.addWidget(self.ra_edit)

        # Dec field
        self.dec_edit = QLineEdit()
        self.dec_edit.setPlaceholderText("Dec (+/-DD:MM:SS.S)")
        sky_coords_layout.addWidget(self.dec_edit)

        # Add "Pick coordinates" button
        self.sky_coords_btn = QPushButton("📡 Enter Coordinates")
        self.sky_coords_btn.clicked.connect(self._get_sky_coordinates)
        sky_coords_layout.addWidget(self.sky_coords_btn)

        basic_layout.addWidget(self.sky_coords_container, 3, 1)

        # Help text
        self.coords_help = QLabel("Right Ascension and Declination for celestial objects")
        self.coords_help.setStyleSheet("color: #666; font-size: 11px;")
        basic_layout.addWidget(self.coords_help, 4, 1)

    def _create_equipment_section(self, basic_layout):
        """Create equipment section for astronomy"""
        equipment_label = QLabel("Equipment:")
        basic_layout.addWidget(equipment_label, 5, 0, Qt.AlignTop)

        self.equipment_container = QWidget()
        equipment_layout = QVBoxLayout(self.equipment_container)

        # Equipment selection display
        self.equipment_display = QLabel("No equipment selected")
        equipment_layout.addWidget(self.equipment_display)

        # Equipment selection button
        self.select_equipment_btn = QPushButton("Select Equipment")
        self.select_equipment_btn.clicked.connect(self._select_equipment)
        equipment_layout.addWidget(self.select_equipment_btn)

        basic_layout.addWidget(self.equipment_container, 5, 1)

    def _get_coordinates_from_map(self):
        """Get coordinates from an interactive map"""
        from ui.dialogs.coordinate_picker import CoordinatePickerDialog

        # Get current coordinates if available
        current_lat = None
        current_lon = None

        try:
            lat_text = self.latitude_edit.text().strip()
            lon_text = self.longitude_edit.text().strip()

            if lat_text and lon_text:
                current_lat = float(lat_text)
                current_lon = float(lon_text)
        except ValueError:
            pass

        # Open coordinate picker dialog
        dialog = CoordinatePickerDialog(self, current_lat, current_lon)

        if dialog.exec():
            lat, lon = dialog.get_coordinates()
            self.latitude_edit.setText(f"{lat:.6f}")
            self.longitude_edit.setText(f"{lon:.6f}")

    def _get_sky_coordinates(self):
        """Open dialog to enter sky coordinates"""
        from ui.dialogs.sky_coordinates_dialog import SkyCoordinatesDialog

        # Get current values if any
        current_ra = self.ra_edit.text() if hasattr(self, 'ra_edit') else None
        current_dec = self.dec_edit.text() if hasattr(self, 'dec_edit') else None

        dialog = SkyCoordinatesDialog(self, current_ra, current_dec)
        if dialog.exec():
            ra, dec = dialog.get_coordinates()

            # Update form fields
            self.ra_edit.setText(ra)
            self.dec_edit.setText(dec)

            # Also update the custom fields if they exist
            for field_id, widget in self.custom_field_widgets.items():
                field_name = None

                # Get field name using repository to avoid detached instance issues
                with self.db_manager.session_scope() as session:
                    from db.models import CustomField
                    field = session.query(CustomField).filter_by(id=field_id).first()
                    if field:
                        field_name = field.field_name

                if field_name == "Right Ascension" and isinstance(widget, QLineEdit):
                    widget.setText(ra)
                elif field_name == "Declination" and isinstance(widget, QLineEdit):
                    widget.setText(dec)

    def _clear_coordinates(self):
        """Clear the coordinate fields"""
        self.latitude_edit.clear()
        self.longitude_edit.clear()

    def _select_equipment(self):
        """Open dialog to select equipment"""
        from ui.dialogs.equipment_manager import EquipmentManagerDialog

        dialog = EquipmentManagerDialog(
            self,
            self.db_manager,
            for_selection=True,
            observation_id=self.current_observation_id
        )

        if dialog.exec():
            self.selected_equipment_ids = dialog.get_selected_equipment()

            # Update display using a fresh session
            with self.db_manager.session_scope() as session:
                from db.repositories import EquipmentRepository
                equipment_list = []

                for eq_id in self.selected_equipment_ids:
                    if equipment := EquipmentRepository.get_equipment(session, eq_id):
                        equipment_list.append(equipment.name)

                if equipment_list:
                    self.equipment_display.setText(", ".join(equipment_list))
                else:
                    self.equipment_display.setText("No equipment selected")

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

    def _create_photos_section(self):
        """Create the photos section"""
        self.photos_frame = QFrame()
        self.photos_layout = QVBoxLayout(self.photos_frame)

        self.photos_label = QLabel("Photos")
        self.photos_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.photos_layout.addWidget(self.photos_label)

        # Photo controls
        photo_controls = QHBoxLayout()

        # Add photo button
        add_photo_button = QPushButton("Add Photos")
        add_photo_button.clicked.connect(self._add_photos)
        photo_controls.addWidget(add_photo_button)

        # Add "Use photo coordinates" button
        self.use_photo_coords_btn = QPushButton("Use Photo Coordinates")
        self.use_photo_coords_btn.clicked.connect(self._use_photo_coordinates)
        self.use_photo_coords_btn.setEnabled(False)  # Disabled until photos with EXIF are available
        photo_controls.addWidget(self.use_photo_coords_btn)

        photo_controls.addStretch()
        self.photos_layout.addLayout(photo_controls)

        # Container for photo thumbnails
        self.photos_container = QFrame()
        self.photos_container_layout = QHBoxLayout(self.photos_container)
        self.photos_layout.addWidget(self.photos_container)

        self.form_layout.addWidget(self.photos_frame)

    def check_if_astronomy_lifelist(self):
        """Check if current lifelist is an astronomy type"""
        if not self.current_lifelist_id:
            return False

        # Use a repository method with fresh session to avoid detached issues
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist = LifelistRepository.get_lifelist(session, self.current_lifelist_id)
            if lifelist and lifelist[4] == "Astronomy":
                return True
        return False

    def _use_photo_coordinates(self):
        """Let user choose which photo coordinates to use"""
        photos_with_coords = [(i, p) for i, p in enumerate(self.photos)
                              if p.get("latitude") is not None and p.get("longitude") is not None]

        if not photos_with_coords:
            QMessageBox.information(self, "No Coordinates",
                                    "None of the photos have GPS coordinates.")
            return

        # If only one photo with coordinates, use it directly
        if len(photos_with_coords) == 1:
            _, photo = photos_with_coords[0]
            self.latitude_edit.setText(str(photo["latitude"]))
            self.longitude_edit.setText(str(photo["longitude"]))
            return

        # Multiple photos with coordinates - let user choose
        from PySide6.QtWidgets import QInputDialog

        photo_choices = []
        for idx, photo in photos_with_coords:
            photo_name = Path(photo["path"]).name
            coords = f"({photo['latitude']:.6f}, {photo['longitude']:.6f})"
            primary = " (Primary)" if photo.get("is_primary", False) else ""
            photo_choices.append(f"{photo_name} {coords}{primary}")

        choice, ok = QInputDialog.getItem(
            self,
            "Select Photo Coordinates",
            "Choose which photo's coordinates to use:",
            photo_choices,
            0,
            False
        )

        if ok and choice:
            selected_idx = photo_choices.index(choice)
            _, photo = photos_with_coords[selected_idx]
            self.latitude_edit.setText(str(photo["latitude"]))
            self.longitude_edit.setText(str(photo["longitude"]))

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
        self.selected_equipment_ids = []

        # Get lifelist info to determine terminology using a fresh session
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

            # Show/hide astronomy-specific fields
            is_astronomy = lifelist_type == "Astronomy"
            if hasattr(self, 'earth_coords_container'):
                self.earth_coords_container.setVisible(not is_astronomy)
            if hasattr(self, 'sky_coords_container'):
                self.sky_coords_container.setVisible(is_astronomy)
            if hasattr(self, 'equipment_container'):
                self.equipment_container.setVisible(is_astronomy)
            if hasattr(self, 'coords_help'):
                self.coords_help.setVisible(is_astronomy)

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
                # Use a repository method to get all observation data at once
                from db.repositories import ObservationRepository

                # Define a custom repository method for UI display
                observation_data = self._get_observation_data_for_display(session, observation_id)

                if observation_data:
                    self._populate_form_from_data(observation_data, is_astronomy)

            elif entry_name:
                # Pre-fill entry name
                self.entry_name_edit.setText(entry_name)

    def _get_observation_data_for_display(self, session, observation_id):
        """Get observation data ready for display, avoiding detached instance issues"""
        from db.models import Observation, ObservationCustomField
        from sqlalchemy.orm import joinedload

        # Load observation with all needed relationships eagerly loaded
        observation = session.query(Observation).filter_by(
            id=observation_id
        ).options(
            joinedload(Observation.custom_fields).joinedload(ObservationCustomField.field),
            joinedload(Observation.tags),
            joinedload(Observation.photos)
        ).first()

        if not observation:
            return None

        # Extract all data while session is active
        result = {
            'id': observation.id,
            'entry_name': observation.entry_name,
            'observation_date': observation.observation_date,
            'location': observation.location,
            'latitude': observation.latitude,
            'longitude': observation.longitude,
            'tier': observation.tier,
            'notes': observation.notes,
            'lifelist_id': observation.lifelist_id,

            # Extract relationships data too
            'custom_fields': [
                {
                    'field_id': cf.field_id,
                    'field_name': cf.field.field_name,
                    'value': cf.value
                }
                for cf in observation.custom_fields
            ],

            'tags': [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'category': tag.category
                }
                for tag in observation.tags
            ],

            'photos': [
                {
                    'id': photo.id,
                    'path': photo.file_path,
                    'is_primary': photo.is_primary
                }
                for photo in observation.photos
            ]
        }

        # For astronomy lifelists, also load equipment
        if self.check_if_astronomy_lifelist():
            from db.repositories import EquipmentRepository
            equipment = EquipmentRepository.get_observation_equipment(session, observation_id)
            result['equipment'] = [
                {
                    'id': eq.id,
                    'name': eq.name,
                    'type': eq.type
                }
                for eq in equipment
            ]

        return result

    def _populate_form_from_data(self, data, is_astronomy):
        """Populate form fields from extracted observation data"""
        # Basic fields
        self.entry_name_edit.setText(data['entry_name'])

        if data['observation_date']:
            date = QDateTime.fromString(
                data['observation_date'].strftime("%Y-%m-%d %H:%M:%S"),
                "yyyy-MM-dd hh:mm:ss"
            )
            self.date_edit.setDateTime(date)

        if data['location']:
            self.location_edit.setText(data['location'])

        # Handle different coordinate types based on lifelist type
        if is_astronomy:
            # For astronomy, get RA/Dec from custom fields
            for field in data['custom_fields']:
                if field['field_name'] == "Right Ascension":
                    self.ra_edit.setText(field['value'] or "")
                elif field['field_name'] == "Declination":
                    self.dec_edit.setText(field['value'] or "")
        else:
            # For regular lifelists, use lat/lon
            if data['latitude'] is not None:
                self.latitude_edit.setText(str(data['latitude']))

            if data['longitude'] is not None:
                self.longitude_edit.setText(str(data['longitude']))

        # Tier
        if data['tier']:
            index = self.tier_combo.findText(data['tier'])
            if index >= 0:
                self.tier_combo.setCurrentIndex(index)

        # Notes
        if data['notes']:
            self.notes_edit.setText(data['notes'])

        # Custom fields
        for field in data['custom_fields']:
            field_id = field['field_id']
            if field_id in self.custom_field_widgets:
                widget = self.custom_field_widgets[field_id]
                value = field['value']

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

        # Tags - extract to simple tuples
        self.current_tags = [(tag['name'], tag['category']) for tag in data['tags']]
        self._update_tags_display()

        # Photos - extract needed info
        self.photos = data['photos']
        self._update_photos_display()

        # Equipment for astronomy
        if is_astronomy and 'equipment' in data:
            self.selected_equipment_ids = [eq['id'] for eq in data['equipment']]

            if hasattr(self, 'equipment_display'):
                if self.selected_equipment_ids:
                    equipment_list = [eq['name'] for eq in data['equipment']]
                    self.equipment_display.setText(", ".join(equipment_list))
                else:
                    self.equipment_display.setText("No equipment selected")

    def _update_field_labels(self):
        """Update field labels with correct terminology"""
        # Nothing to do here in this stub implementation
        pass

    def _load_tag_categories(self, session):
        """Load available tag categories"""
        # Get all tags
        from db.models import Tag
        all_tags = session.query(Tag).all()

        # Extract unique categories
        categories = list({tag.category for tag in all_tags if tag.category})

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
        from db.models import CustomField
        custom_fields = session.query(CustomField).filter_by(
            lifelist_id=lifelist_id
        ).order_by(CustomField.display_order).all()

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

                # For choice fields, only load first N options initially
                if len(options) > 20:
                    for option in options[:20]:
                        if isinstance(option, dict):
                            widget.addItem(option.get("label", ""))

                    widget.addItem("... (load more)")
                    widget.currentTextChanged.connect(
                        lambda text, w=widget, f=field: self._handle_choice_selection(text, w, f)
                    )
                else:
                    # Load all options if few
                    for option in options:
                        if isinstance(option, dict):
                            widget.addItem(option.get("label", ""))
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

    def _handle_choice_selection(self, text, widget, field):
        """Handle selection of choice field with lazy loading"""
        if text == "... (load more)":
            # Remove the placeholder
            widget.removeItem(widget.findText(text))

            # Load remaining options
            options = self._get_field_options(field)
            for option in options[20:]:
                if isinstance(option, dict):
                    widget.addItem(option.get("label", ""))

    def _get_field_options(self, field):
        """Get options for a field"""
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
        return options

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
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.fits *.fit)"
        )

        if not file_paths:
            return

        # Add the photos
        for path in file_paths:
            # Check if this path is already in the list
            if any(p.get("path") == path for p in self.photos):
                continue

            # Extract EXIF data if possible
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

        # Auto-populate coordinates if empty and photo has EXIF data
        self._auto_populate_coordinates()

    def _auto_populate_coordinates(self):
        """Auto-populate observation coordinates from photos if available"""
        # Check if observation coordinates are already set
        if (hasattr(self, 'latitude_edit') and hasattr(self, 'longitude_edit') and
                self.latitude_edit.text().strip() and self.longitude_edit.text().strip()):
            return

        # Find first photo with EXIF coordinates
        for photo in self.photos:
            if photo.get("latitude") is not None and photo.get("longitude") is not None:
                # Ask user if they want to use these coordinates
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Use Photo Coordinates",
                    f"A photo has GPS coordinates ({photo['latitude']:.6f}, {photo['longitude']:.6f}). "
                    f"Would you like to use these for the observation location?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # For regular observations, use lat/lon
                    if hasattr(self, 'latitude_edit') and hasattr(self, 'longitude_edit'):
                        self.latitude_edit.setText(str(photo["latitude"]))
                        self.longitude_edit.setText(str(photo["longitude"]))

                break  # Only ask for the first photo with coordinates

    def _update_photos_display(self):
        """Update the photos display with rotation controls"""
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
                # Load the image
                pixmap = QPixmap(photo["path"])

                # Apply rotation if specified
                rotation = photo.get("rotation", 0)
                if rotation != 0:
                    transform = QTransform().rotate(rotation)
                    pixmap = pixmap.transformed(transform)

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

                # Rotation controls
                rotation_layout = QHBoxLayout()

                rotate_left_btn = QPushButton("↶")  # Counter-clockwise
                rotate_left_btn.setToolTip("Rotate counter-clockwise")
                rotate_left_btn.setMaximumWidth(30)
                rotate_left_btn.clicked.connect(
                    lambda checked=False, idx=i: self._rotate_photo(idx, -90)
                )

                rotate_right_btn = QPushButton("↷")  # Clockwise
                rotate_right_btn.setToolTip("Rotate clockwise")
                rotate_right_btn.setMaximumWidth(30)
                rotate_right_btn.clicked.connect(
                    lambda checked=False, idx=i: self._rotate_photo(idx, 90)
                )

                rotation_layout.addWidget(rotate_left_btn)
                rotation_layout.addWidget(rotate_right_btn)
                photo_layout.addLayout(rotation_layout)

                # Show if photo has GPS coordinates
                if photo.get("latitude") is not None and photo.get("longitude") is not None:
                    gps_label = QLabel("GPS: ✓")
                    gps_label.setStyleSheet("color: green; font-weight: bold;")
                    photo_layout.addWidget(gps_label)

                # Remove button
                remove_button = QPushButton("Remove")
                remove_button.clicked.connect(
                    lambda checked=False, idx=i: self._remove_photo(idx)
                )
                photo_layout.addWidget(remove_button)

                self.photos_container_layout.addWidget(photo_frame)
            except Exception as e:
                print(f"Error creating thumbnail: {e}")

            # Enable/disable "Use Photo Coordinates" button based on available photos with GPS
            photos_with_coords = [p for p in self.photos
                                  if p.get("latitude") is not None and p.get("longitude") is not None]
            self.use_photo_coords_btn.setEnabled(len(photos_with_coords) > 0)

    def _set_primary_photo(self, index):
        """Set a photo as the primary photo"""
        for i in range(len(self.photos)):
            self.photos[i]["is_primary"] = (i == index)
        self._update_photos_display()

        # When setting a new primary photo, offer to update coordinates if they have EXIF data
        if 0 <= index < len(self.photos):
            photo = self.photos[index]
            if photo.get("latitude") is not None and photo.get("longitude") is not None:
                # Ask user if they want to update coordinates to match this photo
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Update Coordinates",
                    f"This photo has GPS coordinates ({photo['latitude']:.6f}, {photo['longitude']:.6f}). "
                    f"Would you like to update the observation coordinates?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # For regular lifelists, update the earth coordinates
                    if not self.check_if_astronomy_lifelist():
                        self.latitude_edit.setText(str(photo["latitude"]))
                        self.longitude_edit.setText(str(photo["longitude"]))

    def _remove_photo(self, index):
        """Remove a photo"""
        if 0 <= index < len(self.photos):
            was_primary = self.photos[index]["is_primary"]
            self.photos.pop(index)

            # If we removed the primary photo, set a new one
            if was_primary and self.photos:
                self.photos[0]["is_primary"] = True

            self._update_photos_display()

    def _rotate_photo(self, index, angle):
        """Rotate a photo by the given angle in degrees"""
        if 0 <= index < len(self.photos):
            # Update rotation value (accumulate rotations)
            current_rotation = self.photos[index].get("rotation", 0)
            new_rotation = (current_rotation + angle) % 360
            self.photos[index]["rotation"] = new_rotation

            # Update display
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
        date_str = self.date_edit.dateTime().toString("yyyy-MM-dd hh:mm:ss")
        observation_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else None

        location = self.location_edit.text().strip() or None

        # Get coordinates based on lifelist type
        latitude = longitude = None
        is_astronomy = self.check_if_astronomy_lifelist()

        if not is_astronomy:
            # For regular lifelists, get latitude/longitude
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

        # Use a fresh session for saving
        with self.db_manager.session_scope() as session:
            from db.models import Observation

            if self.current_observation_id:
                # Update existing observation
                observation = session.query(Observation).filter_by(
                    id=self.current_observation_id
                ).first()

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
                observation = Observation(
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

            # Save equipment if astronomy lifelist
            if is_astronomy and hasattr(self, 'selected_equipment_ids'):
                from db.repositories import EquipmentRepository
                EquipmentRepository.set_observation_equipment(
                    session,
                    observation.id,
                    self.selected_equipment_ids
                )

            # Commit changes
            session.commit()

        # Return to lifelist view
        QMessageBox.information(self, "Success", f"{self.observation_term.capitalize()} saved successfully")
        self.main_window.open_lifelist(self.current_lifelist_id)

    def _save_custom_fields(self, session, observation):
        """Save custom field values"""
        # Get custom field values from form widgets
        field_values = {}

        for field_id, widget in self.custom_field_widgets.items():
            value = None

            # Extract value based on widget type
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
            elif isinstance(widget, QDateEdit):
                value = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QComboBox):
                value = widget.currentText().strip()
            elif isinstance(widget, QCheckBox):
                value = "1" if widget.isChecked() else "0"

            # Store non-empty values
            if value:
                field_values[field_id] = value

        # For astronomy lifelists, also save RA/Dec from the dedicated fields
        if self.check_if_astronomy_lifelist():
            from db.models import CustomField

            # Find the RA and Dec fields
            ra_field = session.query(CustomField).filter_by(
                lifelist_id=self.current_lifelist_id,
                field_name="Right Ascension"
            ).first()

            dec_field = session.query(CustomField).filter_by(
                lifelist_id=self.current_lifelist_id,
                field_name="Declination"
            ).first()

            # Save RA/Dec if fields exist
            if ra_field and hasattr(self, 'ra_edit'):
                ra_value = self.ra_edit.text().strip()
                if ra_value:
                    field_values[ra_field.id] = ra_value

            if dec_field and hasattr(self, 'dec_edit'):
                dec_value = self.dec_edit.text().strip()
                if dec_value:
                    field_values[dec_field.id] = dec_value

        # Use repository to save custom field values
        from db.repositories import ObservationRepository
        ObservationRepository.set_observation_custom_fields(session, observation.id, field_values)

    def _save_tags(self, session, observation):
        """Save observation tags"""
        from db.models import Tag

        # Clear existing tags
        observation.tags = []

        # Add current tags
        for name, category in self.current_tags:
            # Find or create tag
            tag = session.query(Tag).filter_by(name=name).first()

            if not tag:
                tag = Tag(
                    name=name,
                    category=category
                )
                session.add(tag)
                session.flush()

            # Add to observation
            observation.tags.append(tag)

    def _save_photos(self, session, observation):
        """Save observation photos"""
        from db.repositories import PhotoRepository
        from db.models import Photo

        # Handle existing photos in the database
        if self.current_observation_id:
            # Get existing photos
            existing_photos = PhotoRepository.get_observation_photos(session, observation.id)
            existing_ids = {photo.id for photo in existing_photos}
            existing_paths = {photo.file_path for photo in existing_photos}

            # Find photos to delete (in database but not in self.photos)
            current_ids = {photo.get("id") for photo in self.photos if photo.get("id")}
            current_paths = {photo["path"] for photo in self.photos if "path" in photo}

            photos_to_delete = [photo for photo in existing_photos
                                if photo.id not in current_ids and photo.file_path not in current_paths]

            # Delete removed photos
            for photo in photos_to_delete:
                self.photo_manager.delete_photo(session, photo)

        # Add/update photos
        for photo_data in self.photos:
            path = photo_data.get("path")
            photo_id = photo_data.get("id")
            rotation = photo_data.get("rotation", 0)

            if not path:
                continue

            # Check if this is an existing photo with an ID
            if photo_id and self.current_observation_id:
                # Existing photo - update primary flag if needed
                photo = session.query(Photo).filter_by(id=photo_id).first()
                if photo:
                    if photo.is_primary != photo_data.get("is_primary", False):
                        PhotoRepository.set_primary_photo(session, photo.id)

                    # Apply rotation if needed
                    if rotation != 0:
                        self._apply_rotation_to_stored_photo(photo, rotation, session)

            # Check if this is an existing photo by path
            elif self.current_observation_id:
                # Get existing photos again in case of session expiry
                existing_photos = PhotoRepository.get_observation_photos(session, observation.id)
                photo_with_path = next((p for p in existing_photos if p.file_path == path), None)

                if photo_with_path:
                    # Existing photo by path - update primary flag if needed
                    if photo_with_path.is_primary != photo_data.get("is_primary", False):
                        PhotoRepository.set_primary_photo(session, photo_with_path.id)

                    # Apply rotation if needed
                    if rotation != 0:
                        self._apply_rotation_to_stored_photo(photo_with_path, rotation, session)
                else:
                    # New photo - store it
                    if rotation != 0:
                        # Rotate the image before storing
                        rotated_path = self._create_rotated_copy(path, rotation)
                        if rotated_path:
                            path = rotated_path

                    self.photo_manager.store_photo(
                        session,
                        observation.id,
                        path,
                        is_primary=photo_data.get("is_primary", False)
                    )
            else:
                # New photo for new observation - store it
                if rotation != 0:
                    # Rotate the image before storing
                    rotated_path = self._create_rotated_copy(path, rotation)
                    if rotated_path:
                        path = rotated_path

                self.photo_manager.store_photo(
                    session,
                    observation.id,
                    path,
                    is_primary=photo_data.get("is_primary", False)
                )

    def _apply_rotation_to_stored_photo(self, photo, rotation, session):
        """Apply rotation to an already stored photo"""
        try:
            # Get the file path
            file_path = photo.file_path

            # Create a rotated version
            rotated_path = self._create_rotated_copy(file_path, rotation)

            if rotated_path:
                # Replace the original with the rotated version
                import shutil
                shutil.copy2(rotated_path, file_path)

                # Update thumbnails
                self.photo_manager.regenerate_thumbnails(photo, session)
        except Exception as e:
            print(f"Error rotating stored photo: {e}")

    def _create_rotated_copy(self, path, rotation):
        """Create a rotated copy of the image and return its path"""
        try:
            # Create a temporary file name
            import tempfile
            from pathlib import Path

            original_path = Path(path)
            temp_dir = Path(tempfile.gettempdir())
            temp_file = temp_dir / f"rotated_{original_path.name}"

            # Open and rotate the image
            with Image.open(path) as img:
                # PIL rotation is counter-clockwise, so we negate the angle
                rotated_img = img.rotate(-rotation, expand=True)
                rotated_img.save(temp_file)

            return str(temp_file)
        except Exception as e:
            print(f"Error creating rotated copy: {e}")
            return None