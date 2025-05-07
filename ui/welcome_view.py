"""
Welcome view - Main welcome screen for the application
"""
import tkinter as tk
import customtkinter as ctk
from tktooltip import ToolTip

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
            text="Welcome to Lifelist Tracker",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        welcome_label.pack(pady=20)

        # Main content
        content_frame = ctk.CTkFrame(welcome_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=20)

        intro_text = """
        Lifelist Tracker helps you track and catalog your collections. From wildlife sightings to books read, 
        music listened to, or places visited, our flexible system adapts to your needs.

        Key features:

        • Create different types of lifelists for wildlife, plants, books, movies, music, travel, and more

        • Add custom fields tailored to your specific collection needs

        • Attach photos to your entries with automatic location detection

        • Organize entries with custom tiers and hierarchical tags

        • View locations on an interactive map

        • Import standard classifications for easier data entry

        Get started by selecting an existing lifelist or creating a new one using our guided wizard!
        """

        intro_label = ctk.CTkLabel(
            content_frame,
            text=intro_text,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=600
        )
        intro_label.pack(pady=10, anchor="w")

        # Two-column layout for lifelist types and recent lifelists
        columns_frame = ctk.CTkFrame(content_frame)
        columns_frame.pack(fill=tk.X, pady=10)

        # Left column: Lifelist types
        left_column = ctk.CTkFrame(columns_frame)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        types_label = ctk.CTkLabel(
            left_column,
            text="Available Lifelist Types:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        types_label.pack(anchor="w", pady=(0, 10))

        # Get all available lifelist types
        lifelist_types = self.db.get_lifelist_types()

        # Create a scrollable frame for types if there are many
        types_scroll = ctk.CTkScrollableFrame(left_column, height=250)
        types_scroll.pack(fill=tk.BOTH, expand=True)

        # Create a button for each lifelist type
        for type_id, type_name, type_desc, _ in lifelist_types:
            type_frame = ctk.CTkFrame(types_scroll)
            type_frame.pack(fill=tk.X, pady=3)

            type_btn = ctk.CTkButton(
                type_frame,
                text=type_name,
                command=lambda tid=type_id: self._create_lifelist_with_type(tid),
                height=30
            )
            type_btn.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.X, expand=True)

            info_label = ctk.CTkLabel(
                type_frame,
                text="ⓘ",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=30
            )
            info_label.pack(side=tk.RIGHT, padx=5)

            # Show tooltip with description on hover
            _create_tooltip(info_label, type_desc)

        # Right column: Recent lifelists
        right_column = ctk.CTkFrame(columns_frame)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        if lifelists := self.db.get_lifelists():
            recent_label = ctk.CTkLabel(
                right_column,
                text="Recent Lifelists:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            recent_label.pack(anchor="w", pady=(0, 10))

            # Group lifelists by type
            lifelists_by_type = {}
            for lifelist in lifelists:
                lifelist_id, name, _, type_name = lifelist
                if type_name not in lifelists_by_type:
                    lifelists_by_type[type_name] = []
                lifelists_by_type[type_name].append((lifelist_id, name))

            # Create a scrollable frame for recent lifelists
            recent_scroll = ctk.CTkScrollableFrame(right_column, height=250)
            recent_scroll.pack(fill=tk.BOTH, expand=True)

            # Add each type group
            for type_name, type_lifelists in lifelists_by_type.items():
                if type_name:
                    # Create a header for this type
                    type_header = ctk.CTkLabel(
                        recent_scroll,
                        text=type_name,
                        font=ctk.CTkFont(size=12),
                        fg_color="gray30",
                        corner_radius=5
                    )
                    type_header.pack(fill=tk.X, pady=(10, 5), padx=5)

                    # Add lifelists for this type
                    for lid, name in type_lifelists:
                        list_btn = ctk.CTkButton(
                            recent_scroll,
                            text=name,
                            width=300,
                            height=30,
                            command=lambda lid=lid: self.controller.open_lifelist(lid)
                        )
                        list_btn.pack(anchor="w", pady=2, padx=15)
        else:
            # If no lifelists exist, show a message
            no_lists_label = ctk.CTkLabel(
                right_column,
                text="You don't have any lifelists yet.\nCreate your first one by selecting a type.",
                font=ctk.CTkFont(size=14),
                justify="center"
            )
            no_lists_label.pack(expand=True, pady=20)

        # Bottom buttons section
        button_frame = ctk.CTkFrame(content_frame)
        button_frame.pack(fill=tk.X, pady=20)

        # Create new lifelist button with wizard
        create_btn = ctk.CTkButton(
            button_frame,
            text="Create New Lifelist (Advanced)",
            width=300,
            height=40,
            command=self._show_lifelist_wizard
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

    def _create_lifelist_with_type(self, type_id):
        """
        Start the creation process for a lifelist of the selected type
        
        Args:
            type_id: ID of the selected lifelist type
        """
        # For simplicity, use the full wizard
        self.controller.show_lifelist_wizard(
            lambda lifelist_id: self.controller.open_lifelist(lifelist_id)
        )

    def _show_lifelist_wizard(self):
        """Show dialog to create a new lifelist with the advanced wizard"""
        self.controller.show_lifelist_wizard(
            lambda lifelist_id: self.controller.open_lifelist(lifelist_id)
        )

    def _import_lifelist(self):
        """Import a lifelist from file"""
        from ui.utils import import_lifelist_dialog

        # Use the import dialog utility
        import_lifelist_dialog(
            self.content_frame.winfo_toplevel(),
            self.db,
            lambda: self.controller.show_welcome()  # Refresh view after import
        )


def _create_tooltip(widget, text):
    """
    Create a simple tooltip for a widget using the tkinter-tooltip library

    Args:
        widget: Widget to attach tooltip to
        text: Tooltip text
    """
    # Create tooltip with a slight delay to avoid flickering
    ToolTip(widget,
            msg=text,
            delay=0.1,  # Small delay for better reliability
            follow=True,  # Follow the mouse
            #wrap_length=250,  # Control text wrapping
            bg="gray20",  # Dark background
            fg="white",  # Light text
            padx=10,
            pady=10)
