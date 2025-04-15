# views/app.py
"""
Main application module - Manages application state and UI components
"""
import tkinter as tk
from tkinter import messagebox
import atexit
import customtkinter as ctk

from LifelistTracker.services.app_state_service import IAppStateService
from LifelistTracker.services.lifelist_service import ILifelistService
from LifelistTracker.services.config_service import IConfigService
from LifelistTracker.services.database_service import IDatabaseService
from LifelistTracker.viewmodels.lifelist_viewmodel import LifelistViewModel
from LifelistTracker.viewmodels.welcome_viewmodel import WelcomeViewModel
from LifelistTracker.viewmodels.observation_viewmodel import ObservationViewModel
from LifelistTracker.viewmodels.observation_form_viewmodel import ObservationFormViewModel
from LifelistTracker.viewmodels.taxonomy_viewmodel import TaxonomyViewModel
from LifelistTracker.views.welcome_view import WelcomeView
from LifelistTracker.views.lifelist_view import LifelistView
from LifelistTracker.views.observation_form import ObservationForm
from LifelistTracker.views.observation_view import ObservationView
from LifelistTracker.views.taxonomy_manager import TaxonomyManager
from LifelistTracker.views.utils import import_lifelist_dialog, export_lifelist_dialog
from LifelistTracker.navigation_controller import NavigationController
from LifelistTracker.di_container import container


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

        # Get services from dependency injection container
        self.config_service = container.resolve(IConfigService)
        self.app_state_service = container.resolve(IAppStateService)
        self.lifelist_service = container.resolve(ILifelistService)
        self.database_service = container.resolve(IDatabaseService)

        # Apply configuration
        window_size = self.config_service.get_window_size()
        self.root.title("Lifelist Manager")
        self.root.geometry(f"{window_size['width']}x{window_size['height']}")

        # Set up the main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create sidebar
        self.sidebar = ctk.CTkFrame(self.main_container, width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Create content area
        self.content = ctk.CTkFrame(self.main_container)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Register state change callback
        self.app_state_service.register_state_change_callback(self.setup_sidebar)

        # Create NavigationController for view management
        self.nav_controller = NavigationController(self.content, self.app_state_service)

        # Get ViewModels from dependency injection container
        welcome_viewmodel = container.resolve(WelcomeViewModel)
        lifelist_viewmodel = container.resolve(LifelistViewModel)
        observation_viewmodel = container.resolve(ObservationViewModel)
        observation_form_viewmodel = container.resolve(ObservationFormViewModel)
        taxonomy_viewmodel = container.resolve(TaxonomyViewModel)

        # Register views with the navigation controller
        self.nav_controller.register_view('welcome_view', WelcomeView,
                                          controller=self.nav_controller, viewmodel=welcome_viewmodel)
        self.nav_controller.register_view('lifelist_view', LifelistView,
                                          controller=self.nav_controller, viewmodel=lifelist_viewmodel)
        self.nav_controller.register_view('observation_view', ObservationView,
                                          controller=self.nav_controller, viewmodel=observation_viewmodel)
        self.nav_controller.register_view('observation_form', ObservationForm,
                                          controller=self.nav_controller, viewmodel=observation_form_viewmodel)
        self.nav_controller.register_view('taxonomy_view', TaxonomyManager,
                                          controller=self.nav_controller, viewmodel=taxonomy_viewmodel)

        # Set up the sidebar and show welcome screen
        self.setup_sidebar()
        self.nav_controller.show_welcome()

        # Register cleanup function to close database connection
        atexit.register(self.database_service.close)

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
        lifelists = self.lifelist_service.get_all_lifelists()

        if lifelists:
            for lifelist in lifelists:
                lifelist_btn = ctk.CTkButton(
                    self.sidebar,
                    text=lifelist.name,
                    command=lambda lid=lifelist.id: self.nav_controller.open_lifelist(lid)
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
        current_lifelist_id = self.app_state_service.get_current_lifelist_id()
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
        try:
            # Get the lifelist view instance, initializing if needed
            lifelist_view = self.nav_controller.get_view('lifelist_view')
            lifelist_view.show_create_lifelist_dialog()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open create lifelist dialog: {str(e)}")

    def delete_current_lifelist(self):
        """Delete the current lifelist"""
        try:
            lifelist_id = self.app_state_service.get_current_lifelist_id()
            if lifelist_id:
                # Get the lifelist view instance, initializing if needed
                lifelist_view = self.nav_controller.get_view('lifelist_view')
                lifelist_view.delete_lifelist(lifelist_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete lifelist: {str(e)}")

    def import_lifelist(self):
        """Import a lifelist from file"""
        import_lifelist_dialog(self.root, self.lifelist_service, self.setup_sidebar)

    def export_lifelist(self):
        """Export current lifelist to file"""
        lifelist_id = self.app_state_service.get_current_lifelist_id()
        lifelist_name = self.app_state_service.get_lifelist_name()
        export_lifelist_dialog(self.root, self.lifelist_service, lifelist_id, lifelist_name)