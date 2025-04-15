# views/observation_form.py
"""
Observation form - Add and edit observations
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

from LifelistTracker.navigation_controller import NavigationController
from LifelistTracker.viewmodels.observation_form_viewmodel import ObservationFormViewModel
from LifelistTracker.views.utils import create_scrollable_container, create_labeled_entry

class ObservationForm:
    """
    UI Component for adding and editing observations
    """

    def __init__(self, controller: NavigationController, viewmodel: ObservationFormViewModel):
        """
        Initialize the observation form

        Args:
            controller: Navigation controller
            viewmodel: Observation Form ViewModel
        """
        self.controller = controller
        self.viewmodel = viewmodel
        self.content_frame = None

        # Form widgets references
        self.species_entry = None
        self.date_entry = None
        self.location_entry = None
        self.lat_entry = None
        self.lon_entry = None
        self.tier_var = None
        self.notes_text = None
        self.custom_field_entries = {}
        self.suggestion_frame = None
        self.suggestion_list = None
        self.tag_entry = None
        self.tag_labels_frame = None
        self.photos_display_frame = None

        # Register for viewmodel state changes
        self.viewmodel.register_state_change_callback(self.on_viewmodel_changed)

    def show(self, lifelist_id=None, observation_id=None, species_name=None, **kwargs):
        """
        Display the observation form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation to edit, or None for a new observation
            species_name: Optional species name to pre-fill
            **kwargs: Additional keyword arguments
        """
        # Get content frame from kwargs
        self.content_frame = kwargs.get('content_frame')
        if not self.content_frame:
            return

        # Initialize form in viewmodel
        self.viewmodel.initialize_form(lifelist_id, observation_id, species_name)

        # Display the form
        self.display_form()

    def on_viewmodel_changed(self):
        """Handle viewmodel state changes by refreshing the view"""
        if self.content_frame:
            self.display_form()

    def display_form(self):
        """Display the observation form"""
        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create the form container
        form_container = ctk.CTkFrame(self.content_frame)
        form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas, form_frame = create_scrollable_container(form_container)

        # Form title
        title_text = "Edit Observation" if self.viewmodel.editing_mode else "Add New Observation"
        title_label = ctk.CTkLabel(
            form_frame,
            text=title_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # Form fields
        self._create_basic_fields(form_frame)

        # Custom fields
        self._create_custom_fields(form_frame)

        # Tags section
        self._create_tags_section(form_frame)

        # Photos section
        self._create_photos_section(form_frame)

        # Buttons frame
        self._create_action_buttons(form_frame)

    def _create_basic_fields(self, parent):
        """
        Create the basic observation fields

        Args:
            parent: Parent widget
        """
        form_fields_frame = ctk.CTkFrame(parent)
        form_fields_frame.pack(fill=tk.X, padx=20, pady=10)

        # Species field with auto-suggestion
        species_frame = ctk.CTkFrame(form_fields_frame)
        species_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(species_frame, text="Species Name:", width=150).pack(side=tk.LEFT, padx=5)

        # Create a frame for the species input and suggestion list
        species_input_frame = ctk.CTkFrame(species_frame)
        species_input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.species_entry = ctk.CTkEntry(species_input_frame, width=300)
        self.species_entry.pack(side=tk.TOP, fill=tk.X, pady=2)

        # Set initial value from viewmodel
        self.species_entry.delete(0, tk.END)
        self.species_entry.insert(0, self.viewmodel.species_name)

        # Suggestion listbox (hidden initially)
        self.suggestion_frame = ctk.CTkFrame(species_input_frame)
        self.suggestion_list = tk.Listbox(self.suggestion_frame, bg="#2b2b2b", fg="white", height=5)
        self.suggestion_list.pack(fill=tk.BOTH, expand=True)

        # Show suggestions if needed
        if self.viewmodel.showing_suggestions:
            self.suggestion_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
            self.suggestion_list.delete(0, tk.END)

            for suggestion in self.viewmodel.suggestions:
                self.suggestion_list.insert(tk.END, suggestion["display_name"])

        # Bind events for auto-suggestion
        self.species_entry.bind("<KeyRelease>", self._update_suggestions)
        self.suggestion_list.bind("<ButtonRelease-1>", self._select_suggestion)
        self.suggestion_list.bind("<Return>", self._select_suggestion)

        # Add a button to manage taxonomies
        taxonomy_btn = ctk.CTkButton(
            species_frame,
            text="Manage",
            width=70,
            command=self.controller.show_taxonomy_manager
        )
        taxonomy_btn.pack(side=tk.LEFT, padx=5)

        # Date field
        date_frame, self.date_entry = create_labeled_entry(
            form_fields_frame, "Observation Date:", 300, "YYYY-MM-DD")

        # Set initial value if available
        if self.viewmodel.observation and self.viewmodel.observation.observation_date:
            self.date_entry.insert(0, self.viewmodel.observation.observation_date)

        # Location field
        location_frame, self.location_entry = create_labeled_entry(
            form_fields_frame, "Location:", 300)

        # Set initial value if available
        if self.viewmodel.observation and self.viewmodel.observation.location:
            self.location_entry.insert(0, self.viewmodel.observation.location)

        # Coordinates fields
        coords_frame = ctk.CTkFrame(form_fields_frame)
        coords_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(coords_frame, text="Coordinates:", width=150).pack(side=tk.LEFT, padx=5)

        self.lat_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Latitude")
        self.lat_entry.pack(side=tk.LEFT, padx=5)

        # Set initial value if available
        if self.viewmodel.observation and self.viewmodel.observation.latitude:
            self.lat_entry.insert(0, str(self.viewmodel.observation.latitude))

        self.lon_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Longitude")
        self.lon_entry.pack(side=tk.LEFT, padx=5)

        # Set initial value if available
        if self.viewmodel.observation and self.viewmodel.observation.longitude:
            self.lon_entry.insert(0, str(self.viewmodel.observation.longitude))

        # Tier field
        tier_frame = ctk.CTkFrame(form_fields_frame)
        tier_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150).pack(side=tk.LEFT, padx=5)

        self.tier_var = tk.StringVar()
        if self.viewmodel.observation and self.viewmodel.observation.tier:
            self.tier_var.set(self.viewmodel.observation.tier)
        elif self.viewmodel.tier_options:
            self.tier_var.set(self.viewmodel.tier_options[0])

        tier_dropdown = ctk.CTkComboBox(
            tier_frame,
            values=self.viewmodel.tier_options,
            variable=self.tier_var,
            width=300
        )
        tier_dropdown.pack(side=tk.LEFT, padx=5)

        # Notes field
        notes_frame = ctk.CTkFrame(form_fields_frame)
        notes_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(notes_frame, text="Notes:", width=150).pack(side=tk.LEFT, padx=5, anchor="n")
        self.notes_text = ctk.CTkTextbox(notes_frame, width=300, height=100)
        self.notes_text.pack(side=tk.LEFT, padx=5)

        # Set initial value if available
        if self.viewmodel.observation and self.viewmodel.observation.notes:
            self.notes_text.insert("1.0", self.viewmodel.observation.notes)

    def _create_custom_fields(self, parent):
        """
        Create the custom fields section

        Args:
            parent: Parent widget
        """
        custom_fields = self.viewmodel.custom_fields
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

        self.custom_field_entries = {}

        for field in custom_fields:
            field_frame = ctk.CTkFrame(custom_fields_frame)
            field_frame.pack(fill=tk.X, pady=5)

            field_id = field.get("id")
            field_name = field.get("field_name", "")
            field_type = field.get("field_type", "text")

            ctk.CTkLabel(field_frame, text=f"{field_name}:", width=150).pack(side=tk.LEFT, padx=5)

            # Create appropriate widget for field type
            if field_type == "text":
                field_entry = ctk.CTkEntry(field_frame, width=300)
            elif field_type == "number":
                field_entry = ctk.CTkEntry(field_frame, width=300)
            elif field_type == "date":
                field_entry = ctk.CTkEntry(field_frame, width=300, placeholder_text="YYYY-MM-DD")
            elif field_type == "boolean":
                field_entry = ctk.CTkCheckBox(field_frame, text="")
            else:
                field_entry = ctk.CTkEntry(field_frame, width=300)

            field_entry.pack(side=tk.LEFT, padx=5)
            self.custom_field_entries[field_id] = field_entry

            # Set initial value if available
            if self.viewmodel.observation and self.viewmodel.observation.custom_field_values:
                for field_value in self.viewmodel.observation.custom_field_values:
                    if field_value.get("field_id") == field_id:
                        value = field_value.get("value", "")
                        if field_type == "boolean":
                            if value == "1":
                                field_entry.select()
                        else:
                            field_entry.insert(0, value)

    def _create_tags_section(self, parent):
        """
        Create the tags section

        Args:
            parent: Parent widget
        """
        tags_label = ctk.CTkLabel(
            parent,
            text="Tags",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        tags_label.pack(pady=(20, 5))

        tags_frame = ctk.CTkFrame(parent)
        tags_frame.pack(fill=tk.X, padx=20, pady=5)

        # Tag entry and add button
        tag_entry_frame = ctk.CTkFrame(tags_frame)
        tag_entry_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(tag_entry_frame, text="Add Tag:", width=150).pack(side=tk.LEFT, padx=5)
        self.tag_entry = ctk.CTkEntry(tag_entry_frame, width=200)
        self.tag_entry.pack(side=tk.LEFT, padx=5)

        # Tag display area
        self.tag_labels_frame = ctk.CTkFrame(tags_frame)
        self.tag_labels_frame.pack(fill=tk.X, pady=5)

        # Show existing tags
        for tag_name in self.viewmodel.tags:
            self._add_tag_label(tag_name)

        add_tag_btn = ctk.CTkButton(
            tag_entry_frame,
            text="Add",
            width=80,
            command=self._add_tag
        )
        add_tag_btn.pack(side=tk.LEFT, padx=5)

    def _create_photos_section(self, parent):
        """
        Create the photos section

        Args:
            parent: Parent widget
        """
        photos_label = ctk.CTkLabel(
            parent,
            text="Photos",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        photos_label.pack(pady=(20, 5))

        photos_frame = ctk.CTkFrame(parent)
        photos_frame.pack(fill=tk.X, padx=20, pady=5)

        # Add photos button
        add_photos_btn = ctk.CTkButton(
            photos_frame,
            text="Add Photos",
            command=self._add_photos
        )
        add_photos_btn.pack(pady=10)

        # Photos display area
        self.photos_display_frame = ctk.CTkFrame(photos_frame)
        self.photos_display_frame.pack(fill=tk.X, pady=5)

        # Show existing photos
        self._update_photos_display()

    def _create_action_buttons(self, parent):
        """
        Create action buttons

        Args:
            parent: Parent widget
        """
        buttons_frame = ctk.CTkFrame(parent)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            command=self._cancel
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # If editing an existing observation, add a delete button
        if self.viewmodel.editing_mode:
            delete_btn = ctk.CTkButton(
                buttons_frame,
                text="Delete Observation",
                fg_color="red3",
                hover_color="red4",
                command=self._delete_observation
            )
            delete_btn.pack(side=tk.LEFT, padx=5)

        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=self._save_observation
        )
        save_btn.pack(side=tk.RIGHT, padx=5)

    def _update_suggestions(self, event):
        """
        Update species name suggestions based on input

        Args:
            event: KeyRelease event
        """
        # Get the current text
        text = self.species_entry.get().strip()

        # Update suggestions in viewmodel
        self.viewmodel.update_species_suggestions(text)

        # Update UI based on viewmodel state
        if self.viewmodel.showing_suggestions:
            self.suggestion_list.delete(0, tk.END)
            for suggestion in self.viewmodel.suggestions:
                self.suggestion_list.insert(tk.END, suggestion["display_name"])

            self.suggestion_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        else:
            self.suggestion_frame.pack_forget()

    def _select_suggestion(self, event):
        """
        Select a suggestion from the suggestion list

        Args:
            event: Selection event
        """
        try:
            index = self.suggestion_list.curselection()[0]
            self.viewmodel.select_suggestion(index)

            # Update species entry with selected name
            self.species_entry.delete(0, tk.END)
            self.species_entry.insert(0, self.viewmodel.species_name)

            # Hide suggestions
            self.suggestion_frame.pack_forget()
        except:
            pass

    def _add_tag(self):
        """Add a tag to the current tags list"""
        tag_name = self.tag_entry.get().strip()
        if tag_name:
            self.viewmodel.add_tag(tag_name)
            self.tag_entry.delete(0, tk.END)

    def _add_tag_label(self, tag_name):
        """Add a tag label to the UI"""
        tag_label_frame = ctk.CTkFrame(self.tag_labels_frame)
        tag_label_frame.pack(side=tk.LEFT, padx=2, pady=2)

        tag_label = ctk.CTkLabel(tag_label_frame, text=tag_name, padx=5)
        tag_label.pack(side=tk.LEFT)

        remove_btn = ctk.CTkButton(
            tag_label_frame,
            text="✕",
            width=20,
            height=20,
            command=lambda t=tag_name: self.viewmodel.remove_tag(t)
        )
        remove_btn.pack(side=tk.LEFT)

    def _add_photos(self):
        """Add photos to the observation"""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff")
        ]
        file_paths = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=filetypes
        )

        if file_paths:
            self.viewmodel.add_photos(file_paths)

    def _update_photos_display(self):
        """Update the display of photos"""
        # Clear existing photos
        for widget in self.photos_display_frame.winfo_children():
            widget.destroy()

        # Add photo thumbnails
        for i, photo in enumerate(self.viewmodel.photos):
            photo_frame = ctk.CTkFrame(self.photos_display_frame)
            photo_frame.pack(side=tk.LEFT, padx=5, pady=5)

            if photo.get("thumbnail"):
                thumbnail_label = ctk.CTkLabel(photo_frame, text="", image=photo["thumbnail"])
                thumbnail_label.pack(padx=5, pady=5)
                # Keep a reference to prevent garbage collection
                photo["thumbnail_label"] = thumbnail_label
            else:
                thumbnail_label = ctk.CTkLabel(photo_frame, text="No Thumbnail")
                thumbnail_label.pack(padx=5, pady=5)

            # Primary photo indicator/setter
            primary_var = tk.BooleanVar(value=photo.get("is_primary", False))
            primary_check = ctk.CTkCheckBox(
                photo_frame,
                text="Primary",
                variable=primary_var,
                command=lambda idx=i: self.viewmodel.set_primary_photo(idx)
            )
            primary_check.pack(padx=5, pady=2)

            # Remove button
            remove_btn = ctk.CTkButton(
                photo_frame,
                text="Remove",
                width=80,
                fg_color="red3",
                hover_color="red4",
                command=lambda idx=i: self.viewmodel.remove_photo(idx)
            )
            remove_btn.pack(padx=5, pady=2)

    def _validate_fields(self):
        """
        Validate form fields

        Returns:
            bool: True if fields are valid, False otherwise
        """
        species = self.species_entry.get().strip()
        if not species:
            messagebox.showerror("Error", "Species name is required")
            return False

        # Validate coordinates if entered
        lat = self.lat_entry.get().strip()
        lon = self.lon_entry.get().strip()

        if lat:
            try:
                float(lat)
            except ValueError:
                messagebox.showerror("Error", "Latitude must be a number")
                return False

        if lon:
            try:
                float(lon)
            except ValueError:
                messagebox.showerror("Error", "Longitude must be a number")
                return False

        return True

    def _save_observation(self):
        """Save the observation"""
        if not self._validate_fields():
            return

        # Collect form data
        observation_data = {
            "species_name": self.species_entry.get().strip(),
            "observation_date": self.date_entry.get().strip() or None,
            "location": self.location_entry.get().strip() or None,
            "latitude": float(self.lat_entry.get().strip()) if self.lat_entry.get().strip() else None,
            "longitude": float(self.lon_entry.get().strip()) if self.lon_entry.get().strip() else None,
            "tier": self.tier_var.get(),
            "notes": self.notes_text.get("1.0", tk.END).strip() or None
        }

        # Collect custom field values
        custom_field_values = {}
        for field_id, entry in self.custom_field_entries.items():
            if isinstance(entry, ctk.CTkCheckBox):
                value = "1" if entry.get() else "0"
            else:
                value = entry.get().strip()

            custom_field_values[field_id] = value

        # Save observation via viewmodel
        success = self.viewmodel.save_observation(observation_data, custom_field_values)

        if success:
            # Return to lifelist view
            self.controller.open_lifelist(self.viewmodel.lifelist_id)
        else:
            messagebox.showerror("Error", "Failed to save observation")

    def _delete_observation(self):
        """Delete the current observation"""
        if not self.viewmodel.observation or not self.viewmodel.observation.id:
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this observation? This action cannot be undone."
        )

        if confirm:
            try:
                # Get the observation service from DI container
                from ..di_container import container
                from ..services.observation_service import IObservationService

                observation_service = container.resolve(IObservationService)

                # Delete the observation
                success, _ = observation_service.delete_observation(self.viewmodel.observation.id)

                if success:
                    # Return to the lifelist view
                    self.controller.open_lifelist(self.viewmodel.lifelist_id)
                else:
                    messagebox.showerror("Error", "Failed to delete the observation")

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _cancel(self):
        """Cancel editing and return to lifelist"""
        if self.viewmodel.lifelist_id:
            self.controller.open_lifelist(self.viewmodel.lifelist_id)
        else:
            self.controller.show_welcome()