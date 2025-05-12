# ui/views/observation_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor
from PIL.ImageQt import ImageQt


# Custom clickable label for thumbnails
class ClickablePhotoLabel(QLabel):
    """A custom QLabel that emits a signal when clicked."""
    clicked = Signal(int)  # Signal to emit photo ID when clicked

    def __init__(self, photo_id, parent=None):
        super().__init__(parent)
        self.photo_id = photo_id
        self.setCursor(QCursor(Qt.PointingHandCursor))  # Change cursor to hand when hovering

    def mousePressEvent(self, event):
        self.clicked.emit(self.photo_id)
        super().mousePressEvent(event)


class ObservationView(QWidget):
    """Widget for displaying observation details"""

    def __init__(self, main_window, photo_manager):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.db_manager
        self.photo_manager = photo_manager

        # Keep references to images
        self.images = []

        # Add view session
        self.view_session = None
        self.current_observation_data = None
        self.current_observation_id = None

        # Progressive loading state
        self.photos_loaded = False
        self.custom_fields_loaded = False
        self.tags_loaded = False

        # Photo gallery tracking
        self.thumbnail_labels = []  # References to QLabel objects
        self.photo_hints = []  # References to hint labels
        self.displayed_photo_id = None  # ID of currently displayed photo

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)

        # Header with back button and title
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)

        self.back_button = QPushButton("Back to Lifelist")
        self.back_button.clicked.connect(self._go_back)
        header_layout.addWidget(self.back_button)

        self.title_label = QLabel("Observation Details")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._edit_observation)
        header_layout.addWidget(self.edit_button)

        layout.addWidget(header_frame)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)

        # Photo gallery
        self.photo_frame = QFrame()
        self.photo_layout = QVBoxLayout(self.photo_frame)

        # Large primary photo
        self.primary_photo_label = QLabel()
        self.primary_photo_label.setAlignment(Qt.AlignCenter)
        self.primary_photo_label.setMinimumHeight(300)
        self.photo_layout.addWidget(self.primary_photo_label)

        # Thumbnail row
        self.thumbnails_frame = QFrame()
        self.thumbnails_layout = QHBoxLayout(self.thumbnails_frame)
        self.thumbnails_layout.setAlignment(Qt.AlignCenter)
        self.photo_layout.addWidget(self.thumbnails_frame)

        self.content_layout.addWidget(self.photo_frame)

        # Details grid
        self.details_frame = QFrame()
        self.details_layout = QGridLayout(self.details_frame)

        # Details will be filled in when loading the observation

        self.content_layout.addWidget(self.details_frame)

        # Custom fields section
        self.custom_fields_frame = QFrame()
        self.custom_fields_layout = QVBoxLayout(self.custom_fields_frame)

        self.custom_fields_label = QLabel("Custom Fields")
        self.custom_fields_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.custom_fields_layout.addWidget(self.custom_fields_label)

        self.content_layout.addWidget(self.custom_fields_frame)

        # Tags section
        self.tags_frame = QFrame()
        self.tags_layout = QVBoxLayout(self.tags_frame)

        self.tags_label = QLabel("Tags")
        self.tags_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.tags_layout.addWidget(self.tags_label)

        self.tags_container = QFrame()
        self.tags_container_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.addWidget(self.tags_container)

        self.content_layout.addWidget(self.tags_frame)

        # Add some space at the bottom
        self.content_layout.addStretch()

    def load_observation(self, observation_id):
        """Load observation with all data immediately"""
        self.current_observation_id = observation_id

        # Clear old UI state
        self._clear_all_display()

        # Close previous session if exists
        if self.view_session:
            self.view_session.close()

        # Create view-scoped session
        self.view_session = self.main_window.db_manager.Session()

        try:
            # Get basic observation data with eager loading
            with self.main_window.db_manager.session_scope() as session:
                from db.repositories import ObservationRepository
                self.current_observation_data = ObservationRepository.get_observation_with_eager_loading(
                    session, observation_id
                )

                if not self.current_observation_data:
                    self.title_label.setText("Observation not found")
                    return

            # Get lifelist info for terminology
            lifelist_id = self.current_observation_data['lifelist_id']
            from db.repositories import LifelistRepository
            with self.main_window.db_manager.session_scope() as session:
                if lifelist := LifelistRepository.get_lifelist(
                        session, lifelist_id
                ):
                    lifelist_type = lifelist[4] if lifelist else ""

                    # Get terminology
                    from config import Config
                    config = Config.load()
                    entry_term = config.get_entry_term(lifelist_type)
                    observation_term = config.get_observation_term(lifelist_type)
                else:
                    entry_term = "item"
                    observation_term = "entry"

            # Display basic info immediately
            self._display_basic_info(entry_term, observation_term)

            # Load photos if present
            if self.current_observation_data['photos']:
                self._load_photos_section()
            else:
                # Explicitly hide the photo frame for entries without photos
                self.photo_frame.hide()
                # Clear any thumbnails from previous views
                self._clear_photos()

            # Load custom fields immediately
            self._display_custom_fields(self.current_observation_data['custom_fields'])

            # Load tags immediately
            self._display_tags(self.current_observation_data['tags'])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load observation: {str(e)}")
            if self.view_session:
                self.view_session.close()
                self.view_session = None

    def _clear_all_display(self):
        """Clear all display elements to prevent showing stale data"""
        # Clear photos
        self._clear_photos()

        # Clear primary photo
        self.primary_photo_label.clear()

        # Clear details grid
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear custom fields
        while self.custom_fields_layout.count() > 1:  # Keep the title
            item = self.custom_fields_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Clear tags
        while self.tags_container_layout.count():
            item = self.tags_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_photos(self):
        """Clear all photo thumbnails and references"""
        # Clear thumbnail images
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear hint labels
        for hint in self.photo_hints:
            if hint.parent():
                hint.setParent(None)

        # Clear lists
        self.images = []
        self.thumbnail_labels = []
        self.photo_hints = []
        self.displayed_photo_id = None

    def _display_basic_info(self, entry_term, observation_term):
        """Display basic observation info from cached data"""
        data = self.current_observation_data
        self.title_label.setText(f"{observation_term.capitalize()}: {data['entry_name']}")

        details = [
            ("Entry Name:", data['entry_name']),
            ("Date:", data['observation_date'].strftime("%Y-%m-%d") if data['observation_date'] else "Not recorded"),
            ("Location:", data['location'] or "Not recorded"),
            ("Coordinates:",
             f"{data['latitude']}, {data['longitude']}" if data['latitude'] and data['longitude'] else "Not recorded"),
            ("Tier:", data['tier'] or "Not specified"),
            ("Notes:", data['notes'] or "No notes")
        ]

        self._update_details_grid(details)

    def _update_details_grid(self, details):
        """Update the details grid with given details"""
        # Clear existing details
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add details
        row = 0
        for label_text, value_text in details:
            # Create label widget
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")

            # Create value widget
            value = QLabel(value_text)
            value.setWordWrap(True)

            # Add to grid
            self.details_layout.addWidget(label, row, 0)
            self.details_layout.addWidget(value, row, 1)

            row += 1

    def _load_section(self, section_name):
        """Load a specific section on demand"""
        data = self.current_observation_data

        if section_name == 'custom_fields' and not self.custom_fields_loaded:
            self._display_custom_fields(data['custom_fields'])
            self.custom_fields_loaded = True

        elif section_name == 'tags' and not self.tags_loaded:
            self._display_tags(data['tags'])
            self.tags_loaded = True

    def _load_photos_section(self):
        """Load and display photos for the observation with interactive gallery"""
        # First clear any existing photos
        self._clear_photos()

        data = self.current_observation_data
        photos = data['photos']

        if not photos:
            self.photo_frame.hide()
            return

        self.photo_frame.show()

        # Find primary photo, or use first one
        primary_photo = next((p for p in photos if p['is_primary']), photos[0] if photos else None)
        self.displayed_photo_id = primary_photo['id'] if primary_photo else None

        if primary_photo:
            self._load_large_photo(primary_photo['id'])

        # Add thumbnails if there are multiple photos
        if len(photos) > 1:
            for photo in photos:
                if thumb_image := self.photo_manager.get_photo_thumbnail(
                        data['lifelist_id'], data['id'], photo['id'], "sm"
                ):
                    # Create clickable thumbnail label
                    thumb_label = ClickablePhotoLabel(photo['id'])

                    # Connect click signal
                    thumb_label.clicked.connect(self._on_thumbnail_clicked)

                    # Convert PIL image to QPixmap
                    q_image = ImageQt(thumb_image)
                    pixmap = QPixmap.fromImage(q_image)

                    thumb_label.setPixmap(pixmap)
                    self.thumbnails_layout.addWidget(thumb_label)

                    # Highlight if primary
                    style = "border: 2px solid #3498db;" if photo['is_primary'] else ""
                    # Add hover effect
                    style += "padding: 2px; margin: 2px;"
                    style += "border-radius: 4px;"
                    thumb_label.setStyleSheet(style)

                    self.images.append(pixmap)  # Keep reference
                    self.thumbnail_labels.append(thumb_label)  # Keep reference

    # Add a method to load a large photo by ID
    def _load_large_photo(self, photo_id):
        """Load and display a large version of the specified photo"""
        data = self.current_observation_data
        photo = next((p for p in data['photos'] if p['id'] == photo_id), None)

        if not photo:
            return

        lifelist_id = data['lifelist_id']
        observation_id = data['id']

        # Load large photo
        large_image = self.photo_manager.get_photo_thumbnail(
            lifelist_id, observation_id, photo_id, "lg"
        )

        if large_image:
            # Convert PIL image to QPixmap
            q_image = ImageQt(large_image)
            pixmap = QPixmap.fromImage(q_image)

            self.primary_photo_label.setPixmap(pixmap)

            # Track which image is displayed
            self.displayed_photo_id = photo_id

            # Update thumbnail highlighting for visual feedback
            self._update_thumbnail_highlighting()

    # Add a method to handle thumbnail clicks
    def _on_thumbnail_clicked(self, photo_id):
        """Handle thumbnail click by displaying that photo in the large view"""
        if photo_id == self.displayed_photo_id:
            return  # Already displaying this photo

        self._load_large_photo(photo_id)

    # Add a method to update thumbnail highlighting
    def _update_thumbnail_highlighting(self):
        """Update the visual highlighting of thumbnails"""
        data = self.current_observation_data

        for thumb_label in self.thumbnail_labels:
            photo = next((p for p in data['photos'] if p['id'] == thumb_label.photo_id), None)

            # Highlight if primary or currently displayed
            is_primary = photo and photo.get('is_primary', False)
            is_displayed = thumb_label.photo_id == self.displayed_photo_id

            style = ""
            if is_primary:
                style += "border: 2px solid #3498db;"  # Blue border for primary
            if is_displayed:
                style += "border: 2px solid #e74c3c;"  # Red border for displayed
                style += "background-color: rgba(231, 76, 60, 0.1);"  # Light red background

            # Add hover effect
            style += "padding: 2px; margin: 2px;"
            style += "border-radius: 4px;"

            thumb_label.setStyleSheet(style)

    def _display_custom_fields(self, custom_fields):
        """Display custom fields for the observation"""
        # Clear any existing content
        while self.custom_fields_layout.count() > 1:  # Keep the header
            item = self.custom_fields_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not custom_fields:
            # Hide section if no custom fields
            self.custom_fields_frame.hide()
            return

        self.custom_fields_frame.show()

        # Create a grid layout for the custom fields
        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)

        for row, field in enumerate(custom_fields):
            # Create label
            label = QLabel(f"{field['field_name']}:")
            label.setStyleSheet("font-weight: bold;")

            # Create value
            value = QLabel(field['value'] or "Not specified")
            value.setWordWrap(True)

            # Add to grid
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(value, row, 1)

        self.custom_fields_layout.addWidget(grid_frame)

    def _display_tags(self, tags):
        """Display observation tags"""
        # Clear existing tags
        while self.tags_container_layout.count():
            item = self.tags_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not tags:
            # Hide section if no tags
            self.tags_frame.hide()
            return

        self.tags_frame.show()

        # Group tags by category
        tags_by_category = {}
        for tag in tags:
            category = tag['category'] or "Uncategorized"
            if category not in tags_by_category:
                tags_by_category[category] = []
            tags_by_category[category].append(tag['name'])

        # Add each category in its own container
        for category, tag_names in tags_by_category.items():
            category_frame = QFrame()
            category_layout = QVBoxLayout(category_frame)

            # Add category header
            if category != "Uncategorized":
                category_label = QLabel(category)
                category_label.setStyleSheet("font-weight: bold;")
                category_layout.addWidget(category_label)

            # Add tags in a flow layout
            tags_flow = QHBoxLayout()

            for tag_name in tag_names:
                tag_label = QLabel(tag_name)
                tag_label.setStyleSheet(
                    "background-color: #3498db; color: white; "
                    "padding: 4px 8px; border-radius: 4px;"
                )
                tags_flow.addWidget(tag_label)

            tags_flow.addStretch()
            category_layout.addLayout(tags_flow)

            self.tags_container_layout.addWidget(category_frame)

    def _go_back(self):
        """Return to lifelist view"""
        lifelist_id = self.main_window.current_lifelist_id
        self.main_window.open_lifelist(lifelist_id)

    def _edit_observation(self):
        """Show the form to edit this observation"""
        self.main_window.show_observation_form(
            observation_id=self.current_observation_id
        )

    def closeEvent(self, event):
        """Clean up session when view closes"""
        if self.view_session:
            self.view_session.close()
            self.view_session = None
        super().closeEvent(event)