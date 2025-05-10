# ui/views/observation_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QGridLayout)
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
        """Load and display an observation"""
        self.images = []  # Clear image references
        self.current_observation_id = observation_id

        # Clear existing content
        self._clear_content()

        with self.db_manager.session_scope() as session:
            # Get the observation details
            query = session.query(
                self.db_manager.engine.models.Observation
            ).filter_by(id=observation_id)

            observation = query.first()

            if not observation:
                self.title_label.setText("Observation not found")
                return

            # Get the lifelist to determine entry_term and observation_term
            from config import Config
            config = Config.load()

            lifelist_id = observation.lifelist_id
            from db.repositories import LifelistRepository
            lifelist = LifelistRepository.get_lifelist(session, lifelist_id)

            lifelist_type = lifelist[4] if lifelist else ""
            entry_term = config.get_entry_term(lifelist_type)
            observation_term = config.get_observation_term(lifelist_type)

            # Update title
            self.title_label.setText(f"{observation_term.capitalize()}: {observation.entry_name}")

            # Load photos
            self._load_photos(session, observation)

            # Display details
            self._display_details(observation, entry_term, observation_term)

            # Display custom fields
            self._display_custom_fields(observation)

            # Display tags
            self._display_tags(observation)

    def _clear_content(self):
        """Clear all content areas"""
        # Clear photos
        self.primary_photo_label.clear()

        # Clear thumbnails
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear details
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear custom fields
        while self.custom_fields_layout.count() > 1:  # Keep the header
            item = self.custom_fields_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Clear tags
        while self.tags_container_layout.count():
            item = self.tags_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_photos(self, session, observation):
        """Load and display photos for the observation"""
        photos = observation.photos

        if not photos:
            self.photo_frame.hide()
            return

        self.photo_frame.show()

        # Find primary photo, or use first one
        primary_photo = next((p for p in photos if p.is_primary), photos[0] if photos else None)

        if primary_photo:
            lifelist_id = observation.lifelist_id
            observation_id = observation.id

            # Load large primary photo
            primary_image = self.photo_manager.get_photo_thumbnail(
                lifelist_id, observation_id, primary_photo.id, "lg"
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
                thumb_image = self.photo_manager.get_photo_thumbnail(
                    observation.lifelist_id, observation.id, photo.id, "sm"
                )

                if thumb_image:
                    # Create thumbnail label
                    thumb_label = QLabel()

                    # Convert PIL image to QPixmap
                    q_image = ImageQt(thumb_image)
                    pixmap = QPixmap.fromImage(q_image)

                    thumb_label.setPixmap(pixmap)
                    self.thumbnails_layout.addWidget(thumb_label)

                    # Highlight if primary
                    if photo.is_primary:
                        thumb_label.setStyleSheet("border: 2px solid #3498db;")

                    self.images.append(pixmap)  # Keep reference

    def _display_details(self, observation, entry_term, observation_term):
        """Display observation details"""
        details = [
            ("Entry Name:", observation.entry_name),
            (f"{observation_term.capitalize()} Date:",
             observation.observation_date.strftime("%Y-%m-%d") if observation.observation_date else "Not recorded"),
            ("Location:", observation.location or "Not recorded"),
            ("Coordinates:",
             f"{observation.latitude}, {observation.longitude}" if observation.latitude and observation.longitude else "Not recorded"),
            ("Tier:", observation.tier or "Not specified"),
            ("Notes:", observation.notes or "No notes")
        ]

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

    def _display_custom_fields(self, observation):
        """Display custom fields for the observation"""
        custom_fields = observation.custom_fields

        if not custom_fields:
            # Hide section if no custom fields
            self.custom_fields_frame.hide()
            return

        self.custom_fields_frame.show()

        # Create a grid layout for the custom fields
        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)

        row = 0
        for field in custom_fields:
            # Create label
            label = QLabel(field.field.field_name + ":")
            label.setStyleSheet("font-weight: bold;")

            # Create value
            value = QLabel(field.value or "Not specified")
            value.setWordWrap(True)

            # Add to grid
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(value, row, 1)

            row += 1

        self.custom_fields_layout.addWidget(grid_frame)

    def _display_tags(self, observation):
        """Display observation tags"""
        tags = observation.tags

        if not tags:
            # Hide section if no tags
            self.tags_frame.hide()
            return

        self.tags_frame.show()

        # Group tags by category
        tags_by_category = {}
        for tag in tags:
            category = tag.category or "Uncategorized"
            if category not in tags_by_category:
                tags_by_category[category] = []
            tags_by_category[category].append(tag.name)

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