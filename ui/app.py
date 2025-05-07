"""
Main application module - Manages application state and UI components
"""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from database_factory import DatabaseFactory
from ui.welcome_view import WelcomeView
from ui.lifelist_view import LifelistView
from ui.observation_form import ObservationForm
from ui.observation_view import ObservationView
from ui.classification_manager import ClassificationManager
from ui.lifelist_wizard import LifelistWizard
from ui.utils import import_lifelist_dialog, export_lifelist_dialog
from app_state import AppState
from navigation_controller import NavigationController
from config_manager import ConfigManager


class LifelistApp:
    """
    Main application class for Lifelist Tracker
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
        self.root.title("Lifelist Tracker")
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
        self.classification_manager = ClassificationManager(self.nav_controller, self.db, self.root)

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

        # Add lifelists, grouped by type
        if lifelists := self.db.get_lifelists():
            # Group lifelists by type
            lifelist_by_type = {}
            for lifelist in lifelists:
                lifelist_id, name, _, type_name = lifelist
                if type_name not in lifelist_by_type:
                    lifelist_by_type[type_name] = []
                lifelist_by_type[type_name].append((lifelist_id, name))

            # Create a section for each type
            for type_name, type_lifelists in lifelist_by_type.items():
                if type_name:  # Skip None type
                    # Create a frame for this type
                    type_frame = ctk.CTkFrame(self.sidebar)
                    type_frame.pack(fill=tk.X, pady=5)

                    # Type header
                    type_label = ctk.CTkLabel(
                        type_frame,
                        text=type_name,
                        font=ctk.CTkFont(size=12),
                        fg_color="gray30",
                        corner_radius=5
                    )
                    type_label.pack(fill=tk.X, padx=10, pady=(5, 2))

                    # Add lifelists for this type
                    for lid, name in type_lifelists:
                        lifelist_btn = ctk.CTkButton(
                            type_frame,
                            text=name,
                            command=lambda lid=lid: self.nav_controller.open_lifelist(lid)
                        )
                        lifelist_btn.pack(pady=2, padx=10, fill=tk.X)

        # Add buttons for creating, importing, and exporting lifelists
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray70")
        separator.pack(fill=tk.X, padx=10, pady=15)

        create_btn = ctk.CTkButton(
            self.sidebar,
            text="Create New Lifelist",
            command=self.show_lifelist_wizard
        )
        create_btn.pack(pady=5, padx=10, fill=tk.X)

        import_btn = ctk.CTkButton(
            self.sidebar,
            text="Import Lifelist",
            command=self.import_lifelist
        )
        import_btn.pack(pady=5, padx=10, fill=tk.X)

        # Only show export if a lifelist is selected
        if current_lifelist_id := self.app_state.get_current_lifelist_id():
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

    def show_lifelist_wizard(self):
        """Show the lifelist creation wizard"""
        try:
            LifelistWizard(self.root, self.nav_controller, self.on_lifelist_created)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open lifelist wizard: {str(e)}")

    def on_lifelist_created(self, lifelist_id):
        """
        Callback for when a new lifelist is created

        Args:
            lifelist_id: ID of the newly created lifelist
        """
        # Refresh sidebar and open the new lifelist
        self.setup_sidebar()
        self.nav_controller.open_lifelist(lifelist_id)

    def delete_current_lifelist(self):
        """Delete the current lifelist"""
        try:
            if lifelist_id := self.app_state.get_current_lifelist_id():
                # Get the lifelist view instance, initializing if needed
                lifelist_view = self.nav_controller.get_view('lifelist_view')
                lifelist_view.delete_lifelist(lifelist_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete lifelist: {str(e)}")

    def import_lifelist(self):
        """Import a lifelist from file"""
        import_lifelist_dialog(self.root, self.db, self.setup_sidebar)

    def export_lifelist(self):
        """Export current lifelist to file"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        lifelist_name = self.app_state.get_lifelist_name()
        export_lifelist_dialog(self.root, self.db, lifelist_id, lifelist_name)