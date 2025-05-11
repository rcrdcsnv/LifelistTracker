# ui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QPushButton, QLabel, QStackedWidget, QScrollArea,
                               QFrame, QMessageBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction

from config import Config
from db.base import DatabaseManager
from db.session_manager import SessionManager
from services.photo_manager import PhotoManager
from services.data_service import DataService
from ui.views.welcome_view import WelcomeView
from ui.views.lifelist_view import LifelistView
from ui.views.observation_view import ObservationView
from ui.views.observation_form import ObservationForm


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, config: Config, db_manager: DatabaseManager,
                 photo_manager: PhotoManager, data_service: DataService,
                 session_manager: SessionManager):
        super().__init__()

        self.config = config
        self.db_manager = db_manager
        self.photo_manager = photo_manager
        self.data_service = data_service
        self.session_manager = session_manager

        # Current state
        self.current_lifelist_id = None
        self.current_observation_id = None

        # Set up UI
        self._setup_ui()

        # Show welcome screen initially
        self._show_welcome()

    def _setup_ui(self):
        """Set up the main UI components"""
        # Set window properties
        self.setWindowTitle("Lifelist Tracker")
        window_size = self.config.ui.window_size
        self.resize(window_size.width, window_size.height)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Create sidebar
        self.sidebar = QFrame()
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(300)
        sidebar_layout = QVBoxLayout(self.sidebar)

        # Sidebar header
        sidebar_title = QLabel("My Lifelists")
        sidebar_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sidebar_layout.addWidget(sidebar_title)

        # Sidebar content (scrollable)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        sidebar_layout.addWidget(self.sidebar_scroll)

        # Sidebar widget to hold lifelist buttons
        self.sidebar_content = QWidget()
        self.sidebar_scroll.setWidget(self.sidebar_content)
        self.sidebar_content_layout = QVBoxLayout(self.sidebar_content)

        # Add buttons for creating, importing, and exporting lifelists
        sidebar_layout.addWidget(self._create_action_button("Create New Lifelist",
                                                            self._show_lifelist_wizard))
        sidebar_layout.addWidget(self._create_action_button("Import Lifelist",
                                                            self._import_lifelist))
        self.export_btn = self._create_action_button("Export Current Lifelist",
                                                     self._export_lifelist)
        sidebar_layout.addWidget(self.export_btn)
        self.export_btn.setVisible(False)

        # Create content area
        self.content_area = QStackedWidget()

        # Add to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

        # Create views
        self.welcome_view = WelcomeView(self)
        self.lifelist_view = LifelistView(self, self.photo_manager)
        self.observation_view = ObservationView(self, self.photo_manager)
        self.observation_form = ObservationForm(self, self.photo_manager)

        # Add views to stack
        self.content_area.addWidget(self.welcome_view)
        self.content_area.addWidget(self.lifelist_view)
        self.content_area.addWidget(self.observation_view)
        self.content_area.addWidget(self.observation_form)

        # Create menu bar
        self._setup_menu()

        # Update sidebar
        self._update_sidebar()

    def _create_action_button(self, text, slot):
        """Create a standardized action button for the sidebar"""
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    def _setup_menu(self):
        """Set up the application menu"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")

        # New lifelist action
        new_action = QAction("&New Lifelist", self)
        new_action.triggered.connect(self._show_lifelist_wizard)
        file_menu.addAction(new_action)

        # Import action
        import_action = QAction("&Import Lifelist", self)
        import_action.triggered.connect(self._import_lifelist)
        file_menu.addAction(import_action)

        # Export action
        self.export_action = QAction("&Export Lifelist", self)
        self.export_action.triggered.connect(self._export_lifelist)
        self.export_action.setEnabled(False)
        file_menu.addAction(self.export_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = self.menuBar().addMenu("&View")

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        # Theme actions
        for theme in ["System", "Light", "Dark"]:
            theme_action = QAction(theme, self)
            theme_action.setCheckable(True)
            theme_action.setChecked(self.config.ui.theme == theme)
            theme_action.triggered.connect(lambda checked, t=theme: self._set_theme(t))
            theme_menu.addAction(theme_action)

    def _update_sidebar(self):
        """Update the sidebar with lifelist buttons"""
        # Clear existing widgets
        while self.sidebar_content_layout.count():
            item = self.sidebar_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get lifelists using session manager
        with self.session_manager.list_session() as session:
            from db.repositories import LifelistRepository
            lifelists = LifelistRepository.get_lifelists(session)

        if not lifelists:
            # No lifelists, just show a message
            label = QLabel("No lifelists found.\nCreate one using the button below.")
            label.setAlignment(Qt.AlignCenter)
            self.sidebar_content_layout.addWidget(label)

            # Hide export button
            self.export_btn.setVisible(False)
            self.export_action.setEnabled(False)
            return

        # Group lifelists by type
        lifelists_by_type = {}
        for lifelist_id, name, _, type_name in lifelists:
            if type_name not in lifelists_by_type:
                lifelists_by_type[type_name] = []
            lifelists_by_type[type_name].append((lifelist_id, name))

        # Add a section for each type
        for type_name, type_lifelists in lifelists_by_type.items():
            if type_name:
                # Create a label for this type
                type_label = QLabel(type_name)
                type_label.setStyleSheet(
                    "background-color: #444; color: white; padding: 4px; border-radius: 4px;"
                )
                self.sidebar_content_layout.addWidget(type_label)

            # Add lifelist buttons for this type
            for lid, name in type_lifelists:
                button = QPushButton(name)
                button.clicked.connect(lambda checked, id=lid: self.open_lifelist(id))
                # Highlight if this is the current lifelist
                if lid == self.current_lifelist_id:
                    button.setStyleSheet("background-color: #555;")
                self.sidebar_content_layout.addWidget(button)

        # Add a spacer
        self.sidebar_content_layout.addStretch()

        # Show export button if a lifelist is selected
        self.export_btn.setVisible(self.current_lifelist_id is not None)
        self.export_action.setEnabled(self.current_lifelist_id is not None)

    def _set_theme(self, theme):
        """Set the application theme"""
        # Update config
        self.config.ui.theme = theme
        self.config.save()

        # Show message that the theme will be applied on restart
        QMessageBox.information(
            self,
            "Theme Changed",
            f"The {theme} theme will be applied when you restart the application."
        )

    def _show_welcome(self):
        """Show the welcome screen"""
        self.current_lifelist_id = None
        self.current_observation_id = None
        self.content_area.setCurrentWidget(self.welcome_view)
        self.welcome_view.refresh()
        self._update_sidebar()

    def _show_lifelist_wizard(self):
        """Show the lifelist creation wizard"""
        from ui.dialogs.lifelist_wizard import LifelistWizard

        wizard = LifelistWizard(self, self.db_manager)
        if wizard.exec():
            if lifelist_id := wizard.get_lifelist_id():
                self.open_lifelist(lifelist_id)

    def _import_lifelist(self):
        """Import a lifelist from file"""
        from ui.dialogs.import_dialog import import_lifelist_dialog

        import_lifelist_dialog(self, self.db_manager, self.data_service,
                               lambda: self._update_sidebar())

    def _export_lifelist(self):
        """Export current lifelist to file"""
        from ui.dialogs.export_dialog import export_lifelist_dialog

        if self.current_lifelist_id:
            export_lifelist_dialog(self, self.db_manager, self.data_service,
                                   self.current_lifelist_id)

    @Slot(int)
    def open_lifelist(self, lifelist_id):
        """Open a lifelist view"""
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None
        self.content_area.setCurrentWidget(self.lifelist_view)
        self.lifelist_view.load_lifelist(lifelist_id)
        self._update_sidebar()

    @Slot(int)
    def show_observation(self, observation_id):
        """Show an observation"""
        self.current_observation_id = observation_id
        self.content_area.setCurrentWidget(self.observation_view)
        self.observation_view.load_observation(observation_id)

    @Slot(int, int, str)
    def show_observation_form(self, lifelist_id=None, observation_id=None, entry_name=None):
        """Show the observation form for adding or editing an observation"""
        if lifelist_id is None:
            lifelist_id = self.current_lifelist_id

        if lifelist_id is None:
            QMessageBox.warning(self, "No Lifelist Selected",
                                "Please select a lifelist first.")
            return

        self.current_observation_id = observation_id
        self.content_area.setCurrentWidget(self.observation_form)
        self.observation_form.load_form(lifelist_id, observation_id, entry_name)

    def closeEvent(self, event):
        """Clean up when the application is closing"""
        # Close all view sessions
        for view_id in list(self.session_manager._view_sessions.keys()):
            self.session_manager.close_view_session(view_id)

        # Call parent close event
        super().closeEvent(event)