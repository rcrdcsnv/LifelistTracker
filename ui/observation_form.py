"""
Observation form - Add and edit observations
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import json

from database_factory import DatabaseFactory
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
        self.entry_entry = None
        self.date_entry = None
        self.location_entry = None
        self.lat_entry = None
        self.lon_entry = None
        self.tier_var = None
        self.notes_text = None
        self.custom_field_entries = {}
        self.suggestion_frame = None
        self.photos_display_frame = None

    def show(self, lifelist_id=None, observation_id=None, entry_name=None, **kwargs):
        """
        Display the observation form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist
            observation_id: ID of the observation to edit, or None for a new observation
            entry_name: Optional entry name to pre-fill
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

        # Get entry and observation terms for this lifelist type
        entry_term = self.app_state.get_entry_term()
        observation_term = self.app_state.get_observation_term()

        # Create the form container
        form_container = ctk.CTkFrame(self.content_frame)
        form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas, form_frame = create_scrollable_container(form_container)

        # Form title
        title_text = f"Edit {observation_term.capitalize()}" if observation_id else f"Add New {observation_term.capitalize()}"
        title_label = ctk.CTkLabel(
            form_frame,
            text=title_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # Form fields
        self._create_basic_fields(form_frame, entry_name, entry_term)

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

    def _create_basic_fields(self, parent, entry_name=None, entry_term="item"):
        """
        Create the basic observation fields

        Args:
            parent: Parent widget
            entry_name: Optional entry name to pre-fill
            entry_term: Term used for entries in this lifelist
        """
        form_fields_frame = ctk.CTkFrame(parent)
        form_fields_frame.pack(fill=tk.X, padx=20, pady=10)

        # Entry field with auto-suggestion
        entry_frame = ctk.CTkFrame(form_fields_frame)
        entry_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(entry_frame, text=f"{entry_term.capitalize()} Name:", width=150).pack(side=tk.LEFT, padx=5)

        # Create a frame for the entry input and suggestion list
        entry_input_frame = ctk.CTkFrame(entry_frame)
        entry_input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.entry_entry = ctk.CTkEntry(entry_input_frame, width=300)
        self.entry_entry.pack(side=tk.TOP, fill=tk.X, pady=2)

        if entry_name:
            self.entry_entry.insert(0, entry_name)

        # Suggestion listbox (hidden initially)
        self.suggestion_frame = ctk.CTkFrame(entry_input_frame)
        self.suggestion_list = tk.Listbox(self.suggestion_frame, bg="#2b2b2b", fg="white", height=5)
        self.suggestion_list.pack(fill=tk.BOTH, expand=True)

        # Bind events for auto-suggestion
        self.entry_entry.bind("<KeyRelease>", self._update_suggestions)
        self.suggestion_list.bind("<ButtonRelease-1>", self._select_suggestion)
        self.suggestion_list.bind("<Return>", self._select_suggestion)

        # Add a button to manage classifications
        manage_btn = ctk.CTkButton(
            entry_frame,
            text="Manage",
            width=70,
            command=self.controller.show_classification_manager
        )
        manage_btn.pack(side=tk.LEFT, padx=5)

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
        self.tier_var = tk.StringVar(value=tier_options[0] if tier_options else "owned")

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
            # Sort fields by display order
            sorted_fields = sorted(custom_fields, key=lambda f: f[5])  # Sort by display_order

            for field in sorted_fields:
                field_id, field_name, field_type, field_options, is_required, display_order, options = field

                # Create a frame for this field
                field_frame = ctk.CTkFrame(custom_fields_frame)
                field_frame.pack(fill=tk.X, pady=5)

                # Add required indicator if field is required
                field_label = f"{field_name}:" + (" *" if is_required else "")

                ctk.CTkLabel(field_frame, text=field_label, width=150).pack(side=tk.LEFT, padx=5)

                # Create different input widgets based on field type
                if field_type == "text":
                    field_entry = ctk.CTkEntry(field_frame, width=300)
                    field_entry.pack(side=tk.LEFT, padx=5)

                elif field_type == "number":
                    field_entry = ctk.CTkEntry(field_frame, width=300)
                    field_entry.pack(side=tk.LEFT, padx=5)

                elif field_type == "date":
                    field_entry = ctk.CTkEntry(field_frame, width=300, placeholder_text="YYYY-MM-DD")
                    field_entry.pack(side=tk.LEFT, padx=5)

                elif field_type == "boolean":
                    field_entry = ctk.CTkCheckBox(field_frame, text="")
                    field_entry.pack(side=tk.LEFT, padx=5)

                elif field_type == "choice" and options:
                    # Create dropdown with options
                    choice_var = tk.StringVar()
                    choice_options = [""]  # Add empty option

                    for option_value, option_label, _ in options:
                        display_text = option_label or option_value
                        choice_options.append(display_text)

                    field_entry = ctk.CTkComboBox(field_frame, values=choice_options, variable=choice_var, width=300)
                    field_entry.pack(side=tk.LEFT, padx=5)

                    # Store both the combobox and the variable
                    self.custom_field_entries[field_id] = (field_entry, choice_var, options)
                    continue  # Skip the default assignment at the end

                elif field_type == "rating":
                    # Parse options
                    max_rating = 5
                    if field_options:
                        try:
                            options_dict = json.loads(field_options) if isinstance(field_options, str) else field_options
                            if "max" in options_dict:
                                max_rating = int(options_dict["max"])
                        except Exception:
                            pass

                    # Create a frame for rating stars
                    rating_frame = ctk.CTkFrame(field_frame)
                    rating_frame.pack(side=tk.LEFT, padx=5)

                    rating_var = tk.IntVar(value=0)
                    rating_buttons = []

                    for i in range(1, max_rating + 1):
                        star_btn = ctk.CTkButton(
                            rating_frame,
                            text="★",
                            width=30,
                            height=30,
                            fg_color="gray30",
                            command=lambda v=i: rating_var.set(v)
                        )
                        star_btn.pack(side=tk.LEFT, padx=1)
                        rating_buttons.append(star_btn)

                    # Update button appearance when rating changes
                    def update_rating_buttons(*args):
                        rating = rating_var.get()
                        for i, btn in enumerate(rating_buttons):
                            if i < rating:
                                btn.configure(fg_color="gold", text_color="black")
                            else:
                                btn.configure(fg_color="gray30", text_color="white")

                    rating_var.trace_add("write", update_rating_buttons)

                    # Store both the buttons and the variable
                    self.custom_field_entries[field_id] = (rating_buttons, rating_var)
                    continue  # Skip the default assignment at the end

                elif field_type == "color":
                    # Parse options
                    colors = []
                    allow_custom = True

                    if field_options:
                        try:
                            options_dict = json.loads(field_options) if isinstance(field_options, str) else field_options
                            if "colors" in options_dict:
                                colors = options_dict["colors"]
                            if "allow_custom" in options_dict:
                                allow_custom = options_dict["allow_custom"]
                        except Exception:
                            pass

                    # Create a frame for color selection
                    color_frame = ctk.CTkFrame(field_frame)
                    color_frame.pack(side=tk.LEFT, padx=5)

                    color_var = tk.StringVar(value="")

                    # Add color swatches if specified
                    if colors:
                        for color in colors[:6]:  # Limit to 6 predefined colors
                            color_btn = ctk.CTkButton(
                                color_frame,
                                text="",
                                width=30,
                                height=30,
                                fg_color=color,
                                command=lambda c=color: color_var.set(c)
                            )
                            color_btn.pack(side=tk.LEFT, padx=1)

                    # Add custom color input if allowed
                    if allow_custom:
                        custom_entry = ctk.CTkEntry(color_frame, width=100, placeholder_text="#RRGGBB")
                        custom_entry.pack(side=tk.LEFT, padx=5)

                        def set_custom_color():
                            color = custom_entry.get().strip()
                            if color:
                                color_var.set(color)

                        apply_btn = ctk.CTkButton(
                            color_frame,
                            text="Apply",
                            width=60,
                            command=set_custom_color
                        )
                        apply_btn.pack(side=tk.LEFT, padx=2)

                        # Store the components
                        self.custom_field_entries[field_id] = (custom_entry, color_var)
                    else:
                        # Just store the variable
                        self.custom_field_entries[field_id] = (None, color_var)

                    continue  # Skip the default assignment at the end

                else:
                    # Default to text input for unknown types
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

        # Tag category dropdown
        self.tag_category_var = tk.StringVar(value="")

        # Get existing tag categories
        all_tags = self.db.get_all_tags()
        if categories := list({tag[2] for tag in all_tags if tag[2]}):
            ctk.CTkLabel(tag_entry_frame, text="Category:", width=80).pack(side=tk.LEFT, padx=5)
            category_dropdown = ctk.CTkComboBox(
                tag_entry_frame, 
                values=[""] + sorted(categories),
                variable=self.tag_category_var,
                width=120
            )
            category_dropdown.pack(side=tk.LEFT, padx=5)

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
                text="Delete",
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
        Update entry name suggestions based on input

        Args:
            event: KeyRelease event
        """
        # Get the current text
        text = self.entry_entry.get().strip()

        if not text or len(text) < 2:
            if self.showing_suggestions:
                self.suggestion_frame.pack_forget()
                self.showing_suggestions = False
            return

        if active_class := self.db.get_active_classification(
            self.current_lifelist_id
        ):
            if results := self.db.search_classification(active_class[0], text):
                # Clear current suggestions
                self.suggestion_list.delete(0, tk.END)
                self.suggestions = []

                # Add new suggestions
                for _, name, alternate_name, category in results:
                    display_name = name
                    if alternate_name:
                        display_name = f"{alternate_name} ({name})"

                    self.suggestion_list.insert(tk.END, display_name)
                    self.suggestions.append((name, alternate_name))

                # Show the suggestion frame if not already showing
                if not self.showing_suggestions:
                    self.suggestion_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
                    self.showing_suggestions = True
            elif self.showing_suggestions:
                self.suggestion_frame.pack_forget()
                self.showing_suggestions = False
        elif self.showing_suggestions:
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
            name, alternate_name = self.suggestions[index]

            # Set the entry entry to the selected suggestion
            if alternate_name:
                self.entry_entry.delete(0, tk.END)
                self.entry_entry.insert(0, alternate_name)
            else:
                self.entry_entry.delete(0, tk.END)
                self.entry_entry.insert(0, name)

            # Hide suggestions
            self.suggestion_frame.pack_forget()
            self.showing_suggestions = False
        except Exception:
            pass

    def _add_tag(self):
        """Add a tag to the current tags list"""
        tag_name = self.tag_entry.get().strip()
        tag_category = self.tag_category_var.get().strip() if hasattr(self, 'tag_category_var') else None

        if tag_name:
            # Check if this tag (with same category) is already in the list
            exists = any(
                existing_tag[0] == tag_name and existing_tag[1] == tag_category
                for existing_tag in self.current_tags
            )
            if not exists:
                self.current_tags.append((tag_name, tag_category))
                self.tag_entry.delete(0, tk.END)
                if hasattr(self, 'tag_category_var'):
                    self.tag_category_var.set("")
                self._update_tag_display()

    def _remove_tag(self, tag_info):
        """
        Remove a tag from the current tags list

        Args:
            tag_info: Tuple of (tag_name, tag_category)
        """
        self.current_tags.remove(tag_info)
        self._update_tag_display()

    def _update_tag_display(self):
        """Update the display of current tags"""
        # Clear existing tags
        for widget in self.tag_labels_frame.winfo_children():
            widget.destroy()

        # Add tag labels, grouped by category
        tag_by_category = {}
        for tag_name, category in self.current_tags:
            if category not in tag_by_category:
                tag_by_category[category] = []
            tag_by_category[category].append(tag_name)
            
        # Create a frame for each category
        for category, tags in tag_by_category.items():
            category_frame = ctk.CTkFrame(self.tag_labels_frame)
            category_frame.pack(fill=tk.X, pady=2)
            
            # Add category label if it exists
            if category:
                ctk.CTkLabel(
                    category_frame, 
                    text=category, 
                    font=ctk.CTkFont(size=12, weight="bold")
                ).pack(anchor="w", padx=5, pady=(5, 0))
                
            # Add tags for this category
            tags_container = ctk.CTkFrame(category_frame)
            tags_container.pack(fill=tk.X, padx=5, pady=5)
                
            for tag_name in tags:
                tag_label_frame = ctk.CTkFrame(tags_container)
                tag_label_frame.pack(side=tk.LEFT, padx=2, pady=2)

                tag_label = ctk.CTkLabel(tag_label_frame, text=tag_name, padx=5)
                tag_label.pack(side=tk.LEFT)

                remove_btn = ctk.CTkButton(
                    tag_label_frame,
                    text="✕",
                    width=20,
                    height=20,
                    command=lambda t=(tag_name, category): self._remove_tag(t)
                )
                remove_btn.pack(side=tk.LEFT)

    def _add_photos(self):
        """Add photos to the observation"""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff")
        ]
        if file_paths := filedialog.askopenfilenames(
            title="Select Photos", filetypes=filetypes
        ):
            # Check if this entry already has a primary photo
            entry_name = self.entry_entry.get().strip()
            has_primary = False

            if entry_name and self.current_lifelist_id:
                has_primary = self.db.entry_has_primary_photo(self.current_lifelist_id, entry_name)

            # Also check if any photos in the current list are marked as primary
            current_has_primary = any(p.get("is_primary", False) for p in self.photos)

            for path in file_paths:
                # Ensure the path is not already in the list
                if all(p["path"] != path for p in self.photos):
                    # Extract EXIF data if available
                    lat, lon, taken_date = PhotoUtils.extract_exif_data(path)

                    # Create thumbnail
                    thumbnail = PhotoUtils.resize_image_for_thumbnail(path)

                    # Add to photos list - only set as primary if there's no existing primary
                    # for this entry and no primary in the current list
                    self.photos.append({
                            "path": path,
                            "is_primary": not has_primary
                            and not current_has_primary
                            and len(self.photos) == 0,
                            "thumbnail": thumbnail,
                            "latitude": lat,
                            "longitude": lon,
                            "taken_date": taken_date,
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

        # Show info about entry-level changes
        entry_term = self.app_state.get_entry_term()
        messagebox.showinfo(
            "Primary Photo Set",
            f"This photo will be set as the primary photo for all observations of this {entry_term} when saved."
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
        db = DatabaseFactory.get_database()
        observation, custom_field_values, obs_tags = db.get_observation_details(observation_id)

        if observation:
            self.entry_entry.insert(0, observation[2] or "")  # entry_name
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
                # Find the field in custom_field_entries
                for field_id, entry in self.custom_field_entries.items():
                    field_info = self.db.cursor.execute(
                        "SELECT field_name, field_type FROM custom_fields WHERE id = ?",
                        (field_id,)
                    ).fetchone()
                    
                    if not field_info or field_info[0] != field_name:
                        continue
                        
                    # Handle different field types
                    field_type = field_info[1]
                    
                    if field_type == "boolean":
                        if isinstance(entry, ctk.CTkCheckBox):
                            if value == "1":
                                entry.select() 
                            else:
                                entry.deselect()
                    elif field_type == "choice":
                        # For choice fields, entry is a tuple: (combobox, variable, options)
                        combobox, variable, options = entry
                        if value:
                            # Find the display text for this value
                            display_text = value
                            for option_value, option_label, _ in options:
                                if option_value == value:
                                    display_text = option_label or option_value
                                    break
                            variable.set(display_text)
                    elif field_type == "rating":
                        # For rating fields, entry is a tuple: (buttons, variable)
                        buttons, variable = entry
                        if value:
                            try:
                                rating = int(value)
                                variable.set(rating)
                            except ValueError:
                                pass
                    elif field_type == "color":
                        # For color fields, entry might be a tuple: (entry, variable) or just variable
                        if isinstance(entry, tuple):
                            _, variable = entry
                            variable.set(value or "")
                    else:
                        # For text, number, date fields
                        entry.insert(0, value or "")

        # Load tags
        if obs_tags:
            for tag_id, tag_name, tag_category in obs_tags:
                self.current_tags.append((tag_name, tag_category))
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
        entry = self.entry_entry.get().strip()
        if not entry:
            entry_term = self.app_state.get_entry_term()
            messagebox.showerror("Error", f"{entry_term.capitalize()} name is required")
            return False
            
        # Validate required custom fields
        for field_id, entry in self.custom_field_entries.items():
            # Get field info
            field_info = self.db.cursor.execute(
                "SELECT field_name, field_type, is_required FROM custom_fields WHERE id = ?",
                (field_id,)
            ).fetchone()
            
            if not field_info or not field_info[2]:  # not required
                continue
                
            field_name = field_info[0]
            field_type = field_info[1]
            
            # Check if field has a value
            if field_type == "boolean":
                # Boolean fields always have a value (True/False)
                continue
            elif field_type == "choice":
                # For choice fields, entry is a tuple: (combobox, variable, options)
                _, variable, _ = entry
                if not variable.get():
                    messagebox.showerror("Error", f"'{field_name}' is required")
                    return False
            elif field_type == "rating":
                # For rating fields, entry is a tuple: (buttons, variable)
                _, variable = entry
                if variable.get() <= 0:
                    messagebox.showerror("Error", f"'{field_name}' is required")
                    return False
            elif field_type == "color":
                # For color fields, entry might be a tuple: (entry, variable) or just variable
                if isinstance(entry, tuple):
                    _, variable = entry
                    if not variable.get():
                        messagebox.showerror("Error", f"'{field_name}' is required")
                        return False
            else:
                # For text, number, date fields
                if not entry.get().strip():
                    messagebox.showerror("Error", f"'{field_name}' is required")
                    return False
                    
        return True

    def _save_observation(self):
        """Save the observation using proper transaction management"""
        if not self._validate_fields():
            return

        # Get basic fields
        entry_name = self.entry_entry.get().strip()
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
            # Get database connection (without context manager)
            db = DatabaseFactory.get_database()

            # Define all operations to perform in the transaction
            def save_operations():
                entry_primary_set = False

                if self.current_observation_id:
                    # Update existing observation
                    success = db.update_observation(
                        self.current_observation_id,
                        entry_name,
                        observation_date,
                        location,
                        latitude,
                        longitude,
                        tier,
                        notes
                    )

                    if not success:
                        raise Exception("Failed to update observation")

                    obs_id = self.current_observation_id

                    # For existing observations, get current photos and remove ones that are no longer in the UI
                    current_photos = db.get_photos(obs_id)
                    current_photo_ids = {photo[0] for photo in current_photos}
                    kept_photo_ids = {photo.get("id") for photo in self.photos if "id" in photo}

                    # Photos to delete = current photos that aren't in the kept photos list
                    photos_to_delete = current_photo_ids - kept_photo_ids

                    # Delete each photo that was removed
                    for photo_id in photos_to_delete:
                        db.delete_photo(photo_id)
                else:
                    # Create new observation
                    obs_id = db.add_observation(
                        self.current_lifelist_id,
                        entry_name,
                        observation_date,
                        location,
                        latitude,
                        longitude,
                        tier,
                        notes
                    )

                    if not obs_id:
                        raise Exception("Failed to add observation")

                # Save custom field values
                for field_id, field_entry in self.custom_field_entries.items():
                    # Get field type
                    field_info = db.cursor.execute(
                        "SELECT field_type FROM custom_fields WHERE id = ?",
                        (field_id,)
                    ).fetchone()

                    if not field_info:
                        continue

                    field_type = field_info[0]
                    value = None

                    # Get value based on field type
                    if field_type == "boolean":
                        if isinstance(field_entry, ctk.CTkCheckBox):
                            value = "1" if field_entry.get() else "0"
                        else:
                            continue
                    elif field_type == "choice":
                        # For choice fields, get the actual value, not the display text
                        combobox, variable, options = field_entry
                        display_text = variable.get()

                        if display_text:
                            # Find the value for this display text
                            for option_value, option_label, _ in options:
                                if option_label == display_text or option_value == display_text:
                                    value = option_value
                                    break
                    elif field_type == "rating":
                        # For rating fields, get the rating value
                        buttons, variable = field_entry
                        rating = variable.get()
                        if rating > 0:
                            value = str(rating)
                    elif field_type == "color":
                        # For color fields, get the color value
                        if isinstance(field_entry, tuple):
                            _, variable = field_entry
                            value = variable.get()
                    else:
                        # For text, number, date fields
                        value = field_entry.get().strip()

                    # Delete any existing values
                    db.cursor.execute(
                        "DELETE FROM observation_custom_fields WHERE observation_id = ? AND field_id = ?",
                        (obs_id, field_id)
                    )

                    # Insert new value if not empty
                    if value:
                        db.cursor.execute(
                            "INSERT INTO observation_custom_fields (observation_id, field_id, value) VALUES (?, ?, ?)",
                            (obs_id, field_id, value)
                        )

                # Save tags
                # First, remove all existing tags for this observation
                db.cursor.execute(
                    "DELETE FROM observation_tags WHERE observation_id = ?",
                    (obs_id,)
                )

                # Add the current tags
                for tag_name, tag_category in self.current_tags:
                    tag_id = db.add_tag(tag_name, tag_category)
                    db.add_tag_to_observation(obs_id, tag_id)

                # Save photos
                for photo in self.photos:
                    if photo.get("is_primary", False):
                        entry_primary_set = True

                    # New or existing photo handling
                    if "id" not in photo:
                        # New photo
                        db.add_photo(
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
                            db.set_primary_photo(photo["id"], obs_id)

                return entry_primary_set

            # Execute all operations as a single transaction
            entry_primary_set = db.execute_transaction(save_operations)

            # Provide feedback only once if any photo was set as primary
            if entry_primary_set:
                entry_term = self.app_state.get_entry_term()
                messagebox.showinfo(
                    "Primary Photo Updated",
                    f"The selected primary photo will now appear for all observations of this {entry_term}."
                )

            # Return to lifelist view
            self.controller.open_lifelist(self.current_lifelist_id)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _delete_observation(self):
        """Delete the current observation"""
        if not self.current_observation_id:
            return

        observation_term = self.app_state.get_observation_term()
        if confirm := messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this {observation_term}? This action cannot be undone.",
        ):
            try:
                # Get database without context manager
                db = DatabaseFactory.get_database()

                # Execute deletion in a transaction
                result = db.execute_transaction(
                    lambda: db.delete_observation(self.current_observation_id)
                )

                success, photos = result

                if success:
                    # Return to the lifelist view
                    self.controller.open_lifelist(self.current_lifelist_id)
                else:
                    messagebox.showerror("Error", f"Failed to delete the {observation_term}")

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")