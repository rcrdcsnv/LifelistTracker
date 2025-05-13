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
            from db.models import Lifelist, LifelistType, LifelistTypeTier, Tag, CustomField, ObservationCustomField
            from datetime import datetime, timedelta
            import random
            import json

            # Check if we already have sample lifelists
            sample_lifelists = session.query(Lifelist).filter(
                Lifelist.name.like("Sample%")
            ).all()

            if sample_lifelists:
                # We already have samples, just show them
                message = "Sample lifelists are already available in your list. Try opening one!"
                QMessageBox.information(self, "Sample Lifelists", message)
                return

            # Get lifelist types
            lifelist_types = LifelistRepository.get_lifelist_types(session)

            # If no types exist, create default types from config
            if not lifelist_types:
                # Create a bird watching type
                bird_type = LifelistType(
                    name="Wildlife",
                    description="A lifelist for tracking wildlife sightings",
                    icon=""
                )
                session.add(bird_type)
                session.flush()  # To get the ID

                # Add tiers
                tiers = ["wild", "heard", "captive"]
                for i, tier_name in enumerate(tiers):
                    tier = LifelistTypeTier(
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
                CustomField
            ).filter(
                CustomField.lifelist_id == lifelist_id
            ).all()

            if not custom_fields:
                # Add some bird-specific fields
                fields = [
                    ("Scientific Name", "text", 0, None),
                    ("Family", "text", 0, None),
                    ("Location Type", "choice", 0, {"options": [
                        {"label": "Forest", "value": "forest"},
                        {"label": "Wetland", "value": "wetland"},
                        {"label": "Urban", "value": "urban"},
                        {"label": "Shore", "value": "shore"},
                        {"label": "Mountain", "value": "mountain"}
                    ]}),
                    ("Weather", "text", 0, None),
                    ("Behavior", "text", 0, None)
                ]

                for i, (name, type_, required, options) in enumerate(fields):
                    field = CustomField(
                        lifelist_id=lifelist_id,
                        field_name=name,
                        field_type=type_,
                        field_options=options,
                        is_required=bool(required),
                        display_order=i
                    )
                    session.add(field)

                session.flush()

                # Get the fields back to use their IDs
                custom_fields = session.query(
                    CustomField
                ).filter(
                    CustomField.lifelist_id == lifelist_id
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
                tag = session.query(Tag).filter(Tag.name == tag_name).first()

                if not tag:
                    tag = Tag(
                        name=tag_name,
                        category="Habitat"
                    )
                    session.add(tag)
                    session.flush()

                tag_ids[tag_name] = tag.id

            # Create behavior tags
            for tag_name in behavior_tags:
                tag = session.query(Tag).filter(Tag.name == tag_name).first()

                if not tag:
                    tag = Tag(
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
                book_type = LifelistType(
                    name="Books",
                    description="A lifelist for tracking your book collection",
                    icon=""
                )
                session.add(book_type)
                session.flush()  # To get the ID

                # Add tiers
                tiers = ["read", "currently reading", "want to read", "abandoned"]
                for i, tier_name in enumerate(tiers):
                    tier = LifelistTypeTier(
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

            # Create an astronomy sample lifelist
            astronomy_type = next((t for t in lifelist_types if t.name == "Astronomy"), None)

            if not astronomy_type:
                # Create astronomy type if it doesn't exist
                astronomy_type = LifelistType(
                    name="Astronomy",
                    description="A lifelist for tracking astronomical observations",
                    icon=""
                )
                session.add(astronomy_type)
                session.flush()

                # Add tiers
                tiers = ["visual", "imaged", "sketched", "want to observe"]
                for i, tier_name in enumerate(tiers):
                    tier = LifelistTypeTier(
                        lifelist_type_id=astronomy_type.id,
                        tier_name=tier_name,
                        tier_order=i
                    )
                    session.add(tier)

                session.flush()

            # Create astronomy lifelist
            astronomy_lifelist_id = LifelistRepository.create_lifelist(
                session,
                "Sample Astronomy",
                astronomy_type.id
            )

            # Add custom fields for astronomy
            astro_custom_fields = session.query(CustomField).filter(
                CustomField.lifelist_id == astronomy_lifelist_id
            ).all()

            if not astro_custom_fields:
                # Add astronomy-specific fields
                astro_fields = [
                    ("Object Type", "choice", 1, {
                        "options": [
                            {"label": "Star", "value": "star"},
                            {"label": "Planet", "value": "planet"},
                            {"label": "Galaxy", "value": "galaxy"},
                            {"label": "Nebula", "value": "nebula"},
                            {"label": "Star Cluster", "value": "star_cluster"},
                            {"label": "Solar System", "value": "solar_system"}
                        ]
                    }),
                    ("Catalog Number", "text", 0, None),
                    ("Right Ascension", "text", 0, None),
                    ("Declination", "text", 0, None),
                    ("Magnitude", "number", 0, None),
                    ("Equipment", "text", 0, None),
                    ("Seeing Conditions", "choice", 0, {
                        "options": [
                            {"label": "Poor", "value": "poor"},
                            {"label": "Fair", "value": "fair"},
                            {"label": "Good", "value": "good"},
                            {"label": "Excellent", "value": "excellent"}
                        ]
                    }),
                    ("Light Pollution", "choice", 0, {
                        "options": [
                            {"label": "Bortle 1 - Excellent", "value": "bortle1"},
                            {"label": "Bortle 2 - Truly Dark", "value": "bortle2"},
                            {"label": "Bortle 3 - Rural Sky", "value": "bortle3"},
                            {"label": "Bortle 4 - Rural/Suburban", "value": "bortle4"},
                            {"label": "Bortle 5 - Suburban Sky", "value": "bortle5"},
                            {"label": "Bortle 6 - Bright Suburban", "value": "bortle6"},
                            {"label": "Bortle 7 - Suburban/Urban", "value": "bortle7"},
                            {"label": "Bortle 8 - City Sky", "value": "bortle8"},
                            {"label": "Bortle 9 - Inner City Sky", "value": "bortle9"}
                        ]
                    }),
                    ("Exposure Details", "text", 0, None),
                    ("Processing Software", "text", 0, None)
                ]

                for i, (name, type_, required, options) in enumerate(astro_fields):
                    field = CustomField(
                        lifelist_id=astronomy_lifelist_id,
                        field_name=name,
                        field_type=type_,
                        field_options=options,
                        is_required=bool(required),
                        display_order=i
                    )
                    session.add(field)

                session.flush()

                astro_custom_fields = session.query(CustomField).filter(
                    CustomField.lifelist_id == astronomy_lifelist_id
                ).all()

            # Create field ID mapping for astronomy
            astro_field_mapping = {}
            for field in astro_custom_fields:
                astro_field_mapping[field.field_name] = field.id

            # Add sample astronomy observations
            celestial_objects = [
                {
                    "entry_name": "M31 Andromeda Galaxy",
                    "tier": "imaged",
                    "location": "Dark Sky Park",
                    "notes": "Beautiful spiral galaxy, visible to naked eye.",
                    "object_type": "galaxy",
                    "catalog_number": "M31, NGC 224",
                    "right_ascension": "00h 42m 44.3s",
                    "declination": "+41° 16' 9\"",
                    "magnitude": "3.44",
                    "equipment": "8\" SCT, DSLR Camera",
                    "seeing_conditions": "good",
                    "light_pollution": "bortle3",
                    "exposure_details": "20 x 120s exposures, ISO 1600",
                    "processing_software": "PixInsight"
                },
                {
                    "entry_name": "Jupiter",
                    "tier": "visual",
                    "location": "Backyard",
                    "notes": "Four Galilean moons visible. Great Red Spot observed.",
                    "object_type": "planet",
                    "catalog_number": "Jupiter",
                    "right_ascension": "20h 10m 00s",  # Position varies
                    "declination": "-20° 30' 00\"",
                    "magnitude": "-2.94",
                    "equipment": "10\" Dobsonian",
                    "seeing_conditions": "fair",
                    "light_pollution": "bortle5",
                    "exposure_details": "Visual observation",
                    "processing_software": ""
                },
                {
                    "entry_name": "M42 Orion Nebula",
                    "tier": "imaged",
                    "location": "Observatory",
                    "notes": "Amazing star-forming region with intricate details.",
                    "object_type": "nebula",
                    "catalog_number": "M42, NGC 1976",
                    "right_ascension": "05h 35m 17.3s",
                    "declination": "-05° 23' 28\"",
                    "magnitude": "4.0",
                    "equipment": "APO Refractor, Cooled CCD",
                    "seeing_conditions": "excellent",
                    "light_pollution": "bortle4",
                    "exposure_details": "LRGB 20x5min each filter",
                    "processing_software": "AstroPixelProcessor"
                }
            ]

            # Create astronomy tags
            astro_object_tags = ["Galaxy", "Nebula", "Star Cluster", "Planet", "Star", "Moon"]
            astro_condition_tags = ["Dark Sky", "Light Polluted", "Good Seeing", "Poor Seeing"]

            # Add astronomy tags
            for tag_name in astro_object_tags:
                tag = session.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(
                        name=tag_name,
                        category="Celestial Object"
                    )
                    session.add(tag)
                    session.flush()
                tag_ids[tag_name] = tag.id

            for tag_name in astro_condition_tags:
                tag = session.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(
                        name=tag_name,
                        category="Observing Conditions"
                    )
                    session.add(tag)
                    session.flush()
                tag_ids[tag_name] = tag.id

            # Add observations
            for obj in celestial_objects:
                # Create observation with random date in past year
                days_ago = random.randint(1, 365)
                obs_date = datetime.now() - timedelta(days=days_ago)

                obs_id = ObservationRepository.create_observation(
                    session,
                    astronomy_lifelist_id,
                    obj["entry_name"],
                    tier=obj["tier"],
                    observation_date=obs_date,
                    location=obj["location"],
                    notes=obj["notes"]
                )

                if not obs_id:
                    continue

                # Add custom field values
                custom_values = {}
                for field_name in ["object_type", "catalog_number", "right_ascension", "declination",
                                   "magnitude", "equipment", "seeing_conditions", "light_pollution",
                                   "exposure_details", "processing_software"]:
                    if field_name in obj and field_name in astro_field_mapping:
                        custom_values[astro_field_mapping[field_name]] = obj[field_name]

                if custom_values:
                    ObservationRepository.set_observation_custom_fields(
                        session,
                        obs_id,
                        custom_values
                    )

                # Add appropriate tags based on object type and conditions
                obs_tags = []

                # Object type tags
                if obj.get("object_type") == "galaxy":
                    obs_tags.append(tag_ids.get("Galaxy"))
                elif obj.get("object_type") == "nebula":
                    obs_tags.append(tag_ids.get("Nebula"))
                elif obj.get("object_type") == "star_cluster":
                    obs_tags.append(tag_ids.get("Star Cluster"))
                elif obj.get("object_type") == "planet":
                    obs_tags.append(tag_ids.get("Planet"))

                # Condition tags
                if obj.get("seeing_conditions") in ["good", "excellent"]:
                    obs_tags.append(tag_ids.get("Good Seeing"))
                else:
                    obs_tags.append(tag_ids.get("Poor Seeing"))

                if obj.get("light_pollution", "").startswith(("bortle1", "bortle2", "bortle3")):
                    obs_tags.append(tag_ids.get("Dark Sky"))
                else:
                    obs_tags.append(tag_ids.get("Light Polluted"))

                # Add tags to observation
                if obs_tags:
                    from db.repositories import TagRepository
                    TagRepository.set_observation_tags(session, obs_id, [t for t in obs_tags if t])

            # Commit changes
            session.commit()

            message = (
                "Sample lifelists have been created! You can now explore:\n\n"
                "1. Sample Bird Watching - a wildlife lifelist with observations and custom fields\n"
                "2. Sample Book Collection - a book tracking lifelist\n"
                "3. Sample Astronomy - an astronomy lifelist with celestial objects\n\n"
                "Open them from the sidebar to explore their features."
            )

            QMessageBox.information(self, "Sample Lifelists Created", message)