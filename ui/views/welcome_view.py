# ui/views/welcome_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QScrollArea, QSpacerItem,
                               QSizePolicy)
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
        # In a real implementation, this would display sample lifelists
        # For now, just show the lifelist wizard
        self.main_window._show_lifelist_wizard()