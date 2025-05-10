# ui/views/lifelist_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QLineEdit, QTableView,
                               QHeaderView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QIcon, QPixmap, QImage

from typing import List, Dict, Any
from db.base import DatabaseManager
from db.models import Lifelist, LifelistType, Observation, Photo
from services.photo_manager import PhotoManager
from PIL.ImageQt import ImageQt


class ObservationTableModel(QAbstractTableModel):
    """Model for displaying observations in a table"""

    def __init__(self, observations=None, photo_manager=None, parent=None):
        super().__init__(parent)
        self.observations = observations or []
        self.photo_manager = photo_manager
        self.headers = ["", "Entry", "Date", "Location", "Tier", "Actions"]
        self.thumbnails = {}  # Cache for thumbnails

    def rowCount(self, parent=QModelIndex()):
        return len(self.observations)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.observations)):
            return None

        observation = self.observations[index.row()]

        if role == Qt.DisplayRole:
            col = index.column()
            if col == 0:  # Thumbnail column
                return None
            elif col == 1:  # Entry name
                return observation["entry_name"]
            elif col == 2:  # Date
                return observation["date"].strftime("%Y-%m-%d") if observation["date"] else ""
            elif col == 3:  # Location
                return observation["location"] or ""
            elif col == 4:  # Tier
                return observation["tier"] or ""
            elif col == 5:  # Actions
                return None

        elif role == Qt.DecorationRole and index.column() == 0:
            # Return thumbnail
            obs_id = observation["id"]
            if obs_id in self.thumbnails:
                return self.thumbnails[obs_id]

            if self.photo_manager and observation.get("photo_id"):
                thumbnail = self.photo_manager.get_photo_thumbnail(
                    observation["lifelist_id"],
                    obs_id,
                    observation["photo_id"],
                    "xs"
                )

                if thumbnail:
                    # Convert PIL Image to QPixmap
                    qimage = ImageQt(thumbnail)
                    pixmap = QPixmap.fromImage(qimage)
                    self.thumbnails[obs_id] = pixmap
                    return pixmap

            return None

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def setObservations(self, observations):
        self.beginResetModel()
        self.observations = observations
        # Clear thumbnail cache when observations change
        self.thumbnails.clear()
        self.endResetModel()


class LifelistView(QWidget):
    """Widget for displaying and managing lifelists"""

    def __init__(self, main_window, photo_manager):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.db_manager
        self.photo_manager = photo_manager

        # Current lifelist info
        self.lifelist_id = None
        self.lifelist_name = ""
        self.lifelist_type = ""
        self.entry_term = ""
        self.observation_term = ""

        # Filter state
        self.current_tier = "All"
        self.search_text = ""
        self.selected_tags = []

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)

        # Header
        self.header_frame = QWidget()
        header_layout = QHBoxLayout(self.header_frame)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        self.type_label = QLabel("")
        self.type_label.setStyleSheet("background-color: #444; padding: 4px 8px; border-radius: 4px;")
        header_layout.addWidget(self.type_label)

        header_layout.addStretch()

        self.map_btn = QPushButton("View Map")
        self.map_btn.clicked.connect(self._view_map)
        header_layout.addWidget(self.map_btn)

        self.tiers_btn = QPushButton("Edit Tiers")
        self.tiers_btn.clicked.connect(self._edit_tiers)
        header_layout.addWidget(self.tiers_btn)

        self.classify_btn = QPushButton("Manage Classifications")
        self.classify_btn.clicked.connect(self._manage_classifications)
        header_layout.addWidget(self.classify_btn)

        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self._add_observation)
        header_layout.addWidget(self.add_btn)

        layout.addWidget(self.header_frame)

        # Filter bar
        filter_frame = QWidget()
        filter_layout = QHBoxLayout(filter_frame)

        # Search box
        filter_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entries...")
        self.search_box.returnPressed.connect(self._apply_filters)
        filter_layout.addWidget(self.search_box)

        # Tier filter
        filter_layout.addWidget(QLabel("Tier:"))
        self.tier_combo = QComboBox()
        self.tier_combo.currentTextChanged.connect(self._on_tier_changed)
        filter_layout.addWidget(self.tier_combo)

        # Tag filter
        filter_layout.addWidget(QLabel("Tags:"))
        self.tag_btn = QPushButton("Select Tags")
        self.tag_btn.clicked.connect(self._select_tags)
        filter_layout.addWidget(self.tag_btn)

        filter_layout.addStretch()

        # Filter buttons
        self.clear_btn = QPushButton("Clear Filters")
        self.clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.clear_btn)

        self.apply_btn = QPushButton("Apply Filters")
        self.apply_btn.clicked.connect(self._apply_filters)
        filter_layout.addWidget(self.apply_btn)

        layout.addWidget(filter_frame)

        # Table view for observations
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Set thumbnail column size
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_view.setColumnWidth(0, 60)

        # Create model
        self.observation_model = ObservationTableModel(photo_manager=self.photo_manager)
        self.table_view.setModel(self.observation_model)

        # Connect double-click signal
        self.table_view.doubleClicked.connect(self._on_observation_double_clicked)

        layout.addWidget(self.table_view)

    def load_lifelist(self, lifelist_id):
        """Load a lifelist into the view"""
        self.lifelist_id = lifelist_id

        # Get lifelist info
        with self.db_manager.session_scope() as session:
            from db.repositories import LifelistRepository
            lifelist = LifelistRepository.get_lifelist(session, lifelist_id)

            if not lifelist:
                QMessageBox.warning(self, "Error", "Lifelist not found")
                return

            self.lifelist_name = lifelist[1]
            self.lifelist_type = lifelist[4] if lifelist[4] else ""

            # Get terminology based on lifelist type
            from config import Config
            config = Config.load()
            self.entry_term = config.get_entry_term(self.lifelist_type)
            self.observation_term = config.get_observation_term(self.lifelist_type)

            # Update UI
            self.title_label.setText(self.lifelist_name)
            self.type_label.setText(f"Type: {self.lifelist_type}")
            self.add_btn.setText(f"Add {self.observation_term.capitalize()}")

            # Load tiers for filter
            self._load_tiers(session, lifelist_id)

        # Load observations
        self._load_observations()

    def _load_tiers(self, session, lifelist_id):
        """Load tiers for the tier filter dropdown"""
        from db.repositories import LifelistRepository
        tiers = ["All"] + LifelistRepository.get_lifelist_tiers(session, lifelist_id)

        # Update combobox
        self.tier_combo.clear()
        self.tier_combo.addItems(tiers)
        self.current_tier = "All"

    def _load_observations(self):
        """Load observations based on current filters"""
        if not self.lifelist_id:
            return

        with self.db_manager.session_scope() as session:
            # Build query
            query = session.query(
                Observation.id,
                Observation.entry_name,
                Observation.observation_date.label('date'),
                Observation.location,
                Observation.tier,
                Observation.lifelist_id
            )

            # Add filters
            query = query.filter(Observation.lifelist_id == self.lifelist_id)

            if self.current_tier != "All":
                query = query.filter(Observation.tier == self.current_tier)

            if self.search_text:
                search_term = f"%{self.search_text}%"
                query = query.filter(
                    Observation.entry_name.like(search_term) |
                    Observation.notes.like(search_term) |
                    Observation.location.like(search_term)
                )

            if self.selected_tags:
                # Filter by tags (requires all selected tags)
                for tag_id in self.selected_tags:
                    query = query.filter(
                        Observation.tags.any(id=tag_id)
                    )

            # Order by most recent
            query = query.order_by(Observation.observation_date.desc())

            # Execute query
            observations = query.all()

            # Convert to list of dictionaries
            results = []
            for obs in observations:
                entry = {
                    "id": obs.id,
                    "entry_name": obs.entry_name,
                    "date": obs.date,
                    "location": obs.location,
                    "tier": obs.tier,
                    "lifelist_id": obs.lifelist_id,
                    "photo_id": None
                }

                # Get primary photo if available (using first observation for performance)
                photo = session.query(Photo).filter(
                    Photo.observation_id == obs.id,
                    Photo.is_primary == True
                ).first()

                if photo:
                    entry["photo_id"] = photo.id

                results.append(entry)

            # Update model
            self.observation_model.setObservations(results)

            # Adjust "Actions" column width
            self.table_view.setColumnWidth(5, 150)

    def _on_tier_changed(self, tier):
        """Handle tier selection change"""
        self.current_tier = tier

    def _select_tags(self):
        """Show dialog to select tags for filtering"""
        from ui.dialogs.tag_selector import TagSelectorDialog

        dialog = TagSelectorDialog(self, self.db_manager, self.selected_tags)
        if dialog.exec():
            self.selected_tags = dialog.get_selected_tags()
            self._apply_filters()

    def _clear_filters(self):
        """Clear all filters"""
        self.search_box.clear()
        self.tier_combo.setCurrentText("All")
        self.current_tier = "All"
        self.search_text = ""
        self.selected_tags = []
        self._load_observations()

    def _apply_filters(self):
        """Apply current filters"""
        self.search_text = self.search_box.text()
        self._load_observations()

    def _on_observation_double_clicked(self, index):
        """Handle observation double-click"""
        row = index.row()
        observation_id = self.observation_model.observations[row]["id"]
        self.main_window.show_observation(observation_id)

    def _add_observation(self):
        """Add a new observation"""
        self.main_window.show_observation_form(self.lifelist_id)

    def _edit_tiers(self):
        """Show dialog to edit tiers"""
        from ui.dialogs.tier_editor import TierEditorDialog

        dialog = TierEditorDialog(self, self.db_manager, self.lifelist_id, self.observation_term)
        if dialog.exec():
            # Refresh tiers in the dropdown
            with self.db_manager.session_scope() as session:
                self._load_tiers(session, self.lifelist_id)

    def _manage_classifications(self):
        """Show dialog to manage classifications"""
        from ui.dialogs.classification_manager import ClassificationManagerDialog

        dialog = ClassificationManagerDialog(self, self.db_manager, self.lifelist_id, self.entry_term)
        dialog.exec()

    def _view_map(self):
        """Show a map of observations"""
        from ui.dialogs.map_dialog import MapDialog

        dialog = MapDialog(self, self.db_manager, self.lifelist_id, self.observation_term)
        dialog.exec()