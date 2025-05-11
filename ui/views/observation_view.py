# ui/views/observation_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PIL.ImageQt import ImageQt


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
        """Load observation with progressive loading strategy"""
        self.current_observation_id = observation_id
        self.photos_loaded = False
        self.custom_fields_loaded = False
        self.tags_loaded = False

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
                self.photos_loaded = True

            # Create placeholders for other sections
            self._create_section_placeholders()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load observation: {str(e)}")
            if self.view_session:
                self.view_session.close()
                self.view_session = None

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

    def _create_section_placeholders(self):
        """Create UI placeholders for sections that can be loaded on demand"""
        # Custom fields placeholder
        if self.current_observation_data['custom_fields'] and not self.custom_fields_loaded:
            placeholder = QPushButton("Load Custom Fields")
            placeholder.clicked.connect(lambda: self._load_section('custom_fields'))
            self.custom_fields_layout.addWidget(placeholder)

        # Tags placeholder  
        if self.current_observation_data['tags'] and not self.tags_loaded:
            placeholder = QPushButton("Load Tags")
            placeholder.clicked.connect(lambda: self._load_section('tags'))
            self.tags_layout.addWidget(placeholder)

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
        """Load and display photos for the observation"""
        data = self.current_observation_data
        photos = data['photos']

        if not photos:
            self.photo_frame.hide()
            return

        self.photo_frame.show()

        # Find primary photo, or use first one
        primary_photo = next((p for p in photos if p['is_primary']), photos[0] if photos else None)

        if primary_photo:
            lifelist_id = data['lifelist_id']
            observation_id = data['id']

            # Load large primary photo
            primary_image = self.photo_manager.get_photo_thumbnail(
                lifelist_id, observation_id, primary_photo['id'], "lg"
            )

            if primary_image:
                # Convert PIL image to QPixmap
                q_image = ImageQt(primary_image)
                pixmap = QPixmap.fromImage(q_image)

                self.primary_photo_label.setPixmap(pixmap)
                self.images.append(pixmap)  # Keep reference

        # Add thumbnails if there are multiple photos
        if len(photos) > 1:
            for photo in photos:
                if thumb_image := self.photo_manager.get_photo_thumbnail(
                        data['lifelist_id'], data['id'], photo['id'], "sm"
                ):
                    # Create thumbnail label
                    thumb_label = QLabel()

                    # Convert PIL image to QPixmap
                    q_image = ImageQt(thumb_image)
                    pixmap = QPixmap.fromImage(q_image)

                    thumb_label.setPixmap(pixmap)
                    self.thumbnails_layout.addWidget(thumb_label)

                    # Highlight if primary
                    if photo['is_primary']:
                        thumb_label.setStyleSheet("border: 2px solid #3498db;")

                    self.images.append(pixmap)  # Keep reference

    def _display_custom_fields(self, custom_fields):
        """Display custom fields for the observation"""
        # Clear the placeholder button
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