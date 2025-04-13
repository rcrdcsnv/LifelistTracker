"""
Observation form - Add and edit observations
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from models.photo_utils import PhotoUtils
from ui.utils import create_scrollable_container, create_labeled_entry


class ObservationForm:
    """
    UI Component for adding and editing observations
    """

    def __init__(self, controller, app_state, db, content_frame):
        """
        Initialize the observation form

        Args:
            controller: Navigation controller
            app_state: Application state manager
            db: Database connection
            content_frame: Content frame for displaying the form
        """
        self.controller = controller
        self.app_state = app_state
        self.db = db
        self.content_frame = content_frame

        # Form state variables
        self.current_observation_id = None
        self.current_lifelist_id = None
        self.photos = []
        self.current_tags = []
        self.suggestion_list = None
        self.showing_suggestions = False
        self.suggestions = []

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
        self.photos_display_frame = None

    def show(self, lifelist_id=None, observation_id=None, species_name=None, **kwargs):
        """
        Display the observation form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation to edit, or None for a new observation
            species_name: Optional species name to pre-fill
            **kwargs: Additional arguments
        """
        # Use current lifelist_id if not provided
        if lifelist_id is None:
            lifelist_id = self.app_state.get_current_lifelist_id()

        if lifelist_id is None:
            # No lifelist selected
            messagebox.showerror("Error", "No lifelist selected")
            return

        self.current_observation_id = observation_id
        self.current_lifelist_id = lifelist_id
        self.photos = []
        self.current_tags = []

        # Clear the content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create the form container
        form_container = ctk.CTkFrame(self.content_frame)
        form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas, form_frame = create_scrollable_container(form_container)

        # Form title
        title_text = "Edit Observation" if observation_id else "Add New Observation"
        title_label = ctk.CTkLabel(
            form_frame,
            text=title_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # Form fields
        self._create_basic_fields(form_frame, species_name)

        # Custom fields
        self._create_custom_fields(form_frame)

        # Tags section
        self._create_tags_section(form_frame)

        # Photos section
        self._create_photos_section(form_frame)

        # Buttons frame
        self._create_action_buttons(form_frame)

        # If editing an existing observation, load its data
        if observation_id:
            self._load_observation_data(observation_id)

    def _create_basic_fields(self, parent, species_name=None):
        """
        Create the basic observation fields

        Args:
            parent: Parent widget
            species_name: Optional species name to pre-fill
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

        if species_name:
            self.species_entry.insert(0, species_name)

        # Suggestion listbox (hidden initially)
        self.suggestion_frame = ctk.CTkFrame(species_input_frame)
        self.suggestion_list = tk.Listbox(self.suggestion_frame, bg="#2b2b2b", fg="white", height=5)
        self.suggestion_list.pack(fill=tk.BOTH, expand=True)

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

        # Location field
        location_frame, self.location_entry = create_labeled_entry(
            form_fields_frame, "Location:", 300)

        # Coordinates fields
        coords_frame = ctk.CTkFrame(form_fields_frame)
        coords_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(coords_frame, text="Coordinates:", width=150).pack(side=tk.LEFT, padx=5)

        self.lat_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Latitude")
        self.lat_entry.pack(side=tk.LEFT, padx=5)

        self.lon_entry = ctk.CTkEntry(coords_frame, width=145, placeholder_text="Longitude")
        self.lon_entry.pack(side=tk.LEFT, padx=5)

        # Tier field
        tier_frame = ctk.CTkFrame(form_fields_frame)
        tier_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150).pack(side=tk.LEFT, padx=5)

        tier_options = self.db.get_lifelist_tiers(self.current_lifelist_id)
        self.tier_var = tk.StringVar(value=tier_options[0] if tier_options else "wild")

        tier_dropdown = ctk.CTkComboBox(tier_frame, values=tier_options, variable=self.tier_var, width=300)
        tier_dropdown.pack(side=tk.LEFT, padx=5)

        # Notes field
        notes_frame = ctk.CTkFrame(form_fields_frame)
        notes_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(notes_frame, text="Notes:", width=150).pack(side=tk.LEFT, padx=5, anchor="n")
        self.notes_text = ctk.CTkTextbox(notes_frame, width=300, height=100)
        self.notes_text.pack(side=tk.LEFT, padx=5)

    def _create_custom_fields(self, parent):
        """
        Create the custom fields section

        Args:
            parent: Parent widget
        """
        custom_fields_label = ctk.CTkLabel(
            parent,
            text="Custom Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        custom_fields_label.pack(pady=(20, 5))

        custom_fields_frame = ctk.CTkFrame(parent)
        custom_fields_frame.pack(fill=tk.X, padx=20, pady=5)

        # Get custom fields for this lifelist
        custom_fields = self.db.get_custom_fields(self.current_lifelist_id)
        self.custom_field_entries = {}

        if custom_fields:
            for field_id, field_name, field_type in custom_fields:
                field_frame = ctk.CTkFrame(custom_fields_frame)
                field_frame.pack(fill=tk.X, pady=5)

                ctk.CTkLabel(field_frame, text=f"{field_name}:", width=150).pack(side=tk.LEFT, padx=5)

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
        else:
            no_fields_label = ctk.CTkLabel(
                custom_fields_frame,
                text="No custom fields defined for this lifelist"
            )
            no_fields_label.pack(pady=10)

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
            command=lambda: self.controller.open_lifelist(self.current_lifelist_id)
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # If editing an existing observation, add a delete button
        if self.current_observation_id:
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

        if not text or len(text) < 2:
            if self.showing_suggestions:
                self.suggestion_frame.pack_forget()
                self.showing_suggestions = False
            return

        # Get active taxonomy
        active_tax = self.db.get_active_taxonomy(self.current_lifelist_id)

        if active_tax:
            # Search the taxonomy
            results = self.db.search_taxonomy(active_tax[0], text)

            if results:
                # Clear current suggestions
                self.suggestion_list.delete(0, tk.END)
                self.suggestions = []

                # Add new suggestions
                for _, scientific_name, common_name, family, _, _ in results:
                    display_name = scientific_name
                    if common_name:
                        display_name = f"{common_name} ({scientific_name})"

                    self.suggestion_list.insert(tk.END, display_name)
                    self.suggestions.append((scientific_name, common_name))

                # Show the suggestion frame if not already showing
                if not self.showing_suggestions:
                    self.suggestion_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
                    self.showing_suggestions = True
            else:
                # No results, hide suggestions
                if self.showing_suggestions:
                    self.suggestion_frame.pack_forget()
                    self.showing_suggestions = False
        else:
            # No active taxonomy, hide suggestions
            if self.showing_suggestions:
                self.suggestion_frame.pack_forget()
                self.showing_suggestions = False

    def _select_suggestion(self, event):
        """
        Select a suggestion from the suggestion list

        Args:
            event: Selection event
        """
        if not self.showing_suggestions:
            return

        # Get selected suggestion
        try:
            index = self.suggestion_list.curselection()[0]
            scientific_name, common_name = self.suggestions[index]

            # Set the species entry to the selected suggestion
            if common_name:
                self.species_entry.delete(0, tk.END)
                self.species_entry.insert(0, common_name)
            else:
                self.species_entry.delete(0, tk.END)
                self.species_entry.insert(0, scientific_name)

            # Hide suggestions
            self.suggestion_frame.pack_forget()
            self.showing_suggestions = False
        except:
            pass

    def _add_tag(self):
        """Add a tag to the current tags list"""
        tag_name = self.tag_entry.get().strip()
        if tag_name and tag_name not in self.current_tags:
            self.current_tags.append(tag_name)
            self.tag_entry.delete(0, tk.END)
            self._update_tag_display()

    def _remove_tag(self, tag_name):
        """
        Remove a tag from the current tags list

        Args:
            tag_name: Name of the tag to remove
        """
        self.current_tags.remove(tag_name)
        self._update_tag_display()

    def _update_tag_display(self):
        """Update the display of current tags"""
        # Clear existing tags
        for widget in self.tag_labels_frame.winfo_children():
            widget.destroy()

        # Add tag labels
        for tag_name in self.current_tags:
            tag_label_frame = ctk.CTkFrame(self.tag_labels_frame)
            tag_label_frame.pack(side=tk.LEFT, padx=2, pady=2)

            tag_label = ctk.CTkLabel(tag_label_frame, text=tag_name, padx=5)
            tag_label.pack(side=tk.LEFT)

            remove_btn = ctk.CTkButton(
                tag_label_frame,
                text="✕",
                width=20,
                height=20,
                command=lambda t=tag_name: self._remove_tag(t)
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
            # Check if this species already has a primary photo
            species_name = self.species_entry.get().strip()
            has_primary = False

            if species_name and self.current_lifelist_id:
                has_primary = self.db.species_has_primary_photo(self.current_lifelist_id, species_name)

            # Also check if any photos in the current list are marked as primary
            current_has_primary = any(p.get("is_primary", False) for p in self.photos)

            for path in file_paths:
                # Ensure the path is not already in the list
                if not any(p["path"] == path for p in self.photos):
                    # Extract EXIF data if available
                    lat, lon, taken_date = PhotoUtils.extract_exif_data(path)

                    # Create thumbnail
                    thumbnail = PhotoUtils.resize_image_for_thumbnail(path)

                    # Add to photos list - only set as primary if there's no existing primary
                    # for this species and no primary in the current list
                    self.photos.append({
                        "path": path,
                        "is_primary": not (has_primary or current_has_primary) and len(self.photos) == 0,
                        "thumbnail": thumbnail,
                        "latitude": lat,
                        "longitude": lon,
                        "taken_date": taken_date
                    })

            self._update_photos_display()

    def _set_primary_photo(self, index):
        """
        Set a photo as the primary photo

        Args:
            index: Index of the photo in the photos list
        """
        for i in range(len(self.photos)):
            self.photos[i]["is_primary"] = (i == index)
        self._update_photos_display()

        # Show info about species-level changes
        messagebox.showinfo(
            "Primary Photo Set",
            "This photo will be set as the primary photo for all observations of this species when saved."
        )

    def _remove_photo(self, index):
        """
        Remove a photo from the photos list

        Args:
            index: Index of the photo to remove
        """
        self.photos.pop(index)
        # If we removed the primary photo, set a new one
        if not any(p["is_primary"] for p in self.photos) and self.photos:
            self.photos[0]["is_primary"] = True
        self._update_photos_display()

    def _update_photos_display(self):
        """Update the display of photos"""
        # Clear existing photos
        for widget in self.photos_display_frame.winfo_children():
            widget.destroy()

        # Add photo thumbnails
        for i, photo in enumerate(self.photos):
            photo_frame = ctk.CTkFrame(self.photos_display_frame)
            photo_frame.pack(side=tk.LEFT, padx=5, pady=5)

            if photo["thumbnail"]:
                thumbnail_label = ctk.CTkLabel(photo_frame, text="", image=photo["thumbnail"])
                thumbnail_label.pack(padx=5, pady=5)
                # Keep a reference to prevent garbage collection
                photo["thumbnail_label"] = thumbnail_label

            else:
                thumbnail_label = ctk.CTkLabel(photo_frame, text="No Thumbnail")
                thumbnail_label.pack(padx=5, pady=5)

            # Primary photo indicator/setter
            primary_var = tk.BooleanVar(value=photo["is_primary"])
            primary_check = ctk.CTkCheckBox(
                photo_frame,
                text="Primary",
                variable=primary_var,
                command=lambda idx=i: self._set_primary_photo(idx)
            )
            primary_check.pack(padx=5, pady=2)

            # Remove button
            remove_btn = ctk.CTkButton(
                photo_frame,
                text="Remove",
                width=80,
                fg_color="red3",
                hover_color="red4",
                command=lambda idx=i: self._remove_photo(idx)
            )
            remove_btn.pack(padx=5, pady=2)

    def _load_observation_data(self, observation_id):
        """
        Load data for an existing observation

        Args:
            observation_id: ID of the observation to load
        """
        observation, custom_field_values, obs_tags = self.db.get_observation_details(observation_id)

        if observation:
            self.species_entry.insert(0, observation[2] or "")  # species_name
            if observation[3]:  # observation_date
                self.date_entry.insert(0, observation[3])
            if observation[4]:  # location
                self.location_entry.insert(0, observation[4])
            if observation[5]:  # latitude
                self.lat_entry.insert(0, str(observation[5]))
            if observation[6]:  # longitude
                self.lon_entry.insert(0, str(observation[6]))
            if observation[7]:  # tier
                self.tier_var.set(observation[7])
            if observation[8]:  # notes
                self.notes_text.insert("1.0", observation[8])

        # Load custom field values
        if custom_field_values:
            for field_name, field_type, value in custom_field_values:
                for field_id, entry in self.custom_field_entries.items():
                    if self.db.cursor.execute(
                            "SELECT field_name FROM custom_fields WHERE id = ?",
                            (field_id,)
                    ).fetchone()[0] == field_name:
                        if field_type == "boolean":
                            entry.select() if value == "1" else entry.deselect()
                        else:
                            entry.insert(0, value or "")

        # Load tags
        if obs_tags:
            for tag_id, tag_name in obs_tags:
                self.current_tags.append(tag_name)
            self._update_tag_display()

        # Load photos
        obs_photos = self.db.get_photos(observation_id)
        for photo in obs_photos:
            photo_id, file_path, is_primary, lat, lon, taken_date = photo

            # Create thumbnail
            thumbnail = PhotoUtils.resize_image_for_thumbnail(file_path)

            # Add to photos list
            self.photos.append({
                "id": photo_id,
                "path": file_path,
                "is_primary": bool(is_primary),
                "thumbnail": thumbnail,
                "latitude": lat,
                "longitude": lon,
                "taken_date": taken_date
            })

        self._update_photos_display()

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
        return True

    def _save_observation(self):
        """Save the observation"""
        if not self._validate_fields():
            return

        # Get basic fields
        species = self.species_entry.get().strip()
        observation_date = self.date_entry.get().strip() or None
        location = self.location_entry.get().strip() or None
        latitude = self.lat_entry.get().strip() or None
        longitude = self.lon_entry.get().strip() or None
        tier = self.tier_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip() or None

        # Convert latitude/longitude to float if not None
        if latitude:
            try:
                latitude = float(latitude)
            except ValueError:
                messagebox.showerror("Error", "Latitude must be a number")
                return

        if longitude:
            try:
                longitude = float(longitude)
            except ValueError:
                messagebox.showerror("Error", "Longitude must be a number")
                return

        try:
            if self.current_observation_id:
                # Update existing observation
                success = self.db.update_observation(
                    self.current_observation_id,
                    species,
                    observation_date,
                    location,
                    latitude,
                    longitude,
                    tier,
                    notes
                )

                if not success:
                    messagebox.showerror("Error", "Failed to update observation")
                    return

                obs_id = self.current_observation_id

                # For existing observations, get current photos and remove ones that are no longer in the UI
                current_photos = self.db.get_photos(obs_id)
                current_photo_ids = set(photo[0] for photo in current_photos)
                kept_photo_ids = set(photo.get("id") for photo in self.photos if "id" in photo)

                # Photos to delete = current photos that aren't in the kept photos list
                photos_to_delete = current_photo_ids - kept_photo_ids

                # Delete each photo that was removed
                for photo_id in photos_to_delete:
                    self.db.delete_photo(photo_id)

            else:
                # Create new observation
                obs_id = self.db.add_observation(
                    self.current_lifelist_id,
                    species,
                    observation_date,
                    location,
                    latitude,
                    longitude,
                    tier,
                    notes
                )

                if not obs_id:
                    messagebox.showerror("Error", "Failed to add observation")
                    return

            # Save custom field values
            for field_id, field_entry in self.custom_field_entries.items():
                if isinstance(field_entry, ctk.CTkCheckBox):
                    value = "1" if field_entry.get() else "0"
                else:
                    value = field_entry.get().strip()

                # Delete any existing values
                self.db.cursor.execute(
                    "DELETE FROM observation_custom_fields WHERE observation_id = ? AND field_id = ?",
                    (obs_id, field_id)
                )

                # Insert new value
                if value:
                    self.db.cursor.execute(
                        "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                        (obs_id, field_id, value)
                    )

            # Save tags
            # First, remove all existing tags for this observation
            self.db.cursor.execute(
                "DELETE FROM observation_tags WHERE observation_id = ?",
                (obs_id,)
            )

            # Add the current tags
            for tag_name in self.current_tags:
                tag_id = self.db.add_tag(tag_name)
                self.db.add_tag_to_observation(obs_id, tag_id)

            # Save photos
            species_primary_set = False
            for photo in self.photos:
                if photo.get("is_primary", False):
                    species_primary_set = True

                # New or existing photo handling
                if "id" not in photo:
                    # New photo
                    self.db.add_photo(
                        obs_id,
                        photo["path"],
                        1 if photo["is_primary"] else 0,
                        photo.get("latitude"),
                        photo.get("longitude"),
                        photo.get("taken_date")
                    )
                else:
                    # Update existing photo's primary status if needed
                    if photo["is_primary"]:
                        self.db.set_primary_photo(photo["id"], obs_id)

            # Provide feedback only once if any photo was set as primary
            if species_primary_set:
                messagebox.showinfo(
                    "Primary Photo Updated",
                    "The selected primary photo will now appear for all observations of this species."
                )

            self.db.conn.commit()

            # Return to lifelist view
            self.controller.open_lifelist(self.current_lifelist_id)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _delete_observation(self):
        """Delete the current observation"""
        if not self.current_observation_id:
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this observation? This action cannot be undone."
        )

        if confirm:
            success, photos = self.db.delete_observation(self.current_observation_id)

            if success:
                # Return to the lifelist view
                self.controller.open_lifelist(self.current_lifelist_id)
            else:
                messagebox.showerror("Error", "Failed to delete the observation")