"""
Main application module - Manages application state and UI components
"""
import tkinter as tk
import customtkinter as ctk

from database import Database
from ui.lifelist_view import LifelistView
from ui.observation_form import ObservationForm
from ui.observation_view import ObservationView
from ui.taxonomy_manager import TaxonomyManager
from ui.utils import import_lifelist_dialog, export_lifelist_dialog
from app_state import AppState
from navigation_controller import NavigationController


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
        self.root.title("Lifelist Manager")
        self.root.geometry("1200x800")

        # Initialize database with context manager support
        self.db = Database()

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

        # Legacy UI components (for backward compatibility)
        self.lifelist_view = LifelistView(self, self.db, self.content)
        self.observation_form = ObservationForm(self, self.db, self.content)
        self.observation_view = ObservationView(self, self.db, self.content)
        self.taxonomy_manager = TaxonomyManager(self, self.db, self.root)

        # Set up the sidebar and show welcome screen
        self.setup_sidebar()
        self.show_welcome_screen()

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
                    command=lambda lid=lifelist[0], lname=lifelist[1]: self.open_lifelist(lid, lname)
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

    def show_welcome_screen(self):
        """Display the welcome screen"""
        # Transition to using the navigation controller
        self.nav_controller.show_welcome()

    def open_lifelist(self, lifelist_id, lifelist_name):
        """
        Open a lifelist and display its contents

        Args:
            lifelist_id: ID of the lifelist to open
            lifelist_name: Name of the lifelist
        """
        # Update app state
        self.app_state.set_current_lifelist(lifelist_id)

        # For backward compatibility
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None

        # Display the lifelist using existing view for now
        self.lifelist_view.display_lifelist(lifelist_id, lifelist_name)

    def show_create_lifelist_dialog(self):
        """Show dialog to create a new lifelist"""
        self.lifelist_view.show_create_lifelist_dialog()

    def delete_current_lifelist(self):
        """Delete the current lifelist"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        self.lifelist_view.delete_lifelist(lifelist_id)

    def import_lifelist(self):
        """Import a lifelist from file"""
        import_lifelist_dialog(self.root, self.db, self.setup_sidebar)

    def export_lifelist(self):
        """Export current lifelist to file"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        lifelist_name = self.app_state.get_lifelist_name()
        export_lifelist_dialog(self.root, self.db, lifelist_id, lifelist_name)

    def get_lifelist_name(self):
        """Get the name of the current lifelist"""
        return self.app_state.get_lifelist_name()


class WelcomeView:
    """
    Welcome screen view component
    """

    def __init__(self, controller, app_state, db, content_frame):
        """
        Initialize the welcome view

        Args:
            controller: Navigation controller
            app_state: Application state manager
            db: Database connection
            content_frame: Content frame for displaying the view
        """
        self.controller = controller
        self.app_state = app_state
        self.db = db
        self.content_frame = content_frame

    def show(self, **kwargs):
        """Display the welcome screen"""
        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create welcome screen
        welcome_frame = ctk.CTkFrame(self.content_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True)

        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text="Welcome to Lifelist Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        welcome_label.pack(pady=20)

        intro_text = """
        Lifelist Manager helps you track and catalog your observations.

        - Create different lifelists for birds, reptiles, astronomical objects, etc.
        - Add custom fields to track specific information for each observation
        - Attach photos to observations and select primary thumbnails
        - Filter observations by tags and tiers
        - View locations on an interactive map

        Get started by selecting or creating a lifelist from the sidebar.
        """

        intro_label = ctk.CTkLabel(
            welcome_frame,
            text=intro_text,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=600
        )
        intro_label.pack(pady=10)