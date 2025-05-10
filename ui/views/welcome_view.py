# ui/views/welcome_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QSpacerItem,
                               QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class WelcomeView(QWidget):
    """Welcome screen widget"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.db_manager

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)

        # Welcome header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2a5db0;")
        header_layout = QVBoxLayout(header_frame)

        welcome_label = QLabel("Welcome to Lifelist Tracker")
        welcome_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        welcome_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(welcome_label)

        subtitle_label = QLabel("Track and catalog your collections")
        subtitle_label.setStyleSheet("color: white; font-size: 16px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)

        layout.addWidget(header_frame)

        # Content area
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)

        # App description
        description_label = QLabel(
            "Lifelist Tracker helps you catalog and track your collections and observations. "
            "From wildlife sightings to books read, places visited, or any other collection, "
            "our flexible system can be adapted to your needs.")
        description_label.setWordWrap(True)
        content_layout.addWidget(description_label)

        # Create two columns for quick start and recent lifelists
        columns_layout = QHBoxLayout()

        # Left column - Quick start
        left_column = QFrame()
        left_layout = QVBoxLayout(left_column)

        quick_start_label = QLabel("Quick Start")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        quick_start_label.setFont(font)
        left_layout.addWidget(quick_start_label)

        # Quick start actions
        start_actions = [
            ("Create a new lifelist", self._create_new_lifelist),
            ("Import an existing lifelist", self._import_lifelist),
            ("Explore sample lifelists", self._explore_samples)
        ]

        for action_text, action_slot in start_actions:
            action_button = QPushButton(action_text)
            action_button.clicked.connect(action_slot)
            left_layout.addWidget(action_button)

        left_layout.addStretch()
        columns_layout.addWidget(left_column)

        # Right column - Recent lifelists
        right_column = QFrame()
        right_layout = QVBoxLayout(right_column)

        recent_label = QLabel("Your Lifelists")
        recent_label.setFont(font)
        right_layout.addWidget(recent_label)

        # Scrollable area for recent lifelists
        lifelists_scroll = QScrollArea()
        lifelists_scroll.setWidgetResizable(True)

        self.lifelists_container = QWidget()
        self.lifelists_layout = QVBoxLayout(self.lifelists_container)
        lifelists_scroll.setWidget(self.lifelists_container)

        right_layout.addWidget(lifelists_scroll)
        columns_layout.addWidget(right_column)

        # Add columns to content
        content_layout.addLayout(columns_layout)
        layout.addWidget(content_frame)

        # Add a spacer at the bottom
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def refresh(self):
        """Refresh the view with current data"""
        # Clear existing lifelist buttons
        while self.lifelists_layout.count():
            item = self.lifelists_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get lifelists
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelists = LifelistRepository.get_lifelists(session)

        # Group lifelists by type
        lifelists_by_type = {}
        for lifelist_id, name, _, type_name in lifelists:
            if type_name not in lifelists_by_type:
                lifelists_by_type[type_name] = []
            lifelists_by_type[type_name].append((lifelist_id, name))

        if not lifelists:
            empty_label = QLabel("You don't have any lifelists yet. Create your first one!")
            empty_label.setWordWrap(True)
            empty_label.setAlignment(Qt.AlignCenter)
            self.lifelists_layout.addWidget(empty_label)
            return

        # Add lifelists grouped by type
        for type_name, type_lifelists in lifelists_by_type.items():
            if type_name:
                # Add type header
                type_label = QLabel(type_name)
                type_label.setStyleSheet("background-color: #444; color: white; padding: 4px; border-radius: 4px;")
                self.lifelists_layout.addWidget(type_label)

            # Add lifelist buttons
            for lifelist_id, name in type_lifelists:
                button = QPushButton(name)
                button.clicked.connect(lambda checked=False, lid=lifelist_id: self.main_window.open_lifelist(lid))
                self.lifelists_layout.addWidget(button)

        # Add a spacer at the end
        self.lifelists_layout.addStretch()

    def _create_new_lifelist(self):
        """Show lifelist creation wizard"""
        self.main_window._show_lifelist_wizard()

    def _import_lifelist(self):
        """Show lifelist import dialog"""
        self.main_window._import_lifelist()

    def _explore_samples(self):
        """Show sample lifelists"""
        # Create a few sample lifelists
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository, ObservationRepository
            from datetime import datetime, timedelta
            import random

            # Check if we already have sample lifelists
            if (
                sample_lifelists := session.query(
                    self.db_manager.engine.models.Lifelist
                )
                .filter(
                    self.db_manager.engine.models.Lifelist.name.like("Sample%")
                )
                .all()
            ):
                # We already have samples, just show them
                message = "Sample lifelists are already available in your list. Try opening one!"
                QMessageBox.information(self, "Sample Lifelists", message)
                return

            # Get lifelist types
            lifelist_types = LifelistRepository.get_lifelist_types(session)

            # If no types exist, create default types from config
            if not lifelist_types:
                # Create a bird watching type
                bird_type = self.db_manager.engine.models.LifelistType(
                    name="Wildlife",
                    description="A lifelist for tracking wildlife sightings",
                    icon=""
                )
                session.add(bird_type)
                session.flush()  # To get the ID

                # Add tiers
                tiers = ["wild", "heard", "captive"]
                for i, tier_name in enumerate(tiers):
                    tier = self.db_manager.engine.models.LifelistTypeTier(
                        lifelist_type_id=bird_type.id,
                        tier_name=tier_name,
                        tier_order=i
                    )
                    session.add(tier)

                lifelist_types = [bird_type]

            # Choose a type for our sample
            lifelist_type = next((t for t in lifelist_types if t.name == "Wildlife"), lifelist_types[0])

            # Create a bird watching lifelist
            lifelist_id = LifelistRepository.create_lifelist(
                session,
                "Sample Bird Watching",
                lifelist_type.id,
                "eBird"
            )

            if not lifelist_id:
                QMessageBox.warning(self, "Error", "Failed to create sample lifelist")
                return

            # Add custom fields if not already present
            custom_fields = session.query(
                self.db_manager.engine.models.CustomField
            ).filter(
                self.db_manager.engine.models.CustomField.lifelist_id == lifelist_id
            ).all()

            if not custom_fields:
                # Add some bird-specific fields
                fields = [
                    ("Scientific Name", "text", 0),
                    ("Family", "text", 0),
                    ("Location Type", "choice", 0, {"options": [
                        {"label": "Forest", "value": "forest"},
                        {"label": "Wetland", "value": "wetland"},
                        {"label": "Urban", "value": "urban"},
                        {"label": "Shore", "value": "shore"},
                        {"label": "Mountain", "value": "mountain"}
                    ]}),
                    ("Weather", "text", 0),
                    ("Behavior", "text", 0)
                ]

                for i, (name, type_, required, options) in enumerate(fields):
                    field = self.db_manager.engine.models.CustomField(
                        lifelist_id=lifelist_id,
                        field_name=name,
                        field_type=type_,
                        field_options=options if 'options' in locals() else None,
                        is_required=bool(required),
                        display_order=i
                    )
                    session.add(field)

                session.flush()

                # Get the fields back to use their IDs
                custom_fields = session.query(
                    self.db_manager.engine.models.CustomField
                ).filter(
                    self.db_manager.engine.models.CustomField.lifelist_id == lifelist_id
                ).all()

            # Create field ID mapping
            field_mapping = {}
            for field in custom_fields:
                field_mapping[field.field_name] = field.id

            # Add some sample observations
            bird_observations = [
                {
                    "entry_name": "American Robin",
                    "scientific_name": "Turdus migratorius",
                    "family": "Turdidae",
                    "location": "Central Park",
                    "latitude": 40.785091,
                    "longitude": -73.968285,
                    "tier": "wild",
                    "location_type": "urban",
                    "weather": "Sunny",
                    "behavior": "Foraging on ground"
                },
                {
                    "entry_name": "Bald Eagle",
                    "scientific_name": "Haliaeetus leucocephalus",
                    "family": "Accipitridae",
                    "location": "Yellowstone National Park",
                    "latitude": 44.427963,
                    "longitude": -110.588455,
                    "tier": "wild",
                    "location_type": "forest",
                    "weather": "Partly cloudy",
                    "behavior": "Soaring"
                },
                {
                    "entry_name": "Northern Cardinal",
                    "scientific_name": "Cardinalis cardinalis",
                    "family": "Cardinalidae",
                    "location": "Backyard",
                    "latitude": 39.952584,
                    "longitude": -75.165222,
                    "tier": "wild",
                    "location_type": "urban",
                    "weather": "Rainy",
                    "behavior": "Singing"
                },
                {
                    "entry_name": "Great Blue Heron",
                    "scientific_name": "Ardea herodias",
                    "family": "Ardeidae",
                    "location": "Lake Michigan",
                    "latitude": 41.878113,
                    "longitude": -87.629799,
                    "tier": "wild",
                    "location_type": "wetland",
                    "weather": "Foggy",
                    "behavior": "Fishing"
                },
                {
                    "entry_name": "Barn Owl",
                    "scientific_name": "Tyto alba",
                    "family": "Tytonidae",
                    "location": "Old barn",
                    "tier": "heard",
                    "location_type": "urban",
                    "weather": "Night",
                    "behavior": "Calling"
                }
            ]

            # Create tags
            habitat_tags = ["Forest", "Wetland", "Urban", "Coastal", "Mountain"]
            behavior_tags = ["Flying", "Perching", "Feeding", "Singing", "Nesting"]

            tag_ids = {}

            # Create habitat tags
            for tag_name in habitat_tags:
                tag = session.query(
                    self.db_manager.engine.models.Tag
                ).filter(
                    self.db_manager.engine.models.Tag.name == tag_name
                ).first()

                if not tag:
                    tag = self.db_manager.engine.models.Tag(
                        name=tag_name,
                        category="Habitat"
                    )
                    session.add(tag)
                    session.flush()

                tag_ids[tag_name] = tag.id

            # Create behavior tags
            for tag_name in behavior_tags:
                tag = session.query(
                    self.db_manager.engine.models.Tag
                ).filter(
                    self.db_manager.engine.models.Tag.name == tag_name
                ).first()

                if not tag:
                    tag = self.db_manager.engine.models.Tag(
                        name=tag_name,
                        category="Behavior"
                    )
                    session.add(tag)
                    session.flush()

                tag_ids[tag_name] = tag.id

            # Add observations
            for bird in bird_observations:
                # Create random date in last 6 months
                days_ago = random.randint(1, 180)
                obs_date = datetime.now() - timedelta(days=days_ago)

                # Create observation
                obs_id = ObservationRepository.create_observation(
                    session,
                    lifelist_id,
                    bird["entry_name"],
                    tier=bird["tier"],
                    observation_date=obs_date,
                    location=bird["location"],
                    latitude=bird.get("latitude"),
                    longitude=bird.get("longitude"),
                    notes=f"Observed a {bird['entry_name']} {bird.get('behavior', '').lower()}."
                )

                if not obs_id:
                    continue

                # Add custom field values
                custom_values = {}
                if "scientific_name" in bird and "Scientific Name" in field_mapping:
                    custom_values[field_mapping["Scientific Name"]] = bird["scientific_name"]

                if "family" in bird and "Family" in field_mapping:
                    custom_values[field_mapping["Family"]] = bird["family"]

                if "location_type" in bird and "Location Type" in field_mapping:
                    custom_values[field_mapping["Location Type"]] = bird["location_type"]

                if "weather" in bird and "Weather" in field_mapping:
                    custom_values[field_mapping["Weather"]] = bird["weather"]

                if "behavior" in bird and "Behavior" in field_mapping:
                    custom_values[field_mapping["Behavior"]] = bird["behavior"]

                if custom_values:
                    ObservationRepository.set_observation_custom_fields(
                        session,
                        obs_id,
                        custom_values
                    )

                # Add tags based on location_type and behavior
                obs_tags = []

                if bird.get("location_type") == "forest":
                    obs_tags.append(tag_ids.get("Forest"))
                elif bird.get("location_type") == "wetland":
                    obs_tags.append(tag_ids.get("Wetland"))
                elif bird.get("location_type") == "urban":
                    obs_tags.append(tag_ids.get("Urban"))

                behavior_lower = bird.get("behavior", "").lower()
                if "singing" in behavior_lower:
                    obs_tags.append(tag_ids.get("Singing"))
                elif "soaring" in behavior_lower or "flying" in behavior_lower:
                    obs_tags.append(tag_ids.get("Flying"))
                elif "foraging" in behavior_lower or "fishing" in behavior_lower:
                    obs_tags.append(tag_ids.get("Feeding"))

                # Add tags to observation
                if obs_tags:
                    from db.repositories import TagRepository
                    TagRepository.set_observation_tags(session, obs_id, [t for t in obs_tags if t])

            # Create book collection sample
            book_type = next((t for t in lifelist_types if t.name == "Books"), None)

            if not book_type:
                # Create a book collection type
                book_type = self.db_manager.engine.models.LifelistType(
                    name="Books",
                    description="A lifelist for tracking your book collection",
                    icon=""
                )
                session.add(book_type)
                session.flush()  # To get the ID

                # Add tiers
                tiers = ["read", "currently reading", "want to read", "abandoned"]
                for i, tier_name in enumerate(tiers):
                    tier = self.db_manager.engine.models.LifelistTypeTier(
                        lifelist_type_id=book_type.id,
                        tier_name=tier_name,
                        tier_order=i
                    )
                    session.add(tier)

                session.flush()

            # Create a book collection lifelist
            book_lifelist_id = LifelistRepository.create_lifelist(
                session,
                "Sample Book Collection",
                book_type.id
            )

            # Add sample books (simplified for brevity)
            book_observations = [
                {
                    "entry_name": "The Lord of the Rings",
                    "tier": "read",
                    "location": "Home library",
                    "notes": "Classic fantasy epic."
                },
                {
                    "entry_name": "Dune",
                    "tier": "read",
                    "location": "Home library",
                    "notes": "Sci-fi masterpiece."
                },
                {
                    "entry_name": "Project Hail Mary",
                    "tier": "currently reading",
                    "location": "Kindle",
                    "notes": "Engaging sci-fi novel."
                }
            ]

            # Add book observations
            for book in book_observations:
                days_ago = random.randint(1, 365)
                obs_date = datetime.now() - timedelta(days=days_ago)

                ObservationRepository.create_observation(
                    session,
                    book_lifelist_id,
                    book["entry_name"],
                    tier=book["tier"],
                    observation_date=obs_date,
                    location=book.get("location"),
                    notes=book.get("notes")
                )

            # Commit changes
            session.commit()

            message = (
                "Sample lifelists have been created! You can now explore:\n\n"
                "1. Sample Bird Watching - a wildlife lifelist with observations and custom fields\n"
                "2. Sample Book Collection - a book tracking lifelist\n\n"
                "Open them from the sidebar to explore their features."
            )

            QMessageBox.information(self, "Sample Lifelists Created", message)