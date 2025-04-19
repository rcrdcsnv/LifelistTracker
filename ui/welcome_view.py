"""
Welcome view - Main welcome screen for the application
"""
import tkinter as tk
import customtkinter as ctk


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
        # Reset application state
        self.app_state.set_current_lifelist(None)
        self.app_state.set_current_observation(None)

        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

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

        # Check if we have any existing lifelists
        lifelists = self.db.get_lifelists()

        if lifelists:
            recent_label = ctk.CTkLabel(
                button_frame,
                text="Recent Lifelists:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            recent_label.pack(anchor="w", pady=(0, 10))

            # Show up to 3 most recent lifelists
            for i, lifelist in enumerate(lifelists[:3]):
                list_btn = ctk.CTkButton(
                    button_frame,
                    text=lifelist[1],
                    width=300,
                    height=40,
                    command=lambda lid=lifelist[0]: self.controller.open_lifelist(lid)
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

    def _show_create_lifelist_dialog(self):
        """Show dialog to create a new lifelist"""
        # Use the lifelist view to show the create dialog
        lifelist_view = self.controller.views['lifelist_view']['instance']
        if lifelist_view:
            lifelist_view.show_create_lifelist_dialog()

    def _import_lifelist(self):
        """Import a lifelist from file"""
        from ui.utils import import_lifelist_dialog

        # Use the import dialog utility
        import_lifelist_dialog(
            self.content_frame.winfo_toplevel(),
            self.db,
            lambda: self.controller.show_welcome()  # Refresh view after import
        )