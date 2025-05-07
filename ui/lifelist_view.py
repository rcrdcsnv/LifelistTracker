"""
Lifelist view module - Displays and manages lifelist contents
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import webbrowser
import os
import tempfile

from database_factory import DatabaseFactory
from models.photo_utils import PhotoUtils
from models.map_generator import MapGenerator
from ui.utils import create_scrollable_container, center_window


class LifelistView:
    """
    UI Component for displaying and managing lifelists
    """

    def __init__(self, controller, app_state, db, content_frame):
        """
        Initialize the lifelist view

        Args:
            controller: Navigation controller
            app_state: Application state manager
            db: Database connection
            content_frame: Content frame for displaying lifelist
        """
        self.controller = controller
        self.app_state = app_state
        self.db = db
        self.content_frame = content_frame

        # State
        self.selected_tag_ids = []
        self.lifelist_frame = None
        self.observation_list_canvas = None
        self.observations_container = None
        self.search_var = None
        self.tier_var = None

    def show(self, lifelist_id=None, lifelist_name=None, **kwargs):
        """
        Display the lifelist view

        Args:
            lifelist_id: Optional ID of lifelist to display (defaults to current)
            lifelist_name: Optional name of lifelist
        """
        # Use current lifelist_id if not provided
        if lifelist_id is None:
            lifelist_id = self.app_state.get_current_lifelist_id()

        if lifelist_name is None:
            lifelist_name = self.app_state.get_lifelist_name()

        self.display_lifelist(lifelist_id, lifelist_name)

    def display_lifelist(self, lifelist_id, lifelist_name):
        """
        Display a lifelist with its observations

        Args:
            lifelist_id: ID of the lifelist to display
            lifelist_name: Name of the lifelist
        """
        # Update application state
        self.app_state.set_current_lifelist(lifelist_id)

        # Get entry and observation terms for this lifelist type
        entry_term = self.app_state.get_entry_term()
        observation_term = self.app_state.get_observation_term()

        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create lifelist view
        self.lifelist_frame = ctk.CTkFrame(self.content_frame)
        self.lifelist_frame.pack(fill=tk.BOTH, expand=True)

        # Header with lifelist name and buttons
        self._create_header(lifelist_name)

        # Search and filter section
        self._create_filter_section(lifelist_id)

        # Observation list
        self._create_observation_list(entry_term)

        # Load observations
        self.load_observations()

    def _create_header(self, lifelist_name):
        """Create the header section with title and buttons"""
        header_frame = ctk.CTkFrame(self.lifelist_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        title_label = ctk.CTkLabel(
            header_frame,
            text=lifelist_name,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Get lifelist type name
        _, lifelist_type = self.app_state.get_lifelist_info()
        if lifelist_type:
            type_label = ctk.CTkLabel(
                header_frame,
                text=f"Type: {lifelist_type}",
                font=ctk.CTkFont(size=12),
                fg_color="gray30",
                corner_radius=5
            )
            type_label.pack(side=tk.LEFT, padx=5)

        # Add the map button
        map_btn = ctk.CTkButton(
            header_frame,
            text="View Map",
            command=self.view_map
        )
        map_btn.pack(side=tk.RIGHT, padx=5)

        edit_tiers_btn = ctk.CTkButton(
            header_frame,
            text="Edit Tiers",
            command=self.edit_lifelist_tiers
        )
        edit_tiers_btn.pack(side=tk.RIGHT, padx=5)

        # The Manage Classifications button uses the new name
        classification_btn = ctk.CTkButton(
            header_frame,
            text="Manage Classifications",
            command=self.controller.show_classification_manager
        )
        classification_btn.pack(side=tk.RIGHT, padx=5)

        # Use the appropriate term for observations based on lifelist type
        observation_term = self.app_state.get_observation_term()
        add_btn = ctk.CTkButton(
            header_frame,
            text=f"Add {observation_term.capitalize()}",
            command=self.add_new_observation
        )
        add_btn.pack(side=tk.RIGHT, padx=5)

    def _create_filter_section(self, lifelist_id):
        """Create the search and filter section"""
        filter_frame = ctk.CTkFrame(self.lifelist_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Search box
        self.search_var = tk.StringVar()
        search_label = ctk.CTkLabel(filter_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=5)

        search_entry = ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=200)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Tier filter
        tier_label = ctk.CTkLabel(filter_frame, text="Tier:")
        tier_label.pack(side=tk.LEFT, padx=(15, 5))

        tiers = ["All"] + self.db.get_all_tiers(lifelist_id)
        self.tier_var = tk.StringVar(value="All")
        tier_dropdown = ctk.CTkComboBox(filter_frame, values=tiers, variable=self.tier_var)
        tier_dropdown.pack(side=tk.LEFT, padx=5)

        # Tag filter (multiselect)
        tag_label = ctk.CTkLabel(filter_frame, text="Tags:")
        tag_label.pack(side=tk.LEFT, padx=(15, 5))

        tag_btn = ctk.CTkButton(
            filter_frame,
            text="Select Tags",
            command=self.show_tag_filter_dialog
        )
        tag_btn.pack(side=tk.LEFT, padx=5)

        # Clear filters button
        clear_btn = ctk.CTkButton(
            filter_frame,
            text="Clear Filters",
            command=self.clear_filters
        )
        clear_btn.pack(side=tk.RIGHT, padx=5)

        # Apply filters button
        apply_btn = ctk.CTkButton(
            filter_frame,
            text="Apply Filters",
            command=self.apply_filters
        )
        apply_btn.pack(side=tk.RIGHT, padx=5)

    def _create_observation_list(self, entry_term):
        """
        Create the scrollable observation list container

        Args:
            entry_term: Term used for entries in this lifelist
        """
        list_frame = ctk.CTkFrame(self.lifelist_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable frame for observations
        self.observation_list_canvas, self.observations_container = create_scrollable_container(list_frame)

        # Header for the list
        header = ctk.CTkFrame(self.observations_container)
        header.pack(fill=tk.X, padx=5, pady=5)

        # Use entry_term for the header
        ctk.CTkLabel(header, text=entry_term.capitalize(), width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Date", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Location", width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Tier", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Actions", width=100).pack(side=tk.LEFT, padx=5)

    def on_frame_configure(self, event):
        """Handle frame configuration event to update scrollregion"""
        self.observation_list_canvas.configure(scrollregion=self.observation_list_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Handle canvas configuration event to update window width"""
        self.observation_list_canvas.itemconfig("win", width=event.width)

    def load_observations(self, search_term=None, tier=None):
        """
        Load observations into the list with optional filtering

        Args:
            search_term: Optional search term to filter by
            tier: Optional tier to filter by
        """
        # Clear existing observation items
        for widget in self.observations_container.winfo_children()[1:]:  # Skip the header
            widget.destroy()

        # Get filtered observations
        if tier == "All":
            tier = None

        current_lifelist_id = self.app_state.get_current_lifelist_id()
        observations = self.db.get_observations(
            current_lifelist_id,
            tier=tier,
            tag_ids=self.selected_tag_ids or None,
            search_term=search_term
        )

        # Get lifelist type-specific terminology
        entry_term = self.app_state.get_entry_term()
        observation_term = self.app_state.get_observation_term()

        if not observations:
            no_results = ctk.CTkLabel(
                self.observations_container,
                text=f"No {observation_term}s found",
                font=ctk.CTkFont(size=14)
            )
            no_results.pack(pady=20)
            return

        # Group observations by entry
        entry_groups = self._group_observations_by_entry(observations)

        # Add each entry group to the list
        for entry_name, data in entry_groups.items():
            self._add_entry_row(entry_name, data, entry_term, observation_term)

    def _group_observations_by_entry(self, observations):
        """
        Group observations by entry name

        Args:
            observations: List of observation records

        Returns:
            dict: Dictionary of entry groups
        """
        entry_groups = {}
        for obs in observations:
            obs_id, entry_name, obs_date, location, tier = obs

            # If we haven't seen this entry yet, create a new entry
            if entry_name not in entry_groups:
                entry_groups[entry_name] = {
                    "latest_id": obs_id,
                    "date": obs_date,
                    "location": location,
                    "tier": tier,
                    "observation_ids": [obs_id]
                }
            else:
                # Add this observation ID to the list
                entry_groups[entry_name]["observation_ids"].append(obs_id)

                # Update date if this observation is more recent
                if (
                    not entry_groups[entry_name]["date"]
                    or obs_date
                    and obs_date > entry_groups[entry_name]["date"]
                ):
                    entry_groups[entry_name]["date"] = obs_date
                    entry_groups[entry_name]["location"] = location
                    entry_groups[entry_name]["latest_id"] = obs_id

                # Update tier if this tier is "higher" in precedence
                # Get tiers in order of precedence
                lifelist_id = self.app_state.get_current_lifelist_id()
                tier_precedence = self.db.get_lifelist_tiers(lifelist_id)

                # Find indices for current and new tiers
                current_tier = entry_groups[entry_name]["tier"]
                try:
                    current_idx = tier_precedence.index(current_tier) if current_tier in tier_precedence else len(tier_precedence)
                except ValueError:
                    current_idx = len(tier_precedence)

                try:
                    new_idx = tier_precedence.index(tier) if tier in tier_precedence else len(tier_precedence)
                except ValueError:
                    new_idx = len(tier_precedence)

                # Lower index means higher precedence
                if new_idx < current_idx:
                    entry_groups[entry_name]["tier"] = tier

        return entry_groups

    def _add_entry_row(self, entry_name, data, entry_term, observation_term):
        """
        Add a row for an entry group to the observation list

        Args:
            entry_name: Name of the entry
            data: Dictionary with entry data
            entry_term: Term used for entries in this lifelist
            observation_term: Term used for observations in this lifelist
        """
        obs_id = data["latest_id"]
        obs_date = data["date"]
        location = data["location"]
        tier = data["tier"]
        observation_count = len(data["observation_ids"])
        lifelist_id = self.app_state.get_current_lifelist_id()

        item = ctk.CTkFrame(self.observations_container)
        item.pack(fill=tk.X, padx=5, pady=2)

        # Try to get the primary photo for this entry
        photo_thumbnail = None
        entry_primary = self.db.get_entry_primary_photo(lifelist_id, entry_name)

        if entry_primary:
            if thumbnail := PhotoUtils.resize_image_for_thumbnail(
                entry_primary[1]
            ):
                photo_thumbnail = thumbnail

        # Entry name (with thumbnail if available)
        entry_frame = ctk.CTkFrame(item)
        entry_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)

        if photo_thumbnail:
            thumbnail_label = ctk.CTkLabel(entry_frame, text="", image=photo_thumbnail)
            thumbnail_label.pack(side=tk.LEFT, padx=5)
            thumbnail_label.image = photo_thumbnail  # Keep a reference

        # Add observation count to entry name if there are multiple observations
        display_name = entry_name
        if observation_count > 1:
            display_name = f"{entry_name} ({observation_count} {observation_term}s)"

        entry_label = ctk.CTkLabel(entry_frame, text=display_name, width=180)
        entry_label.pack(side=tk.LEFT, padx=5)

        # Other fields
        date_label = ctk.CTkLabel(item, text=obs_date or "N/A", width=100)
        date_label.pack(side=tk.LEFT, padx=5)

        location_label = ctk.CTkLabel(item, text=location or "N/A", width=200)
        location_label.pack(side=tk.LEFT, padx=5)

        tier_label = ctk.CTkLabel(item, text=tier or "N/A", width=100)
        tier_label.pack(side=tk.LEFT, padx=5)

        # Action buttons
        actions_frame = ctk.CTkFrame(item)
        actions_frame.pack(side=tk.LEFT, padx=5)

        # Unified approach: Always use View button to see details
        view_btn = ctk.CTkButton(
            actions_frame,
            text="View",
            width=70,
            command=lambda obs_ids=data["observation_ids"], name=entry_name:
            self.view_entry_observations(obs_ids, name, entry_term, observation_term)
        )
        view_btn.pack(side=tk.LEFT, padx=2)

        # Direct Edit button if there's just a single observation
        if observation_count == 1:
            edit_btn = ctk.CTkButton(
                actions_frame,
                text="Edit",
                width=70,
                command=lambda o_id=data["observation_ids"][0]: self.edit_observation(o_id)
            )
            edit_btn.pack(side=tk.LEFT, padx=2)


        # Add button to add a new observation of this entry
        add_btn = ctk.CTkButton(
            actions_frame,
            text="Add New",
            width=70,
            command=lambda entry=entry_name: self.add_new_observation_of_entry(entry)
        )
        add_btn.pack(side=tk.LEFT, padx=2)

    def view_entry_observations(self, observation_ids, entry_name, entry_term, observation_term):
        """
        View all observations for an entry

        Args:
            observation_ids: List of observation IDs
            entry_name: Name of the entry
            entry_term: Term used for entries in this lifelist
            observation_term: Term used for observations in this lifelist
        """
        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create container
        container = ctk.CTkFrame(self.content_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header_frame = ctk.CTkFrame(container)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Use appropriate title based on number of observations
        if len(observation_ids) == 1:
            title_text = f"{observation_term.capitalize()} of {entry_name}"
        else:
            title_text = f"All {observation_term}s of {entry_name}"

        title_label = ctk.CTkLabel(
            header_frame,
            text=title_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        back_btn = ctk.CTkButton(
            header_frame,
            text="Back to Lifelist",
            command=lambda: self.controller.open_lifelist(self.app_state.get_current_lifelist_id())
        )
        back_btn.pack(side=tk.RIGHT, padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text=f"Add {observation_term.capitalize()}",
            command=lambda: self.add_new_observation_of_entry(entry_name)
        )
        add_btn.pack(side=tk.RIGHT, padx=5)

        # List frame
        list_frame = ctk.CTkFrame(container)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable frame for observations
        canvas, observations_container = create_scrollable_container(list_frame)

        # Header for the list
        header = ctk.CTkFrame(observations_container)
        header.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkLabel(header, text="Date", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Location", width=200).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Tier", width=100).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header, text="Actions", width=150).pack(side=tk.LEFT, padx=5)

        # Add each observation
        for obs_id in observation_ids:
            observation = self.db.get_observation_details(obs_id)[0]
            if not observation:
                continue

            _, _, _, obs_date, location, _, _, tier, _ = observation

            item = ctk.CTkFrame(observations_container)
            item.pack(fill=tk.X, padx=5, pady=2)

            date_label = ctk.CTkLabel(item, text=obs_date or "N/A", width=100)
            date_label.pack(side=tk.LEFT, padx=5)

            location_label = ctk.CTkLabel(item, text=location or "N/A", width=200)
            location_label.pack(side=tk.LEFT, padx=5)

            tier_label = ctk.CTkLabel(item, text=tier or "N/A", width=100)
            tier_label.pack(side=tk.LEFT, padx=5)

            # Action buttons
            actions_frame = ctk.CTkFrame(item)
            actions_frame.pack(side=tk.LEFT, padx=5)

            view_btn = ctk.CTkButton(
                actions_frame,
                text="View",
                width=70,
                command=lambda o_id=obs_id: self.view_observation(o_id)
            )
            view_btn.pack(side=tk.LEFT, padx=2)

            edit_btn = ctk.CTkButton(
                actions_frame,
                text="Edit",
                width=70,
                command=lambda o_id=obs_id: self.edit_observation(o_id)
            )
            edit_btn.pack(side=tk.LEFT, padx=2)

    def view_observation(self, observation_id):
        """
        View details of a specific observation

        Args:
            observation_id: ID of the observation to view
        """
        self.app_state.set_current_observation(observation_id)
        self.controller.show_observation(observation_id)

    def add_new_observation(self):
        """Add a new observation"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        self.controller.show_observation_form(lifelist_id=lifelist_id)

    def add_new_observation_of_entry(self, entry_name):
        """
        Add a new observation of a specific entry

        Args:
            entry_name: Name of the entry to observe
        """
        lifelist_id = self.app_state.get_current_lifelist_id()
        self.controller.show_observation_form(lifelist_id=lifelist_id, entry_name=entry_name)

    def edit_observation(self, observation_id):
        """
        Edit an existing observation

        Args:
            observation_id: ID of the observation to edit
        """
        lifelist_id = self.app_state.get_current_lifelist_id()
        self.controller.show_observation_form(lifelist_id=lifelist_id, observation_id=observation_id)

    def apply_filters(self):
        """Apply current filters to the observation list"""
        self.load_observations(
            search_term=self.search_var.get() or None,
            tier=self.tier_var.get()
        )

    def clear_filters(self):
        """Clear all filters"""
        self.search_var.set("")
        self.tier_var.set("All")
        self.selected_tag_ids = []
        self.load_observations()

    def show_tag_filter_dialog(self):
        """Show dialog to select tags for filtering"""
        dialog = ctk.CTkToplevel(self.content_frame.winfo_toplevel())
        dialog.title("Select Tags")
        dialog.geometry("300x400")
        dialog.transient(self.content_frame.winfo_toplevel())
        dialog.grab_set()

        center_window(dialog)

        # Get all tags
        all_tags = self.db.get_all_tags()

        # Selected tags
        selected_tags = set(self.selected_tag_ids)

        ctk.CTkLabel(dialog, text="Select Tags to Filter By:", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        # Scrollable frame for tags
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Group tags by category
        tag_by_category = {}
        for tag_id, tag_name, category in all_tags:
            if category not in tag_by_category:
                tag_by_category[category] = []
            tag_by_category[category].append((tag_id, tag_name))

        # Tag checkboxes, grouped by category
        tag_vars = {}

        # Sort categories with None at the end
        sorted_categories = sorted(
            [c for c in tag_by_category if c is not None]
        ) + [None]

        for category in sorted_categories:
            if category not in tag_by_category:
                continue

            # Add category header if it exists
            if category:
                category_label = ctk.CTkLabel(
                    scroll_frame,
                    text=category,
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                category_label.pack(anchor="w", pady=(10, 0))

            # Add tags for this category
            for tag_id, tag_name in tag_by_category[category]:
                var = tk.BooleanVar(value=tag_id in selected_tags)
                tag_vars[tag_id] = var

                checkbox = ctk.CTkCheckBox(
                    scroll_frame,
                    text=tag_name,
                    variable=var
                )
                checkbox.pack(anchor="w", pady=2, padx=(20 if category else 0))

        # Apply button
        def apply_tag_filter():
            selected = [tag_id for tag_id, var in tag_vars.items() if var.get()]
            self.selected_tag_ids = selected
            self.load_observations()
            dialog.destroy()

        apply_btn = ctk.CTkButton(
            dialog,
            text="Apply",
            command=apply_tag_filter
        )
        apply_btn.pack(pady=10)

    def edit_lifelist_tiers(self):
        """Show dialog to edit tiers for the current lifelist"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        if not lifelist_id:
            return

        dialog = ctk.CTkToplevel(self.content_frame.winfo_toplevel())
        dialog.title("Edit Observation Tiers")
        dialog.geometry("400x400")
        dialog.transient(self.content_frame.winfo_toplevel())
        dialog.grab_set()

        center_window(dialog)

        # Get current tiers
        current_tiers = self.db.get_lifelist_tiers(lifelist_id)

        # Get observation term for this lifelist type
        observation_term = self.app_state.get_observation_term()

        ctk.CTkLabel(
            dialog,
            text=f"Edit {observation_term.capitalize()} Tiers",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        info_text = f"Define the {observation_term} tiers for this lifelist. The order matters - the first tier is considered highest priority."
        ctk.CTkLabel(dialog, text=info_text, wraplength=350).pack(pady=5)

        # Frame for the tiers list
        tiers_frame = ctk.CTkFrame(dialog)
        tiers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable container for tiers
        tiers_scroll = ctk.CTkScrollableFrame(tiers_frame)
        tiers_scroll.pack(fill=tk.BOTH, expand=True)

        # List to keep track of tier entries
        tier_entries = []

        def add_tier_entry(tier_name=""):
            """Add a tier entry to the list"""
            row_frame = ctk.CTkFrame(tiers_scroll)
            row_frame.pack(fill=tk.X, pady=2)

            # Entry for tier name
            entry = ctk.CTkEntry(row_frame, width=250)
            entry.pack(side=tk.LEFT, padx=5)
            if tier_name:
                entry.insert(0, tier_name)

            # Up button
            up_btn = ctk.CTkButton(
                row_frame,
                text="↑",
                width=30,
                command=lambda: move_tier_up(row_frame)
            )
            up_btn.pack(side=tk.LEFT, padx=2)

            # Down button
            down_btn = ctk.CTkButton(
                row_frame,
                text="↓",
                width=30,
                command=lambda: move_tier_down(row_frame)
            )
            down_btn.pack(side=tk.LEFT, padx=2)

            # Remove button
            remove_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=30,
                command=lambda: remove_tier(row_frame)
            )
            remove_btn.pack(side=tk.LEFT, padx=2)

            tier_entries.append((entry, row_frame))

            return entry

        def move_tier_up(row_frame):
            """Move a tier entry up in the list"""
            for i, (_, frame) in enumerate(tier_entries):
                if frame == row_frame and i > 0:
                    # Swap with the entry above
                    tier_entries[i], tier_entries[i - 1] = tier_entries[i - 1], tier_entries[i]

                    # Repack all frames to update the order
                    for _, frame in tier_entries:
                        frame.pack_forget()

                    for _, frame in tier_entries:
                        frame.pack(fill=tk.X, pady=2)

                    break

        def move_tier_down(row_frame):
            """Move a tier entry down in the list"""
            for i, (_, frame) in enumerate(tier_entries):
                if frame == row_frame and i < len(tier_entries) - 1:
                    # Swap with the entry below
                    tier_entries[i], tier_entries[i + 1] = tier_entries[i + 1], tier_entries[i]

                    # Repack all frames to update the order
                    for _, frame in tier_entries:
                        frame.pack_forget()

                    for _, frame in tier_entries:
                        frame.pack(fill=tk.X, pady=2)

                    break

        def remove_tier(row_frame):
            """Remove a tier entry from the list"""
            for i, (_, frame) in enumerate(tier_entries):
                if frame == row_frame:
                    # Remove from the list
                    tier_entries.pop(i)
                    break
            row_frame.destroy()

        # Add entries for existing tiers
        for tier in current_tiers:
            add_tier_entry(tier)

        # Add button
        add_btn = ctk.CTkButton(
            dialog,
            text="+ Add Tier",
            command=lambda: add_tier_entry()
        )
        add_btn.pack(pady=10)

        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Save button
        def save_tiers():
            # Get tier names from entries
            tiers = []
            for entry, _ in tier_entries:
                tier_name = entry.get().strip()
                if tier_name and tier_name not in tiers:
                    tiers.append(tier_name)

            # Make sure we have at least one tier
            if not tiers:
                messagebox.showerror("Error", f"You must define at least one {observation_term} tier")
                return

            try:
                # Get database without context manager
                db = DatabaseFactory.get_database()

                # Save tiers to database in a transaction
                success = db.execute_transaction(
                    lambda: db.set_lifelist_tiers(lifelist_id, tiers)
                )

                if success:
                    # Close dialog
                    dialog.destroy()

                    # Reload the lifelist
                    self.controller.open_lifelist(lifelist_id)
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            command=save_tiers
        )
        save_btn.pack(side=tk.RIGHT, padx=5)

    def view_map(self):
        """View a map of all observations in the current lifelist"""
        lifelist_id = self.app_state.get_current_lifelist_id()
        if not lifelist_id:
            return

        # Get all observations for this lifelist
        observations = self.db.get_observations(lifelist_id)

        # Get observation term for this lifelist type
        observation_term = self.app_state.get_observation_term()

        if not observations:
            messagebox.showinfo("Map View", f"No {observation_term}s to display on the map")
            return

        # Create a temporary file for the map
        map_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        map_file.close()

        # Generate the map
        map_generator = MapGenerator()
        result = map_generator.create_observation_map(observations, self.db, map_file.name)

        if isinstance(result, tuple) and len(result) == 2:
            map_path, message = result

            if map_path:
                # Map was created successfully
                messagebox.showinfo("Map Created", message)
                webbrowser.open(f'file://{os.path.realpath(map_path)}')
            else:
                # Map creation failed
                messagebox.showinfo("Map Creation Failed",
                                    f"Could not create map: {message}\n\n"
                                    "To fix this issue:\n"
                                    "1. Add latitude/longitude data to your observations, or\n"
                                    "2. Upload photos that contain GPS information in their EXIF data")
        else:
            messagebox.showerror("Error", "An unexpected error occurred while creating the map")

    def delete_lifelist(self, lifelist_id):
        """Delete a lifelist"""
        if not lifelist_id:
            return

        lifelist_name = self.app_state.get_lifelist_name()

        if confirm := messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the lifelist '{lifelist_name}'? This will delete all observations and cannot be undone.",
        ):
            if export_first := messagebox.askyesno(
                "Export First?",
                "Would you like to export this lifelist before deleting it?",
            ):
                # Export
                from ui.utils import export_lifelist_dialog
                export_lifelist_dialog(self.content_frame.winfo_toplevel(), self.db, lifelist_id, lifelist_name)

            try:
                # Get database without context manager
                db = DatabaseFactory.get_database()

                if success := db.execute_transaction(
                    lambda: db.delete_lifelist(lifelist_id)
                ):
                    messagebox.showinfo("Success", f"Lifelist '{lifelist_name}' has been deleted")
                    self.app_state.set_current_lifelist(None)
                    self.app_state.set_current_observation(None)
                    self.controller.show_welcome()
                else:
                    messagebox.showerror("Error", f"Failed to delete lifelist '{lifelist_name}'")

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")