# views/observation_view.py
"""
Observation view - Display observation details
"""
import tkinter as tk
import customtkinter as ctk

from LifelistTracker.navigation_controller import NavigationController
from LifelistTracker.viewmodels.observation_viewmodel import ObservationViewModel
from LifelistTracker.views.utils import create_scrollable_container

class ObservationView:
    """
    UI Component for displaying observation details
    """

    def __init__(self, controller: NavigationController, viewmodel: ObservationViewModel):
        """
        Initialize the observation view

        Args:
            controller: Navigation controller
            viewmodel: Observation ViewModel
        """
        self.controller = controller
        self.viewmodel = viewmodel
        self.content_frame = None

        # Register for viewmodel state changes
        self.viewmodel.register_state_change_callback(self.on_viewmodel_changed)

    def show(self, observation_id=None, **kwargs):
        """
        Display details for an observation

        Args:
            observation_id: ID of the observation to display (optional)
            **kwargs: Additional keyword arguments
        """
        # Get content frame from kwargs
        self.content_frame = kwargs.get('content_frame')
        if not self.content_frame:
            return

        # Load observation from viewmodel
        if observation_id:
            success = self.viewmodel.load_observation(observation_id)
            if success:
                self.display_observation()
            else:
                self.display_error("Observation not found")
        else:
            self.display_error("No observation specified")

    def on_viewmodel_changed(self):
        """Handle viewmodel state changes by refreshing the view"""
        if self.content_frame and self.viewmodel.current_observation:
            self.display_observation()

    def display_observation(self):
        """Display the current observation"""
        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create the detail container
        detail_container = ctk.CTkFrame(self.content_frame)
        detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas, detail_frame = create_scrollable_container(detail_container)

        # Get the current observation from viewmodel
        observation = self.viewmodel.current_observation
        if not observation:
            self.display_error("Observation not found")
            return

        # Photos carousel at the top
        self._create_photo_gallery(detail_frame)

        # Header with species name
        species_name = observation.species_name
        title_label = ctk.CTkLabel(
            detail_frame,
            text=species_name,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=15)

        # Details section
        self._create_details_section(detail_frame)

        # Custom fields
        if observation.custom_field_values:
            self._create_custom_fields_section(detail_frame)

        # Tags
        if observation.tags:
            self._create_tags_section(detail_frame)

        # Action buttons
        self._create_action_buttons(detail_frame)

    def display_error(self, message):
        """Display an error message"""
        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create error container
        error_container = ctk.CTkFrame(self.content_frame)
        error_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Display error message
        error_label = ctk.CTkLabel(
            error_container,
            text=message,
            font=ctk.CTkFont(size=16)
        )
        error_label.pack(pady=20)

        # Back button
        back_btn = ctk.CTkButton(
            error_container,
            text="Back to Lifelist",
            command=lambda: self.controller.open_lifelist(self.viewmodel.current_observation.lifelist_id if self.viewmodel.current_observation else None)
        )
        back_btn.pack(pady=10)

    def _create_photo_gallery(self, parent):
        """
        Create a photo gallery for the observation

        Args:
            parent: Parent widget
        """
        if not self.viewmodel.photo_images:
            return

        photos_frame = ctk.CTkFrame(parent)
        photos_frame.pack(fill=tk.X, padx=20, pady=10)

        # Show primary photo larger
        primary_photo = None
        for photo, photo_img in self.viewmodel.photo_images:
            if photo.is_primary:
                primary_photo = (photo, photo_img)
                break

        if not primary_photo and self.viewmodel.photo_images:
            primary_photo = self.viewmodel.photo_images[0]

        if primary_photo:
            _, photo_img = primary_photo
            photo_label = ctk.CTkLabel(photos_frame, text="", image=photo_img)
            photo_label.pack(pady=10)

        # Thumbnails row
        if len(self.viewmodel.photo_thumbnails) > 1:
            thumbnails_frame = ctk.CTkFrame(photos_frame)
            thumbnails_frame.pack(fill=tk.X, pady=10)

            for photo, thumbnail in self.viewmodel.photo_thumbnails:
                thumb_frame = ctk.CTkFrame(thumbnails_frame)
                thumb_frame.pack(side=tk.LEFT, padx=5)

                thumb_label = ctk.CTkLabel(thumb_frame, text="", image=thumbnail)
                thumb_label.pack(padx=5, pady=5)

                # Add a primary indicator if this is the primary photo
                if photo.is_primary:
                    primary_label = ctk.CTkLabel(thumb_frame, text="Primary", font=ctk.CTkFont(size=10))
                    primary_label.pack(pady=2)

    def _create_details_section(self, parent):
        """
        Create the details section

        Args:
            parent: Parent widget
        """
        observation = self.viewmodel.current_observation
        if not observation:
            return

        details_frame = ctk.CTkFrame(parent)
        details_frame.pack(fill=tk.X, padx=20, pady=10)

        # Observation details
        details_grid = ctk.CTkFrame(details_frame)
        details_grid.pack(fill=tk.X, pady=10)

        # Date
        date_frame = ctk.CTkFrame(details_grid)
        date_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(date_frame, text="Date:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(date_frame, text=observation.observation_date or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Location
        location_frame = ctk.CTkFrame(details_grid)
        location_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(location_frame, text="Location:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(location_frame, text=observation.location or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Coordinates
        if observation.latitude and observation.longitude:
            coords_frame = ctk.CTkFrame(details_grid)
            coords_frame.pack(fill=tk.X, pady=2)

            ctk.CTkLabel(coords_frame, text="Coordinates:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            coord_text = f"{observation.latitude}, {observation.longitude}"
            ctk.CTkLabel(coords_frame, text=coord_text).pack(side=tk.LEFT, padx=5)

        # Tier
        tier_frame = ctk.CTkFrame(details_grid)
        tier_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(tier_frame, text=observation.tier or "Not specified").pack(side=tk.LEFT, padx=5)

        # Notes (if any)
        if observation.notes:
            notes_frame = ctk.CTkFrame(details_grid)
            notes_frame.pack(fill=tk.X, pady=5)

            ctk.CTkLabel(notes_frame, text="Notes:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5, anchor="n")

            notes_text = ctk.CTkTextbox(notes_frame, width=400, height=100)
            notes_text.pack(side=tk.LEFT, padx=5, pady=5)
            notes_text.insert("1.0", observation.notes)
            notes_text.configure(state="disabled")  # Make it read-only

    def _create_custom_fields_section(self, parent):
        """
        Create the custom fields section

        Args:
            parent: Parent widget
        """
        custom_fields = self.viewmodel.get_custom_fields()
        if not custom_fields:
            return

        custom_fields_label = ctk.CTkLabel(
            parent,
            text="Custom Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        custom_fields_label.pack(pady=(20, 5))

        custom_fields_frame = ctk.CTkFrame(parent)
        custom_fields_frame.pack(fill=tk.X, padx=20, pady=5)

        for field in custom_fields:
            field_frame = ctk.CTkFrame(custom_fields_frame)
            field_frame.pack(fill=tk.X, pady=2)

            ctk.CTkLabel(field_frame, text=f"{field['field_name']}:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(field_frame, text=field['value'] or "Not specified").pack(side=tk.LEFT, padx=5)

    def _create_tags_section(self, parent):
        """
        Create the tags section

        Args:
            parent: Parent widget
        """
        observation = self.viewmodel.current_observation
        if not observation or not observation.tags:
            return

        tags_label = ctk.CTkLabel(
            parent,
            text="Tags",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        tags_label.pack(pady=(20, 5))

        tags_frame = ctk.CTkFrame(parent)
        tags_frame.pack(fill=tk.X, padx=20, pady=5)

        for tag in observation.tags:
            tag_label = ctk.CTkLabel(
                tags_frame,
                text=tag.name,
                fg_color="gray30",
                corner_radius=10,
                padx=10,
                pady=5
            )
            tag_label.pack(side=tk.LEFT, padx=5, pady=5)

    def _create_action_buttons(self, parent):
        """
        Create action buttons

        Args:
            parent: Parent widget
        """
        observation = self.viewmodel.current_observation
        if not observation:
            return

        buttons_frame = ctk.CTkFrame(parent)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        back_btn = ctk.CTkButton(
            buttons_frame,
            text="Back to Lifelist",
            command=lambda: self.controller.open_lifelist(observation.lifelist_id)
        )
        back_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ctk.CTkButton(
            buttons_frame,
            text="Edit Observation",
            command=lambda: self.edit_observation(observation.id)
        )
        edit_btn.pack(side=tk.RIGHT, padx=5)

    def edit_observation(self, observation_id):
        """
        Edit an observation

        Args:
            observation_id: ID of the observation to edit
        """
        observation = self.viewmodel.current_observation
        if observation:
            self.controller.show_observation_form(
                lifelist_id=observation.lifelist_id,
                observation_id=observation_id
            )