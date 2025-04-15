# views/welcome_view.py
"""
Welcome view - Main welcome screen for the application
"""
import tkinter as tk
import customtkinter as ctk

from LifelistTracker.viewmodels.welcome_viewmodel import WelcomeViewModel
from LifelistTracker.navigation_controller import NavigationController

class WelcomeView:
    """
    Welcome screen view component
    """

    def __init__(self, controller: NavigationController, viewmodel: WelcomeViewModel):
        """
        Initialize the welcome view

        Args:
            controller: Navigation controller
            viewmodel: Welcome ViewModel
        """
        self.controller = controller
        self.viewmodel = viewmodel
        self.content_frame = None

        # Register for viewmodel state changes
        self.viewmodel.register_state_change_callback(self.on_viewmodel_changed)

    def show(self, **kwargs):
        """Display the welcome screen"""
        # Get content frame from kwargs
        self.content_frame = kwargs.get('content_frame')
        if not self.content_frame:
            return

        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Load recent lifelists from viewmodel
        self.viewmodel.load_recent_lifelists()

        # Create welcome screen
        welcome_frame = ctk.CTkFrame(self.content_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True)

        # Logo/Header section
        header_frame = ctk.CTkFrame(welcome_frame)
        header_frame.pack(fill=tk.X, pady=(30, 0))

        welcome_label = ctk.CTkLabel(
            header_frame,
            text="Welcome to Lifelist Manager",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        welcome_label.pack(pady=20)

        # Main content
        content_frame = ctk.CTkFrame(welcome_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=20)

        intro_text = """
        Lifelist Manager helps you track and catalog your observations of species and other collectibles.

        Key features:

        • Create different lifelists for birds, reptiles, plants, astronomical objects, etc.

        • Add custom fields to track specific information for each observation

        • Attach photos to observations and select primary thumbnails

        • Filter observations by tags and observation tiers

        • View locations on an interactive map

        • Import standardized taxonomies for easier data entry

        Get started by selecting or creating a lifelist from the sidebar.
        """

        intro_label = ctk.CTkLabel(
            content_frame,
            text=intro_text,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=600
        )
        intro_label.pack(pady=10, anchor="w")

        # Quick start buttons
        button_frame = ctk.CTkFrame(content_frame)
        button_frame.pack(fill=tk.X, pady=20)

        # Check if we have any recent lifelists
        recent_lifelists = self.viewmodel.recent_lifelists

        if recent_lifelists:
            recent_label = ctk.CTkLabel(
                button_frame,
                text="Recent Lifelists:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            recent_label.pack(anchor="w", pady=(0, 10))

            # Show up to 3 most recent lifelists
            for lifelist in recent_lifelists:
                list_btn = ctk.CTkButton(
                    button_frame,
                    text=lifelist.name,
                    width=300,
                    height=40,
                    command=lambda lid=lifelist.id: self.controller.open_lifelist(lid)
                )
                list_btn.pack(anchor="w", pady=5)

        # Create new lifelist button
        create_btn = ctk.CTkButton(
            button_frame,
            text="+ Create New Lifelist",
            width=300,
            height=40,
            command=self._show_create_lifelist_dialog
        )
        create_btn.pack(anchor="w", pady=(20, 5))

        # Import button
        import_btn = ctk.CTkButton(
            button_frame,
            text="Import Existing Lifelist",
            width=300,
            height=40,
            command=self._import_lifelist
        )
        import_btn.pack(anchor="w", pady=5)

    def on_viewmodel_changed(self):
        """Handle viewmodel state changes by refreshing the view"""
        if self.content_frame:
            self.show(content_frame=self.content_frame)

    def _show_create_lifelist_dialog(self):
        """Show dialog to create a new lifelist"""
        # Use the lifelist view to show the create dialog
        lifelist_view = self.controller.get_view('lifelist_view')
        if lifelist_view:
            lifelist_view.show_create_lifelist_dialog()

    def _import_lifelist(self):
        """Import a lifelist from file"""
        # Get the required services from the lifelist view
        lifelist_view = self.controller.get_view('lifelist_view')
        if lifelist_view:
            lifelist_view.import_lifelist()