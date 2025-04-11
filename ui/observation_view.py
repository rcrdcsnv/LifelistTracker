"""
Observation view - Display observation details
"""
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from ui.utils import create_scrollable_container


class ObservationView:
    """
    UI Component for displaying observation details
    """

    def __init__(self, app, db, content_frame):
        """
        Initialize the observation view

        Args:
            app: Main application reference
            db: Database connection
            content_frame: Content frame for displaying observation
        """
        self.app = app
        self.db = db
        self.content = content_frame

    def show(self, observation_id):
        """
        Display details for an observation

        Args:
            observation_id: ID of the observation to display
        """
        # Clear the content area
        for widget in self.content.winfo_children():
            widget.destroy()

        # Create the detail container
        detail_container = ctk.CTkFrame(self.content)
        detail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create scroll canvas
        canvas, detail_frame = create_scrollable_container(detail_container)

        # Load observation details
        observation, custom_fields, tags = self.db.get_observation_details(observation_id)

        if not observation:
            error_label = ctk.CTkLabel(
                detail_frame,
                text="Observation not found",
                font=ctk.CTkFont(size=16)
            )
            error_label.pack(pady=20)

            back_btn = ctk.CTkButton(
                detail_frame,
                text="Back to Lifelist",
                command=lambda: self.app.open_lifelist(self.app.current_lifelist_id, self.app.get_lifelist_name())
            )
            back_btn.pack(pady=10)
            return

        # Photos carousel at the top
        self._create_photo_gallery(detail_frame, observation_id)

        # Header with species name
        species_name = observation[2]
        title_label = ctk.CTkLabel(
            detail_frame,
            text=species_name,
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=15)

        # Details section
        self._create_details_section(detail_frame, observation)

        # Custom fields
        if custom_fields:
            self._create_custom_fields_section(detail_frame, custom_fields)

        # Tags
        if tags:
            self._create_tags_section(detail_frame, tags)

        # Action buttons
        self._create_action_buttons(detail_frame, observation_id)

    def _create_photo_gallery(self, parent, observation_id):
        """
        Create a photo gallery for the observation

        Args:
            parent: Parent widget
            observation_id: ID of the observation
        """
        photos = self.db.get_photos(observation_id)

        if not photos:
            return

        photos_frame = ctk.CTkFrame(parent)
        photos_frame.pack(fill=tk.X, padx=20, pady=10)

        # Show primary photo larger, with small thumbnails below
        primary_photo = None
        for photo in photos:
            if photo[2]:  # is_primary
                primary_photo = photo
                break

        if not primary_photo and photos:
            primary_photo = photos[0]

        if primary_photo:
            try:
                img = Image.open(primary_photo[1])
                img.thumbnail((600, 400))  # Resize while maintaining aspect ratio
                photo_img = ImageTk.PhotoImage(img)

                photo_label = ctk.CTkLabel(photos_frame, text="", image=photo_img)
                photo_label.pack(pady=10)
                photo_label.image = photo_img  # Keep a reference
            except Exception as e:
                print(f"Error loading primary photo: {e}")

        # Thumbnails row
        if len(photos) > 1:
            thumbnails_frame = ctk.CTkFrame(photos_frame)
            thumbnails_frame.pack(fill=tk.X, pady=10)

            for photo in photos:
                try:
                    img = Image.open(photo[1])
                    img.thumbnail((80, 80))
                    thumbnail = ImageTk.PhotoImage(img)

                    thumb_frame = ctk.CTkFrame(thumbnails_frame)
                    thumb_frame.pack(side=tk.LEFT, padx=5)

                    thumb_label = ctk.CTkLabel(thumb_frame, text="", image=thumbnail)
                    thumb_label.pack(padx=5, pady=5)
                    thumb_label.image = thumbnail  # Keep a reference

                    # Add a primary indicator if this is the primary photo
                    if photo[2]:  # is_primary
                        primary_label = ctk.CTkLabel(thumb_frame, text="Primary", font=ctk.CTkFont(size=10))
                        primary_label.pack(pady=2)
                except Exception as e:
                    print(f"Error creating thumbnail: {e}")

    def _create_details_section(self, parent, observation):
        """
        Create the details section

        Args:
            parent: Parent widget
            observation: Observation data tuple
        """
        details_frame = ctk.CTkFrame(parent)
        details_frame.pack(fill=tk.X, padx=20, pady=10)

        # Observation details
        details_grid = ctk.CTkFrame(details_frame)
        details_grid.pack(fill=tk.X, pady=10)

        # Date
        date_frame = ctk.CTkFrame(details_grid)
        date_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(date_frame, text="Date:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(date_frame, text=observation[3] or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Location
        location_frame = ctk.CTkFrame(details_grid)
        location_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(location_frame, text="Location:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT,
                                                                                                        padx=5)
        ctk.CTkLabel(location_frame, text=observation[4] or "Not recorded").pack(side=tk.LEFT, padx=5)

        # Coordinates
        if observation[5] and observation[6]:  # latitude and longitude
            coords_frame = ctk.CTkFrame(details_grid)
            coords_frame.pack(fill=tk.X, pady=2)

            ctk.CTkLabel(coords_frame, text="Coordinates:", width=150, font=ctk.CTkFont(weight="bold")).pack(
                side=tk.LEFT, padx=5)
            coord_text = f"{observation[5]}, {observation[6]}"
            ctk.CTkLabel(coords_frame, text=coord_text).pack(side=tk.LEFT, padx=5)

        # Tier
        tier_frame = ctk.CTkFrame(details_grid)
        tier_frame.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(tier_frame, text="Tier:", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(tier_frame, text=observation[7] or "Not specified").pack(side=tk.LEFT, padx=5)

        # Notes (if any)
        if observation[8]:
            notes_frame = ctk.CTkFrame(details_grid)
            notes_frame.pack(fill=tk.X, pady=5)

            ctk.CTkLabel(notes_frame, text="Notes:", width=150, font=ctk.CTkFont(weight="bold")).pack(
                side=tk.LEFT, padx=5, anchor="n")

            notes_text = ctk.CTkTextbox(notes_frame, width=400, height=100)
            notes_text.pack(side=tk.LEFT, padx=5, pady=5)
            notes_text.insert("1.0", observation[8])
            notes_text.configure(state="disabled")  # Make it read-only

    def _create_custom_fields_section(self, parent, custom_fields):
        """
        Create the custom fields section

        Args:
            parent: Parent widget
            custom_fields: List of custom field tuples
        """
        custom_fields_label = ctk.CTkLabel(
            parent,
            text="Custom Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        custom_fields_label.pack(pady=(20, 5))

        custom_fields_frame = ctk.CTkFrame(parent)
        custom_fields_frame.pack(fill=tk.X, padx=20, pady=5)

        for field_name, field_type, value in custom_fields:
            field_frame = ctk.CTkFrame(custom_fields_frame)
            field_frame.pack(fill=tk.X, pady=2)

            ctk.CTkLabel(field_frame, text=f"{field_name}:", width=150, font=ctk.CTkFont(weight="bold")).pack(
                side=tk.LEFT, padx=5)

            # Format the value based on field type
            if field_type == "boolean":
                display_value = "Yes" if value == "1" else "No"
            else:
                display_value = value or "Not specified"

            ctk.CTkLabel(field_frame, text=display_value).pack(side=tk.LEFT, padx=5)

    def _create_tags_section(self, parent, tags):
        """
        Create the tags section

        Args:
            parent: Parent widget
            tags: List of tag tuples (id, name)
        """
        tags_label = ctk.CTkLabel(
            parent,
            text="Tags",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        tags_label.pack(pady=(20, 5))

        tags_frame = ctk.CTkFrame(parent)
        tags_frame.pack(fill=tk.X, padx=20, pady=5)

        for tag_id, tag_name in tags:
            tag_label = ctk.CTkLabel(
                tags_frame,
                text=tag_name,
                fg_color="gray30",
                corner_radius=10,
                padx=10,
                pady=5
            )
            tag_label.pack(side=tk.LEFT, padx=5, pady=5)

    def _create_action_buttons(self, parent, observation_id):
        """
        Create action buttons

        Args:
            parent: Parent widget
            observation_id: ID of the observation
        """
        buttons_frame = ctk.CTkFrame(parent)
        buttons_frame.pack(fill=tk.X, padx=20, pady=20)

        back_btn = ctk.CTkButton(
            buttons_frame,
            text="Back to Lifelist",
            command=lambda: self.app.open_lifelist(self.app.current_lifelist_id, self.app.get_lifelist_name())
        )
        back_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ctk.CTkButton(
            buttons_frame,
            text="Edit Observation",
            command=lambda: self.app.observation_form.show(self.app.current_lifelist_id, observation_id)
        )
        edit_btn.pack(side=tk.RIGHT, padx=5)