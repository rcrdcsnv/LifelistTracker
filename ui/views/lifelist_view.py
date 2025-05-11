# ui/views/lifelist_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QLineEdit, QTableView,
                               QHeaderView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PySide6.QtGui import QPixmap

from db.models import Photo


class VirtualObservationModel(QAbstractTableModel):
    """Virtual table model that loads data on demand"""

    def __init__(self, db_manager, photo_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.photo_manager = photo_manager
        self.lifelist_id = None

        # Column configuration
        self.headers = ["", "Entry", "Date", "Location", "Tier"]

        # Cache configuration
        self.cache_size = 100  # Keep 100 rows in memory
        self.fetch_size = 50  # Fetch 50 rows at a time

        # Data cache
        self._cache = {}  # row_index -> row_data
        self._total_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

        # Filter state
        self.filters = {
            'tier': None,
            'search_text': None,
            'tag_ids': []
        }

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows (virtualized)"""
        return self._total_count

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        """Load and return data for the requested cell"""
        if not index.isValid():
            return None

        row = index.row()
        row_data = self._get_row_data(row)
        if not row_data:
            return None

        if role == Qt.DisplayRole:
            return self._get_cell_data(row_data, index.column())
        elif role == Qt.DecorationRole and index.column() == 0:
            return self._get_thumbnail(row_data)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def _get_row_data(self, row):
        """Get row data from cache or database"""
        # Check cache first
        if row in self._cache:
            self._cache_hits += 1
            return self._cache[row]

        self._cache_misses += 1

        # Calculate which batch this row belongs to
        batch_start = (row // self.fetch_size) * self.fetch_size

        # Fetch batch from database
        batch_data = self._fetch_batch(batch_start)

        # Update cache and manage cache size
        for i, data in enumerate(batch_data):
            cache_row = batch_start + i
            self._cache[cache_row] = data

        # Prune cache if it gets too large
        self._prune_cache()

        # Return requested row
        return self._cache.get(row)

    def _fetch_batch(self, start_row):
        """Fetch a batch of observations from database"""
        with self.db_manager.session_scope() as session:
            from db.repositories import ObservationRepository

            observations = ObservationRepository.get_observations_batch(
                session=session,
                lifelist_id=self.lifelist_id,
                offset=start_row,
                limit=self.fetch_size,
                tier=self.filters['tier'],
                search_text=self.filters['search_text'],
                tag_ids=self.filters['tag_ids']
            )

            # Add primary photo IDs
            for obs in observations:
                if (
                    photo := session.query(Photo.id)
                    .filter(
                        Photo.observation_id == obs['id'], Photo.is_primary == True
                    )
                    .first()
                ):
                    obs['photo_id'] = photo.id

            return observations

    def _prune_cache(self):
        """Remove the oldest cache entries to maintain cache size"""
        if len(self._cache) > self.cache_size:
            # Keep middle portion around current view
            items = sorted(self._cache.items())
            keep_count = int(self.cache_size * 0.8)
            start_idx = max(0, len(items) // 2 - keep_count // 2)

            # Create new cache with kept items
            new_cache = {}
            for i in range(start_idx, min(start_idx + keep_count, len(items))):
                new_cache[items[i][0]] = items[i][1]

            self._cache = new_cache

    def _update_total_count(self):
        """Update the total count of observations"""
        if not self.lifelist_id:
            self._total_count = 0
            return

        with self.db_manager.session_scope() as session:
            from db.repositories import ObservationRepository
            self._total_count = ObservationRepository.count_observations(
                session=session,
                lifelist_id=self.lifelist_id,
                tier=self.filters['tier'],
                search_text=self.filters['search_text'],
                tag_ids=self.filters['tag_ids']
            )

    def _get_cell_data(self, row_data, column):
        """Extract cell data for display"""
        if column == 0:  # Thumbnail column
            return None
        elif column == 1:  # Entry name
            return row_data["entry_name"]
        elif column == 2:  # Date
            return row_data["date"].strftime("%Y-%m-%d") if row_data["date"] else ""
        elif column == 3:  # Location
            return row_data["location"] or ""
        elif column == 4:  # Tier
            return row_data["tier"] or ""
        return None

    def _get_thumbnail(self, row_data):
        """Load thumbnail for row"""
        if not row_data.get("photo_id"):
            return None

        if thumbnail := self.photo_manager.get_photo_thumbnail(
            row_data["lifelist_id"], row_data["id"], row_data["photo_id"], "xs"
        ):
            from PIL.ImageQt import ImageQt
            qimage = ImageQt(thumbnail)
            return QPixmap.fromImage(qimage)

        return None

    def apply_filters(self, tier=None, search_text=None, tag_ids=None):
        """Apply new filters and refresh data"""
        # Clear cache when filters change
        self._cache.clear()

        # Update filters
        self.filters['tier'] = tier
        self.filters['search_text'] = search_text
        self.filters['tag_ids'] = tag_ids or []

        # Update total count
        self._update_total_count()

        # Notify view of data change
        self.modelReset.emit()

    def set_lifelist(self, lifelist_id):
        """Set the lifelist ID and reset data"""
        self.lifelist_id = lifelist_id
        self._cache.clear()
        self._update_total_count()
        self.modelReset.emit()


class VirtualScrollTableView(QTableView):
    """Enhanced table view with scroll position tracking"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Enable smooth scrolling
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        # Track scroll events
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # Preload buffer
        self.preload_buffer = 10  # Preload 10 rows above/below visible area

    def _on_scroll(self):
        """Handle scroll events for preloading"""
        # Get visible rows
        visible_top = self.rowAt(0)
        visible_bottom = self.rowAt(self.height() - 1)

        visible_top = max(visible_top, 0)
        if visible_bottom < 0:
            visible_bottom = self.model().rowCount() - 1

        # Calculate preload range
        preload_start = max(0, visible_top - self.preload_buffer)
        preload_end = min(self.model().rowCount() - 1, visible_bottom + self.preload_buffer)

        # Trigger preloading in background if needed
        if hasattr(self.model(), '_preload_range'):
            self.model()._preload_range(preload_start, preload_end)


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

        # Search box with debouncing
        filter_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entries...")
        # Remove direct connection, add debounced search instead
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

        # Virtual scrolling table view
        self.table_view = VirtualScrollTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_view.setColumnWidth(0, 60)

        # Create virtual model
        self.observation_model = VirtualObservationModel(self.db_manager, self.photo_manager)
        self.table_view.setModel(self.observation_model)

        # Connect signals
        self.table_view.doubleClicked.connect(self._on_observation_double_clicked)

        layout.addWidget(self.table_view)

        # Add status bar for cache info
        self.status_bar = QLabel()
        layout.addWidget(self.status_bar)

        # Set up debounced search
        self._setup_search_debouncing()

        # Update status periodically
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(5000)  # Update every 5 seconds

    def _setup_search_debouncing(self):
        """Set up search with debouncing for smooth virtual scrolling"""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_filters)

        # Connect search box with debouncing
        self.search_box.textChanged.connect(
            lambda: self.search_timer.start(300)  # 300ms delay
        )

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

        # Set lifelist in model
        self.observation_model.set_lifelist(lifelist_id)

    def _load_tiers(self, session, lifelist_id):
        """Load tiers for the tier filter dropdown"""
        from db.repositories import LifelistRepository
        tiers = ["All"] + LifelistRepository.get_lifelist_tiers(session, lifelist_id)

        # Update combobox
        self.tier_combo.clear()
        self.tier_combo.addItems(tiers)
        self.current_tier = "All"

    def _apply_filters(self):
        """Apply filters to virtual model"""
        tier = self.current_tier if self.current_tier != "All" else None
        search_text = self.search_box.text().strip()

        # Apply filters to model
        self.observation_model.apply_filters(
            tier=tier,
            search_text=search_text,
            tag_ids=self.selected_tags
        )

    def _update_status(self):
        """Update status bar with cache statistics"""
        if hasattr(self.observation_model, '_cache_hits'):
            total_requests = self.observation_model._cache_hits + self.observation_model._cache_misses
            hit_rate = (self.observation_model._cache_hits / total_requests * 100) if total_requests > 0 else 0

            status_text = (
                f"Items: {self.observation_model._total_count} | "
                f"Cache: {len(self.observation_model._cache)} | "
                f"Hit rate: {hit_rate:.1f}%"
            )
            self.status_bar.setText(status_text)

    def _on_observation_double_clicked(self, index):
        """Handle observation double-click"""
        row = index.row()
        if row_data := self.observation_model._get_row_data(row):
            self.main_window.show_observation(row_data["id"])

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
        self._apply_filters()

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