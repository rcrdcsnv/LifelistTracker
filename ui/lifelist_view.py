"""
Lifelist view module - Displays and manages lifelist contents
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
import webbrowser
import os
import tempfile

from database_factory import DatabaseFactory
from models.photo_utils import PhotoUtils
from models.map_generator import MapGenerator
from ui.utils import show_message, create_scrollable_container, center_window
from file_utils import FileUtils


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
        self._create_observation_list()

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

        taxonomy_btn = ctk.CTkButton(
            header_frame,
            text="Manage Taxonomies",
            command=self.controller.show_taxonomy_manager
        )
        taxonomy_btn.pack(side=tk.RIGHT, padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text="Add Observation",
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

    def _create_observation_list(self):
        """Create the scrollable observation list container"""
        list_frame = ctk.CTkFrame(self.lifelist_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable frame for observations
        self.observation_list_canvas, self.observations_container = create_scrollable_container(list_frame)

        # Header for the list
        header = ctk.CTkFrame(self.observations_container)
        header.pack(fill=tk.X, padx=5, pady=5)

        ctk.CTkLabel(header, text="Species", width=200).pack(side=tk.LEFT, padx=5)
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
            tag_ids=self.selected_tag_ids if self.selected_tag_ids else None,
            search_term=search_term
        )

        if not observations:
            no_results = ctk.CTkLabel(
                self.observations_container,
                text="No observations found",
                font=ctk.CTkFont(size=14)
            )
            no_results.pack(pady=20)
            return

        # Group observations by species
        species_groups = self._group_observations_by_species(observations)

        # Add each species group to the list
        for species_name, data in species_groups.items():
            self._add_species_row(species_name, data)

    def _group_observations_by_species(self, observations):
        """
        Group observations by species name

        Args:
            observations: List of observation records

        Returns:
            dict: Dictionary of species groups
        """
        species_groups = {}
        for obs in observations:
            obs_id, species_name, obs_date, location, tier = obs

            # If we haven't seen this species yet, create a new entry
            if species_name not in species_groups:
                species_groups[species_name] = {
                    "latest_id": obs_id,
                    "date": obs_date,
                    "location": location,
                    "tier": tier,
                    "observation_ids": [obs_id]
                }
            else:
                # Add this observation ID to the list
                species_groups[species_name]["observation_ids"].append(obs_id)

                # Update date if this observation is more recent
                if not species_groups[species_name]["date"] or (obs_date and (
                        not species_groups[species_name]["date"] or obs_date > species_groups[species_name]["date"])):
                    species_groups[species_name]["date"] = obs_date
                    species_groups[species_name]["location"] = location
                    species_groups[species_name]["latest_id"] = obs_id

                # Update tier if this tier is "higher" in precedence
                # Tier precedence: wild > heard > captive
                tier_precedence = {"wild": 3, "heard": 2, "captive": 1}
                current_tier_value = tier_precedence.get(species_groups[species_name]["tier"], 0)
                new_tier_value = tier_precedence.get(tier, 0)

                if new_tier_value > current_tier_value:
                    species_groups[species_name]["tier"] = tier

        return species_groups

    def _add_species_row(self, species_name, data):
        """
        Add a row for a species group to the observation list

        Args:
            species_name: Name of the species
            data: Dictionary with species data
        """
        obs_id = data["latest_id"]
        obs_date = data["date"]
        location = data["location"]
        tier = data["tier"]
        observation_count = len(data["observation_ids"])
        lifelist_id = self.app_state.get_current_lifelist_id()

        item = ctk.CTkFrame(self.observations_container)
        item.pack(fill=tk.X, padx=5, pady=2)

        # Try to get the primary photo for this species
        photo_thumbnail = None
        species_primary = self.db.get_species_primary_photo(lifelist_id, species_name)

        if species_primary:
            thumbnail = PhotoUtils.resize_image_for_thumbnail(species_primary[1])
            if thumbnail:
                photo_thumbnail = thumbnail

        # Species name (with thumbnail if available)
        species_frame = ctk.CTkFrame(item)
        species_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)

        if photo_thumbnail:
            thumbnail_label = ctk.CTkLabel(species_frame, text="", image=photo_thumbnail)
            thumbnail_label.pack(side=tk.LEFT, padx=5)
            thumbnail_label.image = photo_thumbnail  # Keep a reference

        # Add observation count to species name if there are multiple observations
        display_name = species_name
        if observation_count > 1:
            display_name = f"{species_name} ({observation_count} observations)"

        species_label = ctk.CTkLabel(species_frame, text=display_name, width=180)
        species_label.pack(side=tk.LEFT, padx=5)

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

        # If multiple observations, add a button to view all observations
        if observation_count > 1:
            view_all_btn = ctk.CTkButton(
                actions_frame,
                text="View All",
                width=70,
                command=lambda obs_ids=data["observation_ids"], name=species_name:
                self.view_species_observations(obs_ids, name)
            )
            view_all_btn.pack(side=tk.LEFT, padx=2)
        else:
            # For single observations, keep the normal view button
            view_btn = ctk.CTkButton(
                actions_frame,
                text="View",
                width=70,
                command=lambda o_id=data["latest_id"]: self.view_observation(o_id)
            )
            view_btn.pack(side=tk.LEFT, padx=2)

        # Add button to add a new observation of this species
        add_btn = ctk.CTkButton(
            actions_frame,
            text="Add New",
            width=70,
            command=lambda species=species_name: self.add_new_observation_of_species(species)
        )
        add_btn.pack(side=tk.LEFT, padx=2)

    def view_species_observations(self, observation_ids, species_name):
        """
        View all observations for a species

        Args:
            observation_ids: List of observation IDs
            species_name: Name of the species
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

        title_label = ctk.CTkLabel(
            header_frame,
            text=f"All Observations of {species_name}",
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
            text="Add Observation",
            command=lambda: self.add_new_observation_of_species(species_name)
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

    def add_new_observation_of_species(self, species_name):
        """
        Add a new observation of a specific species

        Args:
            species_name: Name of the species to observe
        """
        lifelist_id = self.app_state.get_current_lifelist_id()
        self.controller.show_observation_form(lifelist_id=lifelist_id, species_name=species_name)

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
            search_term=self.search_var.get() if self.search_var.get() else None,
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

        # Tag checkboxes
        tag_vars = {}

        for tag_id, tag_name in all_tags:
            var = tk.BooleanVar(value=tag_id in selected_tags)
            tag_vars[tag_id] = var

            checkbox = ctk.CTkCheckBox(
                scroll_frame,
                text=tag_name,
                variable=var
            )
            checkbox.pack(anchor="w", pady=2)

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

        ctk.CTkLabel(
            dialog,
            text="Edit Observation Tiers",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        info_text = "Define the observation tiers for this lifelist. The order matters - the first tier is considered highest priority."
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

                    # Destroy the frame
                    frame.destroy()
                    break

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
                messagebox.showerror("Error", "You must define at least one observation tier")
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

        if not observations:
            messagebox.showinfo("Map View", "No observations to display on the map")
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
                webbrowser.open('file://' + os.path.realpath(map_path))
            else:
                # Map creation failed
                messagebox.showinfo("Map Creation Failed",
                                    f"Could not create map: {message}\n\n"
                                    "To fix this issue:\n"
                                    "1. Add latitude/longitude data to your observations, or\n"
                                    "2. Upload photos that contain GPS information in their EXIF data")
        else:
            messagebox.showerror("Error", "An unexpected error occurred while creating the map")

    def show_create_lifelist_dialog(self):
        """Show dialog to create a new lifelist"""
        dialog = ctk.CTkToplevel(self.content_frame.winfo_toplevel())
        dialog.title("Create New Lifelist")
        dialog.geometry("600x500")  # Increased size to accommodate more content
        dialog.transient(self.content_frame.winfo_toplevel())
        dialog.grab_set()

        center_window(dialog)

        # Create a tabbed interface for better organization
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        basic_tab = tabview.add("Basic Info")
        fields_tab = tabview.add("Custom Fields")
        tiers_tab = tabview.add("Observation Tiers")

        # Set the default tab
        tabview.set("Basic Info")

        # Basic Info tab
        ctk.CTkLabel(basic_tab, text="Lifelist Name:").pack(pady=(20, 5))
        name_entry = ctk.CTkEntry(basic_tab, width=300)
        name_entry.pack(pady=5)

        ctk.CTkLabel(basic_tab, text="Taxonomy Reference (optional):").pack(pady=(10, 5))
        taxonomy_entry = ctk.CTkEntry(basic_tab, width=300)
        taxonomy_entry.pack(pady=5)

        # Custom Fields tab
        ctk.CTkLabel(fields_tab, text="Custom Fields:").pack(pady=(15, 5))

        custom_fields_frame = ctk.CTkFrame(fields_tab)
        custom_fields_frame.pack(pady=5, fill=tk.X, padx=20)

        custom_fields = []

        def add_custom_field_row():
            row_frame = ctk.CTkFrame(custom_fields_frame)
            row_frame.pack(pady=2, fill=tk.X)

            field_name = ctk.CTkEntry(row_frame, width=150, placeholder_text="Field Name")
            field_name.pack(side=tk.LEFT, padx=5)

            field_type = ctk.CTkComboBox(row_frame, values=["text", "number", "date", "boolean"])
            field_type.pack(side=tk.LEFT, padx=5)

            remove_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=30,
                command=lambda: remove_field_row(row_frame)
            )
            remove_btn.pack(side=tk.LEFT, padx=5)

            custom_fields.append((field_name, field_type, row_frame))

        def remove_field_row(row):
            for i, (_, _, frame) in enumerate(custom_fields):
                if frame == row:
                    custom_fields.pop(i)
                    break
            row.destroy()

        # Add the first custom field row
        add_custom_field_row()

        # Button to add more custom fields
        add_field_btn = ctk.CTkButton(
            fields_tab,
            text="+ Add Another Field",
            command=add_custom_field_row
        )
        add_field_btn.pack(pady=10)

        # Tiers tab
        ctk.CTkLabel(
            tiers_tab,
            text="Observation Tiers",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        info_text = "Define the observation tiers for your lifelist. The order matters - the first tier is considered highest priority."
        ctk.CTkLabel(tiers_tab, text=info_text, wraplength=400).pack(pady=5)

        # Frame for the tiers list
        tiers_container = ctk.CTkFrame(tiers_tab)
        tiers_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable container for tiers
        tiers_scroll = ctk.CTkScrollableFrame(tiers_container)
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

                    # Destroy the frame
                    frame.destroy()
                    break

        # Add default tiers
        for tier in ["wild", "heard", "captive"]:
            add_tier_entry(tier)

        # Add button for tiers
        add_tier_btn = ctk.CTkButton(
            tiers_tab,
            text="+ Add Tier",
            command=lambda: add_tier_entry()
        )
        add_tier_btn.pack(pady=10)

        # Create lifelist button at the bottom
        buttons_frame = ctk.CTkFrame(dialog)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        def create_lifelist():
            name = name_entry.get().strip()
            taxonomy = taxonomy_entry.get().strip() or None

            if not name:
                messagebox.showerror("Error", "Lifelist name is required")
                return

            # Create the lifelist
            lifelist_id = self.db.create_lifelist(name, taxonomy)

            if lifelist_id is None:
                messagebox.showerror("Error", f"A lifelist named '{name}' already exists")
                return

            # Add custom fields
            for field_name_entry, field_type_combobox, _ in custom_fields:
                field_name = field_name_entry.get().strip()
                field_type = field_type_combobox.get()

                if field_name:
                    self.db.add_custom_field(lifelist_id, field_name, field_type)

            # Add custom tiers
            tiers = []
            for entry, _ in tier_entries:
                tier_name = entry.get().strip()
                if tier_name and tier_name not in tiers:
                    tiers.append(tier_name)

            # Make sure we have at least one tier
            if tiers:
                self.db.set_lifelist_tiers(lifelist_id, tiers)

            # Close dialog and open the new lifelist
            dialog.destroy()
            self.controller.open_lifelist(lifelist_id)

        create_btn = ctk.CTkButton(
            buttons_frame,
            text="Create Lifelist",
            command=create_lifelist
        )
        create_btn.pack(side=tk.RIGHT, padx=5)

    def delete_lifelist(self, lifelist_id):
        """Delete a lifelist"""
        if not lifelist_id:
            return

        lifelist_name = self.app_state.get_lifelist_name()

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the lifelist '{lifelist_name}'? This will delete all observations and cannot be undone."
        )

        if confirm:
            # First offer to export
            export_first = messagebox.askyesno(
                "Export First?",
                "Would you like to export this lifelist before deleting it?"
            )

            if export_first:
                # Export
                from ui.utils import export_lifelist_dialog
                export_lifelist_dialog(self.content_frame.winfo_toplevel(), self.db, lifelist_id, lifelist_name)

            try:
                # Get database without context manager
                db = DatabaseFactory.get_database()

                # Execute delete operation in a transaction
                success = db.execute_transaction(
                    lambda: db.delete_lifelist(lifelist_id)
                )

                if success:
                    messagebox.showinfo("Success", f"Lifelist '{lifelist_name}' has been deleted")
                    self.app_state.set_current_lifelist(None)
                    self.app_state.set_current_observation(None)
                    self.controller.show_welcome()
                else:
                    messagebox.showerror("Error", f"Failed to delete lifelist '{lifelist_name}'")

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")