"""
Main application module - Manages application state and UI components
"""
import tkinter as tk
import customtkinter as ctk

from database_factory import DatabaseFactory
from ui.welcome_view import WelcomeView
from ui.lifelist_view import LifelistView
from ui.observation_form import ObservationForm
from ui.observation_view import ObservationView
from ui.taxonomy_manager import TaxonomyManager
from ui.utils import import_lifelist_dialog, export_lifelist_dialog
from app_state import AppState
from navigation_controller import NavigationController
from config_manager import ConfigManager


class LifelistApp:
    """
    Main application class for Lifelist Manager
    """

    def __init__(self, root):
        """
        Initialize the application

        Args:
            root: Tkinter root window
        """
        self.root = root

        # Get the application configuration
        self.config = ConfigManager.get_instance()

        # Apply configuration
        window_size = self.config.get_window_size()
        self.root.title("Lifelist Manager")
        self.root.geometry(f"{window_size['width']}x{window_size['height']}")

        # Initialize database through factory
        self.db = DatabaseFactory.get_database()

        # Set up the main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create sidebar
        self.sidebar = ctk.CTkFrame(self.main_container, width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Create content area
        self.content = ctk.CTkFrame(self.main_container)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create AppState to manage application state
        self.app_state = AppState(self.db)
        self.app_state.register_state_change_callback(self.setup_sidebar)

        # Create NavigationController for view management
        self.nav_controller = NavigationController(self.content, self.app_state, self.db)

        # Register views with the navigation controller
        self.nav_controller.register_view('welcome_view', WelcomeView)
        self.nav_controller.register_view('lifelist_view', LifelistView)
        self.nav_controller.register_view('observation_view', ObservationView)
        self.nav_controller.register_view('observation_form', ObservationForm)
        self.taxonomy_manager = TaxonomyManager(self.nav_controller, self.db, self.root)

        # Set up the sidebar and show welcome screen
        self.setup_sidebar()
        self.nav_controller.show_welcome()

    def setup_sidebar(self):
        """Set up the sidebar with lifelist buttons and actions"""
        # Clear existing widgets
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # Add title
        sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="My Lifelists",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        sidebar_title.pack(pady=10)

        # Add lifelists
        lifelists = self.db.get_lifelists()

        if lifelists:
            for lifelist in lifelists:
                lifelist_btn = ctk.CTkButton(
                    self.sidebar,
                    text=lifelist[1],
                    command=lambda lid=lifelist[0]: self.nav_controller.open_lifelist(lid)
                )
                lifelist_btn.pack(pady=5, padx=10, fill=tk.X)

        # Add buttons for creating, importing, and exporting lifelists
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray70")
        separator.pack(fill=tk.X, padx=10, pady=15)

        create_btn = ctk.CTkButton(
            self.sidebar,
            text="Create New Lifelist",
            command=self.show_create_lifelist_dialog
        )
        create_btn.pack(pady=5, padx=10, fill=tk.X)

        import_btn = ctk.CTkButton(
            self.sidebar,
            text="Import Lifelist",
            command=self.import_lifelist
        )
        import_btn.pack(pady=5, padx=10, fill=tk.X)

        # Only show export if a lifelist is selected
        current_lifelist_id = self.app_state.get_current_lifelist_id()
        if current_lifelist_id:
            export_btn = ctk.CTkButton(
                self.sidebar,
                text="Export Current Lifelist",
                command=self.export_lifelist
            )
            export_btn.pack(pady=5, padx=10, fill=tk.X)

            delete_btn = ctk.CTkButton(
                self.sidebar,
                text="Delete Current Lifelist",
                fg_color="red3",
                hover_color="red4",
                command=self.delete_current_lifelist
            )
            delete_btn.pack(pady=5, padx=10, fill=tk.X)

    def show_create_lifelist_dialog(self):
        """Show dialog to create a new lifelist"""
        # Force the lifelist view to be instantiated if it hasn't been yet
        if 'lifelist_view' in self.nav_controller.views:
            view_info = self.nav_controller.views['lifelist_view']
            if view_info['instance'] is None:
                # We need to instantiate the view first
                view_kwargs = view_info['kwargs'].copy()
                view_kwargs.update({
                    'controller': self.nav_controller,
                    'app_state': self.app_state,
                    'db': self.db,
                    'content_frame': self.content
                })
                view_info['instance'] = view_info['class'](**view_kwargs)

            # Now call the method
            view_info['instance'].show_create_lifelist_dialog()

    def delete_current_lifelist(self):
        """Delete the current lifelist"""
        if 'lifelist_view' in self.nav_controller.views:
            view_info = self.nav_controller.views['lifelist_view']
            if view_info['instance']:
                lifelist_id = self.app_state.get_current_lifelist_id()
                view_info['instance'].delete_lifelist(lifelist_id)

    def import_lifelist(self):
        """Import a lifelist from file"""
        import_lifelist_dialog(self.root, self.db, self.setup_sidebar)

    def export_lifelist(self):
        """Export current lifelist to file"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        lifelist_name = self.app_state.get_lifelist_name()
        export_lifelist_dialog(self.root, self.db, lifelist_id, lifelist_name)