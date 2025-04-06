import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import sqlite3
from datetime import datetime
import uuid
import shutil
from PIL.ExifTags import TAGS, GPSTAGS
import folium
import webbrowser
import re

# Configure CustomTkinter appearance
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class LifelistManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Lifelist Manager")
        self.root.geometry("1200x800")

        # Initialize database
        self.db_path = os.path.join(os.path.expanduser("~"), "lifelist_data")
        os.makedirs(self.db_path, exist_ok=True)
        self.db_file = os.path.join(self.db_path, "lifelist.db")
        self.photo_dir = os.path.join(self.db_path, "photos")
        os.makedirs(self.photo_dir, exist_ok=True)

        self.create_database()

        # Variables
        self.current_lifelist = None
        self.current_observation = None
        self.filter_var = ctk.StringVar(value="All")
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        self.tag_filter = set()

        # Create UI
        self.create_menu()
        self.create_main_frame()

        # Load lifelists
        self.load_lifelists()

    def create_main_frame(self):
        """Create the main application frame and widgets"""
        # Main frame with three panels
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Lifelist selection
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        ctk.CTkLabel(left_frame, text="Your Lifelists", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10,
                                                                                                       pady=(10, 5))

        # Custom treeview for lifelists (CustomTkinter doesn't have a direct ttk.Treeview equivalent)
        # We'll use a listbox with a custom selection handler
        self.lifelist_listbox = ctk.CTkListbox(left_frame, width=200, height=600,
                                               command=self.on_lifelist_select_from_listbox)
        self.lifelist_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Center panel - Observations list
        center_frame = ctk.CTkFrame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Filter and search controls
        filter_frame = ctk.CTkFrame(center_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(filter_frame, text="Tier:").pack(side=tk.LEFT, padx=5)
        tier_combo = ctk.CTkOptionMenu(filter_frame, variable=self.filter_var, values=["All", "Wild", "Captive"],
                                       command=self.filter_observations)
        tier_combo.pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(filter_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_entry = ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=200)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Tags filter frame
        self.tags_filter_frame = ctk.CTkFrame(center_frame)
        self.tags_filter_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(self.tags_filter_frame, text="Filter by Tags",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=5)

        # Observations frame
        observations_frame = ctk.CTkFrame(center_frame)
        observations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ctk.CTkLabel(observations_frame, text="Observations",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)

        # Create a frame for the header
        header_frame = ctk.CTkFrame(observations_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Create header labels
        ctk.CTkLabel(header_frame, text="Species", width=150,
                     font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkLabel(header_frame, text="Tier", width=70,
                     font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header_frame, text="Date", width=100,
                     font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(header_frame, text="Location", width=150,
                     font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)

        # Create a custom listbox for observations
        observations_container = ctk.CTkScrollableFrame(observations_frame)
        observations_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.observations_frame = observations_container

        # Observation context menu
        self.obs_context_menu = tk.Menu(self.root, tearoff=0)
        self.obs_context_menu.add_command(label="Edit", command=self.edit_observation)
        self.obs_context_menu.add_command(label="Delete", command=self.delete_observation)

        # Right panel - Observation details
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ctk.CTkLabel(right_frame, text="Observation Details",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.details_frame = ctk.CTkScrollableFrame(right_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Default "no selection" message
        self.no_selection_label = ctk.CTkLabel(self.details_frame, text="Select an observation to view details")
        self.no_selection_label.pack(fill=tk.BOTH, expand=True)
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Lifelists table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifelists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            taxonomy_source TEXT,
            created_date TEXT,
            modified_date TEXT,
            custom_fields TEXT
        )
        ''')

        # Observations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            lifelist_id TEXT NOT NULL,
            species TEXT NOT NULL,
            tier TEXT NOT NULL,
            observation_date TEXT,
            location TEXT,
            notes TEXT,
            latitude REAL,
            longitude REAL,
            custom_data TEXT,
            created_date TEXT,
            modified_date TEXT,
            thumbnail_photo TEXT,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        # Photos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            observation_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            description TEXT,
            latitude REAL,
            longitude REAL,
            is_thumbnail INTEGER DEFAULT 0,
            upload_date TEXT,
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE
        )
        ''')

        # Tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        ''')

        # Observation-Tags relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS observation_tags (
            observation_id TEXT,
            tag_id TEXT,
            PRIMARY KEY (observation_id, tag_id),
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        conn.close()

    def create_menu(self):
        """Create application menu"""
        menu_bar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New Lifelist", command=self.new_lifelist)
        file_menu.add_command(label="Export Lifelist", command=self.export_lifelist)
        file_menu.add_command(label="Import Lifelist", command=self.import_lifelist)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Lifelist menu
        lifelist_menu = tk.Menu(menu_bar, tearoff=0)
        lifelist_menu.add_command(label="Add Observation", command=self.add_observation)
        lifelist_menu.add_command(label="View Map", command=self.view_map)
        lifelist_menu.add_command(label="Manage Custom Fields", command=self.manage_custom_fields)
        lifelist_menu.add_command(label="Delete Lifelist", command=self.delete_lifelist)
        menu_bar.add_cascade(label="Lifelist", menu=lifelist_menu)

        self.root.config(menu=menu_bar)

    def create_main_frame(self):
        """Create the main application frame and widgets"""
        # Main frame with three panels
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Lifelist selection
        left_frame = ttk.LabelFrame(main_frame, text="Your Lifelists")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        self.lifelist_treeview = ttk.Treeview(left_frame, columns=("name"), show="headings")
        self.lifelist_treeview.heading("name", text="Name")
        self.lifelist_treeview.column("name", width=150)
        self.lifelist_treeview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.lifelist_treeview.bind("<<TreeviewSelect>>", self.on_lifelist_select)

        # Center panel - Observations list
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Filter and search controls
        filter_frame = ttk.Frame(center_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Tier:").pack(side=tk.LEFT, padx=5)
        tier_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, values=["All", "Wild", "Captive"])
        tier_combo.pack(side=tk.LEFT, padx=5)
        tier_combo.bind("<<ComboboxSelected>>", self.filter_observations)

        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Tags filter frame
        self.tags_filter_frame = ttk.LabelFrame(center_frame, text="Filter by Tags")
        self.tags_filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # Observations treeview
        observations_frame = ttk.LabelFrame(center_frame, text="Observations")
        observations_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.observations_treeview = ttk.Treeview(
            observations_frame,
            columns=("species", "tier", "date", "location"),
            show="headings"
        )
        self.observations_treeview.heading("species", text="Species")
        self.observations_treeview.heading("tier", text="Tier")
        self.observations_treeview.heading("date", text="Date")
        self.observations_treeview.heading("location", text="Location")

        self.observations_treeview.column("species", width=150)
        self.observations_treeview.column("tier", width=70)
        self.observations_treeview.column("date", width=100)
        self.observations_treeview.column("location", width=150)

        scrollbar = ttk.Scrollbar(observations_frame, orient=tk.VERTICAL, command=self.observations_treeview.yview)
        self.observations_treeview.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.observations_treeview.pack(fill=tk.BOTH, expand=True)
        self.observations_treeview.bind("<<TreeviewSelect>>", self.on_observation_select)

        # Observation context menu
        self.obs_context_menu = tk.Menu(self.observations_treeview, tearoff=0)
        self.obs_context_menu.add_command(label="Edit", command=self.edit_observation)
        self.obs_context_menu.add_command(label="Delete", command=self.delete_observation)
        self.observations_treeview.bind("<Button-3>", self.show_obs_context_menu)

        # Right panel - Observation details
        right_frame = ttk.LabelFrame(main_frame, text="Observation Details")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.details_frame = ttk.Frame(right_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Default "no selection" message
        self.no_selection_label = ttk.Label(self.details_frame, text="Select an observation to view details")
        self.no_selection_label.pack(fill=tk.BOTH, expand=True)

    def load_lifelists(self):
        """Load all lifelists from the database"""
        self.lifelist_treeview.delete(*self.lifelist_treeview.get_children())

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM lifelists ORDER BY name")
        lifelists = cursor.fetchall()
        conn.close()

        for lifelist in lifelists:
            self.lifelist_treeview.insert("", "end", values=(lifelist[1],), iid=lifelist[0])

    def new_lifelist(self):
        """Create a new lifelist"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Lifelist")
        dialog.geometry("400x300")
        dialog.grab_set()

        ttk.Label(dialog, text="Name:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Description:").grid(row=1, column=0, sticky="nw", padx=10, pady=10)
        description_text = tk.Text(dialog, width=30, height=5)
        description_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="Taxonomy Source:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        taxonomy_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=taxonomy_var, width=30).grid(row=2, column=1, padx=10, pady=10)

        def save_lifelist():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Lifelist name is required")
                return

            description = description_text.get("1.0", tk.END).strip()
            taxonomy = taxonomy_var.get().strip()

            lifelist_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO lifelists (id, name, description, taxonomy_source, created_date, modified_date, custom_fields) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (lifelist_id, name, description, taxonomy, now, now, json.dumps([]))
            )
            conn.commit()
            conn.close()

            self.load_lifelists()
            dialog.destroy()

        buttons_frame = ttk.Frame(dialog)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(buttons_frame, text="Save", command=save_lifelist).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def on_lifelist_select(self, event):
        """Handle lifelist selection"""
        selected_items = self.lifelist_treeview.selection()
        if selected_items:
            self.current_lifelist = selected_items[0]
            self.load_observations()
            self.load_tags_filter()
        else:
            self.current_lifelist = None
            self.clear_observations()

    def load_tags_filter(self):
        """Load tags for the selected lifelist for filtering"""
        # Clear existing filter checkboxes
        for widget in self.tags_filter_frame.winfo_children():
            if widget.cget("text") != "Filter by Tags":  # Keep the label
                widget.destroy()

        if not self.current_lifelist:
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get all tags used in this lifelist
        query = """
        SELECT DISTINCT t.id, t.name 
        FROM tags t
        JOIN observation_tags ot ON t.id = ot.tag_id
        JOIN observations o ON ot.observation_id = o.id
        WHERE o.lifelist_id = ?
        ORDER BY t.name
        """

        cursor.execute(query, (self.current_lifelist,))
        tags = cursor.fetchall()
        conn.close()

        # Create tag filter checkboxes
        if not tags:
            ctk.CTkLabel(self.tags_filter_frame, text="No tags available").pack(padx=5, pady=5)
            return

        # Create a tag container frame with wrapping
        tags_container = ctk.CTkFrame(self.tags_filter_frame)
        tags_container.pack(fill=tk.X, padx=5, pady=5)

        # Set grid for dynamic wrapping
        row, col = 0, 0
        max_cols = 3

        for tag_id, tag_name in tags:
            # Create a custom styled checkbox
            var = tk.BooleanVar()
            cb = ctk.CTkCheckBox(
                tags_container,
                text=tag_name,
                variable=var,
                command=lambda id=tag_id, v=var: self.toggle_tag_filter(id, v.get()),
                border_width=1,
                corner_radius=8
            )

            # Arrange checkboxes in a grid with wrapping
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def toggle_tag_filter(self, tag_id, selected):
        """Toggle a tag in the filter set and reload observations"""
        if selected:
            self.tag_filter.add(tag_id)
        else:
            self.tag_filter.discard(tag_id)

        self.load_observations()

    def filter_observations(self, value=None):
        """Filter observations based on tier selection"""
        self.load_observations()

    def on_search_change(self, *args):
        """Handle search text changes"""
        self.load_observations()

    def clear_observations(self):
        """Clear the observations list"""
        for widget in self.observations_frame.winfo_children():
            widget.destroy()

        self.observation_rows = {}
        self.observation_widgets = []
        self.clear_observation_details()

    def show_obs_context_menu(self, event, obs_id):
        """Show the observation context menu on right-click"""
        self.current_observation = obs_id
        self.obs_context_menu.post(event.x_root, event.y_root)

        # Update visual selection
        for widget in self.observation_widgets:
            widget.configure(fg_color=("gray85", "gray25"))  # Default color

        if obs_id in self.observation_rows:
            self.observation_rows[obs_id].configure(fg_color=("gray75", "gray35"))  # Selected color

    def toggle_tag_filter(self, tag_id, selected):
        """Toggle a tag in the filter set and reload observations"""
        if selected:
            self.tag_filter.add(tag_id)
        else:
            self.tag_filter.discard(tag_id)

        self.load_observations()

    def filter_observations(self, event=None):
        """Filter observations based on tier selection"""
        self.load_observations()

    def on_search_change(self, *args):
        """Handle search text changes"""
        self.load_observations()

    def clear_observations(self):
        """Clear the observations list"""
        self.observations_treeview.delete(*self.observations_treeview.get_children())
        self.clear_observation_details()

    def on_observation_select(self, event):
        """Handle observation selection"""
        selected_items = self.observations_treeview.selection()
        if selected_items:
            self.current_observation = selected_items[0]
            self.load_observation_details()
        else:
            self.current_observation = None
            self.clear_observation_details()

    def add_observation(self):
        """Add a new observation to the current lifelist"""
        if not self.current_lifelist:
            messagebox.showinfo("Information", "Please select a lifelist first")
            return

        self.open_observation_dialog()

    def edit_observation(self):
        """Edit the selected observation"""
        if not self.current_observation:
            messagebox.showinfo("Information", "Please select an observation first")
            return

        self.open_observation_dialog(self.current_observation)

    def open_observation_dialog(self, observation_id=None):
        """Open dialog to add or edit an observation"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Observation" if not observation_id else "Edit Observation")
        dialog.geometry("500x600")
        dialog.grab_set()

        # Get custom fields for this lifelist
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT custom_fields FROM lifelists WHERE id = ?", (self.current_lifelist,))
        result = cursor.fetchone()
        custom_fields = json.loads(result[0]) if result else []

        # Get observation data if editing
        observation_data = None
        if observation_id:
            cursor.execute("SELECT * FROM observations WHERE id = ?", (observation_id,))
            observation_data = cursor.fetchone()

        conn.close()

        # Create a notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Basic info tab
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Info")

        # Species
        ttk.Label(basic_frame, text="Species:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        species_var = tk.StringVar()
        if observation_data:
            species_var.set(observation_data[2])
        ttk.Entry(basic_frame, textvariable=species_var, width=30).grid(row=0, column=1, padx=10, pady=10)

        # Tier
        ttk.Label(basic_frame, text="Tier:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        tier_var = tk.StringVar(value="Wild" if not observation_data else observation_data[3])
        tier_combo = ttk.Combobox(basic_frame, textvariable=tier_var, values=["Wild", "Captive"])
        tier_combo.grid(row=1, column=1, padx=10, pady=10)

        # Date
        ttk.Label(basic_frame, text="Date:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        date_var = tk.StringVar()
        if observation_data and observation_data[4]:
            date_var.set(observation_data[4])
        else:
            date_var.set(datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(basic_frame, textvariable=date_var, width=30).grid(row=2, column=1, padx=10, pady=10)

        # Location
        ttk.Label(basic_frame, text="Location:").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        location_var = tk.StringVar()
        if observation_data:
            location_var.set(observation_data[5] or "")
        ttk.Entry(basic_frame, textvariable=location_var, width=30).grid(row=3, column=1, padx=10, pady=10)

        # Notes
        ttk.Label(basic_frame, text="Notes:").grid(row=4, column=0, sticky="nw", padx=10, pady=10)
        notes_text = tk.Text(basic_frame, width=30, height=5)
        notes_text.grid(row=4, column=1, padx=10, pady=10)
        if observation_data and observation_data[6]:
            notes_text.insert("1.0", observation_data[6])

        # Coordinates
        ttk.Label(basic_frame, text="Latitude:").grid(row=5, column=0, sticky="w", padx=10, pady=10)
        lat_var = tk.StringVar()
        if observation_data and observation_data[7]:
            lat_var.set(str(observation_data[7]))
        ttk.Entry(basic_frame, textvariable=lat_var, width=30).grid(row=5, column=1, padx=10, pady=10)

        ttk.Label(basic_frame, text="Longitude:").grid(row=6, column=0, sticky="w", padx=10, pady=10)
        lon_var = tk.StringVar()
        if observation_data and observation_data[8]:
            lon_var.set(str(observation_data[8]))
        ttk.Entry(basic_frame, textvariable=lon_var, width=30).grid(row=6, column=1, padx=10, pady=10)

        # Custom fields tab
        custom_frame = ttk.Frame(notebook)
        notebook.add(custom_frame, text="Custom Fields")

        custom_entries = {}
        custom_data = {}

        if observation_data and observation_data[9]:
            custom_data = json.loads(observation_data[9])

        for i, field in enumerate(custom_fields):
            ttk.Label(custom_frame, text=f"{field}:").grid(row=i, column=0, sticky="w", padx=10, pady=10)
            custom_var = tk.StringVar()
            if field in custom_data:
                custom_var.set(custom_data[field])
            custom_entries[field] = custom_var
            ttk.Entry(custom_frame, textvariable=custom_var, width=30).grid(row=i, column=1, padx=10, pady=10)

        # Tags tab
        tags_frame = ttk.Frame(notebook)
        notebook.add(tags_frame, text="Tags")

        # Existing tags
        existing_tags_frame = ttk.LabelFrame(tags_frame, text="Existing Tags")
        existing_tags_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get all tags
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tags ORDER BY name")
        all_tags = cursor.fetchall()

        # Get tags for this observation if editing
        selected_tags = set()
        if observation_id:
            cursor.execute("SELECT tag_id FROM observation_tags WHERE observation_id = ?", (observation_id,))
            selected_tags = set(row[0] for row in cursor.fetchall())

        conn.close()

        # Tag selection checkboxes
        tag_vars = {}
        for i, (tag_id, tag_name) in enumerate(all_tags):
            var = tk.BooleanVar(value=tag_id in selected_tags)
            tag_vars[tag_id] = var
            ttk.Checkbutton(existing_tags_frame, text=tag_name, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=10, pady=5
            )

        # New tag field
        new_tag_frame = ttk.LabelFrame(tags_frame, text="Add New Tag")
        new_tag_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(new_tag_frame, text="Tag Name:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        new_tag_var = tk.StringVar()
        ttk.Entry(new_tag_frame, textvariable=new_tag_var, width=20).grid(row=0, column=1, padx=10, pady=10)

        new_tags = []

        def add_new_tag():
            tag_name = new_tag_var.get().strip()
            if tag_name and tag_name not in [tag[1] for tag in all_tags] and tag_name not in new_tags:
                new_tags.append(tag_name)
                ttk.Label(existing_tags_frame, text=f"New: {tag_name}").grid(
                    row=(len(all_tags) + len(new_tags) - 1) // 2,
                    column=(len(all_tags) + len(new_tags) - 1) % 2,
                    sticky="w", padx=10, pady=5
                )
                new_tag_var.set("")

        ttk.Button(new_tag_frame, text="Add", command=add_new_tag).grid(row=0, column=2, padx=10, pady=10)

        # Photos tab
        photos_frame = ttk.Frame(notebook)
        notebook.add(photos_frame, text="Photos")

        # Current photos list
        photos_list_frame = ttk.LabelFrame(photos_frame, text="Current Photos")
        photos_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        photos_listbox = tk.Listbox(photos_list_frame, width=50, height=10)
        photos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        photos_scrollbar = ttk.Scrollbar(photos_list_frame, orient=tk.VERTICAL, command=photos_listbox.yview)
        photos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        photos_listbox.config(yscrollcommand=photos_scrollbar.set)

        # Get existing photos if editing
        photos_data = []
        if observation_id:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id, filename, description, is_thumbnail FROM photos WHERE observation_id = ?",
                           (observation_id,))
            photos_data = cursor.fetchall()
            conn.close()

            for photo in photos_data:
                thumbnail_mark = "* " if photo[3] else ""
                photos_listbox.insert(tk.END, f"{thumbnail_mark}{os.path.basename(photo[1])} - {photo[2] or ''}")

        # Photo buttons frame
        photo_buttons_frame = ttk.Frame(photos_frame)
        photo_buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        new_photos = []

        def add_photo():
            filepaths = filedialog.askopenfilenames(
                title="Select Photos",
                filetypes=(("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"), ("All files", "*.*"))
            )

            for filepath in filepaths:
                filename = os.path.basename(filepath)
                description = ""
                # Add to the list with a temporary description
                photos_listbox.insert(tk.END, f"{filename} - {description}")
                # Store the new photo data
                new_photos.append((filepath, filename, description, False))

        def set_thumbnail():
            selected = photos_listbox.curselection()
            if not selected:
                messagebox.showinfo("Information", "Please select a photo")
                return

            # Update the listbox display
            for i in range(photos_listbox.size()):
                current_text = photos_listbox.get(i)
                if current_text.startswith("* "):
                    photos_listbox.delete(i)
                    photos_listbox.insert(i, current_text[2:])

            new_text = photos_listbox.get(selected[0])
            if not new_text.startswith("* "):
                photos_listbox.delete(selected[0])
                photos_listbox.insert(selected[0], "* " + new_text)

            # Update thumbnail status for existing photos
            for i, photo in enumerate(photos_data):
                photos_data[i] = (photo[0], photo[1], photo[2], i == selected[0] and selected[0] < len(photos_data))

            # Update thumbnail status for new photos
            for i in range(len(new_photos)):
                path, name, desc, _ = new_photos[i]
                new_photos[i] = (path, name, desc,
                                 i + len(photos_data) == selected[0])

        ttk.Button(photo_buttons_frame, text="Add Photos", command=add_photo).pack(side=tk.LEFT, padx=5)
        ttk.Button(photo_buttons_frame, text="Set as Thumbnail", command=set_thumbnail).pack(side=tk.LEFT, padx=5)

        def remove_photo():
            selected = photos_listbox.curselection()
            if not selected:
                messagebox.showinfo("Information", "Please select a photo")
                return

            idx = selected[0]
            if idx < len(photos_data):
                # Mark existing photo for deletion
                photos_data[idx] = (
                photos_data[idx][0], photos_data[idx][1], photos_data[idx][2], photos_data[idx][3], True)
            else:
                # Remove new photo
                new_photos.pop(idx - len(photos_data))

            photos_listbox.delete(idx)

        ttk.Button(photo_buttons_frame, text="Remove Photo", command=remove_photo).pack(side=tk.LEFT, padx=5)

        # Save button
        def save_observation():
            species = species_var.get().strip()
            if not species:
                messagebox.showerror("Error", "Species name is required")
                return

            tier = tier_var.get()
            date = date_var.get()
            location = location_var.get()
            notes = notes_text.get("1.0", tk.END).strip()

            try:
                latitude = float(lat_var.get()) if lat_var.get().strip() else None
                longitude = float(lon_var.get()) if lon_var.get().strip() else None
            except ValueError:
                messagebox.showerror("Error", "Latitude and longitude must be valid numbers")
                return

            # Collect custom field values
            custom_data = {}
            for field, var in custom_entries.items():
                custom_data[field] = var.get()

            now = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            try:
                # Create or update the observation
                if not observation_id:
                    # New observation
                    new_id = str(uuid.uuid4())
                    cursor.execute(
                        """INSERT INTO observations (
                            id, lifelist_id, species, tier, observation_date, location, notes, 
                            latitude, longitude, custom_data, created_date, modified_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_id, self.current_lifelist, species, tier, date, location, notes,
                         latitude, longitude, json.dumps(custom_data), now, now)
                    )
                    current_obs_id = new_id
                else:
                    # Update existing observation
                    cursor.execute(
                        """UPDATE observations SET 
                            species = ?, tier = ?, observation_date = ?, location = ?, notes = ?,
                            latitude = ?, longitude = ?, custom_data = ?, modified_date = ?
                        WHERE id = ?""",
                        (species, tier, date, location, notes, latitude, longitude,
                         json.dumps(custom_data), now, observation_id)
                    )
                    current_obs_id = observation_id

                # Handle new tags
                for tag_name in new_tags:
                    tag_id = str(uuid.uuid4())
                    cursor.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tag_id, tag_name))
                    cursor.execute("INSERT INTO observation_tags (observation_id, tag_id) VALUES (?, ?)",
                                   (current_obs_id, tag_id))

                # Handle existing tags
                if observation_id:
                    # Remove all existing tag relationships
                    cursor.execute("DELETE FROM observation_tags WHERE observation_id = ?", (observation_id,))

                # Add selected tags
                for tag_id, var in tag_vars.items():
                    if var.get():
                        cursor.execute("INSERT INTO observation_tags (observation_id, tag_id) VALUES (?, ?)",
                                       (current_obs_id, tag_id))

                # Handle photo deletions
                for photo in photos_data:
                    if len(photo) > 4 and photo[4]:  # Marked for deletion
                        cursor.execute("DELETE FROM photos WHERE id = ?", (photo[0],))
                        # Delete the file if possible
                        try:
                            os.remove(photo[1])
                        except:
                            pass

                # Update thumbnail status for existing photos
                for photo in photos_data:
                    if len(photo) <= 4:  # Not marked for deletion
                        cursor.execute("UPDATE photos SET is_thumbnail = ? WHERE id = ?",
                                       (1 if photo[3] else 0, photo[0]))

                # Set thumbnail_photo field in observations
                thumbnail_id = None

                # Check existing photos first
                for photo in photos_data:
                    if len(photo) <= 4 and photo[3]:  # Not deleted and is thumbnail
                        thumbnail_id = photo[0]

                # Process new photos
                thumbnail_from_new = None
                for photo_path, filename, description, is_thumbnail in new_photos:
                    photo_id = str(uuid.uuid4())

                    # Copy the photo to the application's photo directory
                    dest_filename = f"{photo_id}_{filename}"
                    dest_path = os.path.join(self.photo_dir, dest_filename)
                    shutil.copy2(photo_path, dest_path)

                    # Extract EXIF data if possible
                    lat, lon = self.extract_gps_from_image(photo_path)

                    cursor.execute(
                        """INSERT INTO photos (
                            id, observation_id, filename, description, latitude, longitude, 
                            is_thumbnail, upload_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (photo_id, current_obs_id, dest_path, description, lat, lon,
                         1 if is_thumbnail else 0, now)
                    )

                    if is_thumbnail:
                        thumbnail_from_new = photo_id

                # Set the thumbnail in the observation record
                final_thumbnail = thumbnail_from_new or thumbnail_id
                if final_thumbnail:
                    cursor.execute("UPDATE observations SET thumbnail_photo = ? WHERE id = ?",
                                   (final_thumbnail, current_obs_id))

                conn.commit()

                # Refresh the UI
                self.load_observations()
                if self.current_observation == current_obs_id:
                    self.load_observation_details()

                dialog.destroy()

            except sqlite3.Error as e:
                conn.rollback()
                messagebox.showerror("Database Error", str(e))
            finally:
                conn.close()

        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(pady=20)

        ttk.Button(buttons_frame, text="Save", command=save_observation).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def extract_gps_from_image(self, image_path):
        """Extract GPS coordinates from image EXIF data if available"""
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return None, None

                # Extract GPS info
                gps_info = {}
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == "GPSInfo":
                        for gps_tag in value:
                            gps_info[GPSTAGS.get(gps_tag, gps_tag)] = value[gps_tag]

                if not gps_info:
                    return None, None

                # Convert GPS coordinates to decimal degrees
                if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
                    lat = self._convert_to_degrees(gps_info["GPSLatitude"])
                    if gps_info["GPSLatitudeRef"] == "S":
                        lat = -lat

                    lon = self._convert_to_degrees(gps_info["GPSLongitude"])
                    if gps_info["GPSLongitudeRef"] == "W":
                        lon = -lon

                    return lat, lon
        except:
            pass

        return None, None

    def _convert_to_degrees(self, value):
        """Helper function to convert GPS coordinates to decimal degrees"""
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)

    def load_observation_details(self):
        """Load and display details for the selected observation"""
        self.clear_observation_details()

        if not self.current_observation:
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get observation data
        cursor.execute("""
            SELECT o.*, l.name as lifelist_name, l.custom_fields
            FROM observations o
            JOIN lifelists l ON o.lifelist_id = l.id
            WHERE o.id = ?
        """, (self.current_observation,))

        obs = cursor.fetchone()
        if not obs:
            conn.close()
            return

        # Get photos
        cursor.execute(
            "SELECT id, filename, description, is_thumbnail FROM photos WHERE observation_id = ? ORDER BY is_thumbnail DESC",
            (self.current_observation,))
        photos = cursor.fetchall()

        # Get tags
        cursor.execute("""
            SELECT t.name 
            FROM tags t
            JOIN observation_tags ot ON t.id = ot.tag_id
            WHERE ot.observation_id = ?
            ORDER BY t.name
        """, (self.current_observation,))

        tags = [tag[0] for tag in cursor.fetchall()]
        conn.close()

        # Create scrollable canvas for details
        canvas = tk.Canvas(self.details_frame)
        scrollbar = ttk.Scrollbar(self.details_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Display observation details
        row = 0

        # Species and tier header
        species_frame = ttk.Frame(scrollable_frame)
        species_frame.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        row += 1

        ttk.Label(species_frame, text=obs[2], font=("", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(species_frame, text=f" ({obs[3]})", font=("", 12, "italic")).pack(side=tk.LEFT)

        # Lifelist name
        ttk.Label(scrollable_frame, text=f"Lifelist: {obs[11]}", font=("", 10)).grid(
            row=row, column=0, sticky="w", padx=10, pady=2
        )
        row += 1

        # Date and location
        if obs[4]:
            ttk.Label(scrollable_frame, text=f"Date: {obs[4]}", font=("", 10)).grid(
                row=row, column=0, sticky="w", padx=10, pady=2
            )
            row += 1

        if obs[5]:
            ttk.Label(scrollable_frame, text=f"Location: {obs[5]}", font=("", 10)).grid(
                row=row, column=0, sticky="w", padx=10, pady=2
            )
            row += 1

        # Coordinates
        if obs[7] and obs[8]:
            ttk.Label(scrollable_frame, text=f"Coordinates: {obs[7]}, {obs[8]}", font=("", 10)).grid(
                row=row, column=0, sticky="w", padx=10, pady=2
            )
            row += 1

        # Notes
        if obs[6]:
            ttk.Label(scrollable_frame, text="Notes:", font=("", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 2)
            )
            row += 1

            notes_text = tk.Text(scrollable_frame, width=40, height=4, wrap=tk.WORD)
            notes_text.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            notes_text.insert("1.0", obs[6])
            notes_text.config(state=tk.DISABLED)
            row += 1

        # Custom fields
        custom_fields = json.loads(obs[12]) if obs[12] else []
        custom_data = json.loads(obs[9]) if obs[9] else {}

        if custom_fields and custom_data:
            ttk.Label(scrollable_frame, text="Custom Fields:", font=("", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 2)
            )
            row += 1

            for field in custom_fields:
                if field in custom_data and custom_data[field]:
                    ttk.Label(scrollable_frame, text=f"{field}: {custom_data[field]}", font=("", 10)).grid(
                        row=row, column=0, sticky="w", padx=20, pady=2
                    )
                    row += 1

        # Tags
        if tags:
            ttk.Label(scrollable_frame, text="Tags:", font=("", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 2)
            )
            row += 1

            tags_frame = ttk.Frame(scrollable_frame)
            tags_frame.grid(row=row, column=0, sticky="w", padx=20, pady=2)
            row += 1

            for i, tag in enumerate(tags):
                ttk.Label(tags_frame, text=tag, background="#e0e0e0", padding=(5, 2)).grid(
                    row=0, column=i, padx=5, pady=2
                )

        # Photos
        if photos:
            ttk.Label(scrollable_frame, text="Photos:", font=("", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 2)
            )
            row += 1

            photos_frame = ttk.Frame(scrollable_frame)
            photos_frame.grid(row=row, column=0, sticky="w", padx=10, pady=2)
            row += 1

            # Show the thumbnail first, then up to 3 more photos
            display_photos = []
            thumbnail = None

            for photo in photos:
                if photo[3]:  # Is thumbnail
                    thumbnail = photo
                else:
                    display_photos.append(photo)

            if thumbnail:
                display_photos.insert(0, thumbnail)

            for i, photo in enumerate(display_photos[:4]):
                try:
                    img = Image.open(photo[1])
                    img = img.resize((150, 150), Image.LANCZOS)
                    photo_img = ImageTk.PhotoImage(img)

                    photo_label = ttk.Label(photos_frame, image=photo_img)
                    photo_label.image = photo_img  # Keep a reference
                    photo_label.grid(row=0, column=i, padx=5, pady=5)

                    if photo[3]:  # Is thumbnail
                        ttk.Label(photos_frame, text="Primary", font=("", 8)).grid(
                            row=1, column=i, padx=5
                        )
                except:
                    ttk.Label(photos_frame, text="Image load error").grid(
                        row=0, column=i, padx=5, pady=5
                    )

            if len(photos) > 4:
                ttk.Label(photos_frame, text=f"+ {len(photos) - 4} more").grid(
                    row=0, column=4, padx=5, pady=5
                )

    def clear_observation_details(self):
        """Clear the observation details panel"""
        for widget in self.details_frame.winfo_children():
            widget.destroy()

        self.no_selection_label = ttk.Label(self.details_frame, text="Select an observation to view details")
        self.no_selection_label.pack(fill=tk.BOTH, expand=True)

    def show_obs_context_menu(self, event):
        """Show the observation context menu on right-click"""
        if self.observations_treeview.identify_row(event.y):
            self.observations_treeview.selection_set(self.observations_treeview.identify_row(event.y))
            self.obs_context_menu.post(event.x_root, event.y_root)

    def delete_observation(self):
        """Delete the selected observation"""
        if not self.current_observation:
            messagebox.showinfo("Information", "Please select an observation first")
            return

        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this observation?"):
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get photos to delete files
        cursor.execute("SELECT filename FROM photos WHERE observation_id = ?", (self.current_observation,))
        photos = cursor.fetchall()

        # Start transaction
        conn.execute("BEGIN TRANSACTION")

        try:
            # Delete the observation (cascades to photos and tags relations)
            cursor.execute("DELETE FROM observations WHERE id = ?", (self.current_observation,))
            conn.commit()

            # Delete photo files
            for photo in photos:
                try:
                    if os.path.exists(photo[0]):
                        os.remove(photo[0])
                except:
                    pass

            # Refresh UI
            self.load_observations()
            self.clear_observation_details()

        except sqlite3.Error as e:
            conn.rollback()
            messagebox.showerror("Database Error", str(e))
        finally:
            conn.close()

    def view_map(self):
        """View observations on a map"""
        if not self.current_lifelist:
            messagebox.showinfo("Information", "Please select a lifelist first")
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get observations with coordinates
        cursor.execute("""
            SELECT id, species, tier, latitude, longitude, location
            FROM observations
            WHERE lifelist_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
        """, (self.current_lifelist,))
        observations = cursor.fetchall()

        conn.close()

        if not observations:
            messagebox.showinfo("Information", "No observations with location data found")
            return

        # Create a map centered on the average coordinates
        avg_lat = sum(obs[3] for obs in observations) / len(observations)
        avg_lon = sum(obs[4] for obs in observations) / len(observations)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

        # Add markers for each observation
        for obs in observations:
            popup_text = f"<b>{obs[1]}</b><br>Tier: {obs[2]}"
            if obs[5]:
                popup_text += f"<br>Location: {obs[5]}"

            folium.Marker(
                location=[obs[3], obs[4]],
                popup=popup_text,
                tooltip=obs[1]
            ).add_to(m)

        # Save the map to a temporary file and open it in the browser
        map_path = os.path.join(self.db_path, "observation_map.html")
        m.save(map_path)
        webbrowser.open(f"file://{map_path}")

    def manage_custom_fields(self):
        """Manage custom fields for the current lifelist"""
        if not self.current_lifelist:
            messagebox.showinfo("Information", "Please select a lifelist first")
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT custom_fields FROM lifelists WHERE id = ?", (self.current_lifelist,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return

        custom_fields = json.loads(result[0])

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Custom Fields")
        dialog.geometry("400x400")
        dialog.grab_set()

        ttk.Label(dialog, text="Custom Fields:", font=("", 12, "bold")).pack(padx=10, pady=10)

        # List of current fields
        fields_frame = ttk.Frame(dialog)
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fields_listbox = tk.Listbox(fields_frame, width=40, height=10)
        fields_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(fields_frame, orient=tk.VERTICAL, command=fields_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        fields_listbox.config(yscrollcommand=scrollbar.set)

        # Populate listbox
        for field in custom_fields:
            fields_listbox.insert(tk.END, field)

        # Add field controls
        add_frame = ttk.Frame(dialog)
        add_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(add_frame, text="New Field:").pack(side=tk.LEFT, padx=5)
        new_field_var = tk.StringVar()
        new_field_entry = ttk.Entry(add_frame, textvariable=new_field_var, width=20)
        new_field_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        def add_field():
            field_name = new_field_var.get().strip()
            if field_name and field_name not in custom_fields:
                custom_fields.append(field_name)
                fields_listbox.insert(tk.END, field_name)
                new_field_var.set("")

        ttk.Button(add_frame, text="Add", command=add_field).pack(side=tk.LEFT, padx=5)

        # Remove field button
        def remove_field():
            selected = fields_listbox.curselection()
            if selected:
                field_name = fields_listbox.get(selected[0])
                if messagebox.askyesno("Confirm",
                                       f"Remove field '{field_name}'? This will remove this field from all observations."):
                    custom_fields.remove(field_name)
                    fields_listbox.delete(selected[0])

        ttk.Button(dialog, text="Remove Selected Field", command=remove_field).pack(pady=5)

        # Save button
        def save_fields():
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("UPDATE lifelists SET custom_fields = ? WHERE id = ?",
                           (json.dumps(custom_fields), self.current_lifelist))
            conn.commit()
            conn.close()
            dialog.destroy()

        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(pady=10)

        ttk.Button(buttons_frame, text="Save", command=save_fields).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def delete_lifelist(self):
        """Delete the current lifelist"""
        if not self.current_lifelist:
            messagebox.showinfo("Information", "Please select a lifelist first")
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM lifelists WHERE id = ?", (self.current_lifelist,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return

        lifelist_name = result[0]

        if not messagebox.askyesno("Confirm",
                                   f"Are you sure you want to delete the lifelist '{lifelist_name}'?\n\nThis will permanently delete all observations, photos, and tags associated with this lifelist."):
            return

        # Get photos to delete files
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.filename
            FROM photos p
            JOIN observations o ON p.observation_id = o.id
            WHERE o.lifelist_id = ?
        """, (self.current_lifelist,))
        photos = cursor.fetchall()

        # Start transaction
        conn.execute("BEGIN TRANSACTION")

        try:
            # Delete the lifelist (cascades to observations, which cascades to photos and tags relations)
            cursor.execute("DELETE FROM lifelists WHERE id = ?", (self.current_lifelist,))
            conn.commit()

            # Delete photo files
            for photo in photos:
                try:
                    if os.path.exists(photo[0]):
                        os.remove(photo[0])
                except:
                    pass

            # Refresh UI
            self.current_lifelist = None
            self.load_lifelists()
            self.clear_observations()

        except sqlite3.Error as e:
            conn.rollback()
            messagebox.showerror("Database Error", str(e))
        finally:
            conn.close()

    def export_lifelist(self):
        """Export the current lifelist to a JSON file"""
        if not self.current_lifelist:
            messagebox.showinfo("Information", "Please select a lifelist first")
            return

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get lifelist data
        cursor.execute("SELECT * FROM lifelists WHERE id = ?", (self.current_lifelist,))
        lifelist = cursor.fetchone()

        if not lifelist:
            conn.close()
            return

        # Get observations
        cursor.execute("SELECT * FROM observations WHERE lifelist_id = ?", (self.current_lifelist,))
        observations = cursor.fetchall()

        # Prepare export data
        export_data = {
            "lifelist": {
                "id": lifelist[0],
                "name": lifelist[1],
                "description": lifelist[2],
                "taxonomy_source": lifelist[3],
                "created_date": lifelist[4],
                "modified_date": lifelist[5],
                "custom_fields": json.loads(lifelist[6]) if lifelist[6] else []
            },
            "observations": []
        }

        # Process each observation
        for obs in observations:
            # Get photos
            cursor.execute("SELECT * FROM photos WHERE observation_id = ?", (obs[0],))
            photos = cursor.fetchall()

            # Get tags
            cursor.execute("""
                SELECT t.name 
                FROM tags t
                JOIN observation_tags ot ON t.id = ot.tag_id
                WHERE ot.observation_id = ?
            """, (obs[0],))
            tags = [tag[0] for tag in cursor.fetchall()]

            # Add to export data
            export_data["observations"].append({
                "id": obs[0],
                "species": obs[2],
                "tier": obs[3],
                "observation_date": obs[4],
                "location": obs[5],
                "notes": obs[6],
                "latitude": obs[7],
                "longitude": obs[8],
                "custom_data": json.loads(obs[9]) if obs[9] else {},
                "created_date": obs[10],
                "modified_date": obs[11],
                "thumbnail_photo": obs[12],
                "tags": tags,
                "photos": [
                    {
                        "id": photo[0],
                        "filename": os.path.basename(photo[2]),
                        "description": photo[3],
                        "latitude": photo[4],
                        "longitude": photo[5],
                        "is_thumbnail": bool(photo[6]),
                        "upload_date": photo[7]
                    } for photo in photos
                ]
            })

        conn.close()

        # Ask for save location
        filepath = filedialog.asksaveasfilename(
            title="Export Lifelist",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )

        if not filepath:
            return

        # Save the export data
        try:
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

            # Create a zip file for photos if there are any
            photo_count = sum(len(obs.get("photos", [])) for obs in export_data["observations"])

            if photo_count > 0 and messagebox.askyesno("Export Photos",
                                                       f"Export {photo_count} photos along with lifelist data?"):
                import zipfile

                zip_path = filepath.replace(".json", "_photos.zip")
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    # Add each photo to the zip
                    for obs in export_data["observations"]:
                        for photo in obs["photos"]:
                            # Get the actual photo path in our system
                            conn = sqlite3.connect(self.db_file)
                            cursor = conn.cursor()
                            cursor.execute("SELECT filename FROM photos WHERE id = ?", (photo["id"],))
                            result = cursor.fetchone()
                            conn.close()

                            if result and os.path.exists(result[0]):
                                # Add to zip with a structured path
                                archive_path = f"{obs['species']}/{photo['filename']}"
                                zip_file.write(result[0], arcname=archive_path)

                messagebox.showinfo("Export Complete",
                                    f"Lifelist exported to {filepath}\nPhotos exported to {zip_path}")
            else:
                messagebox.showinfo("Export Complete", f"Lifelist exported to {filepath}")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def import_lifelist(self):
        """Import a lifelist from a JSON file"""
        filepath = filedialog.askopenfilename(
            title="Import Lifelist",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)

            # Validate basic structure
            if not isinstance(import_data, dict) or "lifelist" not in import_data or "observations" not in import_data:
                messagebox.showerror("Import Error", "Invalid lifelist file format")
                return

            # Ask about photo import
            photo_zip_path = None
            photo_count = sum(len(obs.get("photos", [])) for obs in import_data["observations"])

            if photo_count > 0:
                if messagebox.askyesno("Import Photos",
                                       f"The lifelist contains {photo_count} photo references. Do you want to import photos from a zip file?"):
                    photo_zip_path = filedialog.askopenfilename(
                        title="Select Photos Zip File",
                        filetypes=(("ZIP files", "*.zip"), ("All files", "*.*"))
                    )

            # Connect to database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            try:
                # Generate a new ID for the lifelist
                new_lifelist_id = str(uuid.uuid4())
                lifelist = import_data["lifelist"]

                # Insert lifelist
                now = datetime.now().isoformat()
                cursor.execute(
                    """INSERT INTO lifelists (
                        id, name, description, taxonomy_source, 
                        created_date, modified_date, custom_fields
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (new_lifelist_id, lifelist["name"], lifelist.get("description", ""),
                     lifelist.get("taxonomy_source", ""), now, now,
                     json.dumps(lifelist.get("custom_fields", [])))
                )

                # ID mapping for relations
                id_mapping = {
                    "observations": {},
                    "photos": {},
                    "tags": {}
                }

                # Import tags first
                all_tags = {}
                for obs in import_data["observations"]:
                    for tag_name in obs.get("tags", []):
                        if tag_name not in all_tags:
                            # Check if tag already exists
                            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                            result = cursor.fetchone()

                            if result:
                                all_tags[tag_name] = result[0]
                            else:
                                tag_id = str(uuid.uuid4())
                                cursor.execute("INSERT INTO tags (id, name) VALUES (?, ?)",
                                               (tag_id, tag_name))
                                all_tags[tag_name] = tag_id

                # Open zip file if provided
                zip_file = None
                if photo_zip_path:
                    try:
                        import zipfile
                        zip_file = zipfile.ZipFile(photo_zip_path, 'r')
                    except:
                        messagebox.showwarning("Warning", "Could not open photos zip file. Continuing without photos.")

                # Import observations
                for obs in import_data["observations"]:
                    # Generate new ID
                    new_obs_id = str(uuid.uuid4())
                    id_mapping["observations"][obs["id"]] = new_obs_id

                    # Insert observation
                    cursor.execute(
                        """INSERT INTO observations (
                            id, lifelist_id, species, tier, observation_date, location, notes, 
                            latitude, longitude, custom_data, created_date, modified_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_obs_id, new_lifelist_id, obs["species"], obs["tier"],
                         obs.get("observation_date", ""), obs.get("location", ""), obs.get("notes", ""),
                         obs.get("latitude"), obs.get("longitude"),
                         json.dumps(obs.get("custom_data", {})), now, now)
                    )

                    # Import tags
                    for tag_name in obs.get("tags", []):
                        cursor.execute("INSERT INTO observation_tags (observation_id, tag_id) VALUES (?, ?)",
                                       (new_obs_id, all_tags[tag_name]))

                    # Import photos
                    thumbnail_id = None

                    for photo in obs.get("photos", []):
                        new_photo_id = str(uuid.uuid4())
                        id_mapping["photos"][photo["id"]] = new_photo_id

                        # Try to extract photo from zip if available
                        photo_path = None

                        if zip_file:
                            try:
                                # Look for the photo in various possible paths
                                possible_paths = [
                                    f"{obs['species']}/{photo['filename']}",
                                    photo['filename']
                                ]

                                for path in possible_paths:
                                    try:
                                        zip_info = zip_file.getinfo(path)
                                        photo_data = zip_file.read(zip_info)

                                        # Save to photos directory
                                        dest_filename = f"{new_photo_id}_{photo['filename']}"
                                        dest_path = os.path.join(self.photo_dir, dest_filename)

                                        with open(dest_path, 'wb') as f:
                                            f.write(photo_data)

                                        photo_path = dest_path
                                        break
                                    except:
                                        continue
                            except:
                                pass

                        # Insert photo record
                        cursor.execute(
                            """INSERT INTO photos (
                                id, observation_id, filename, description, latitude, longitude, 
                                is_thumbnail, upload_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (new_photo_id, new_obs_id, photo_path or "", photo.get("description", ""),
                             photo.get("latitude"), photo.get("longitude"),
                             1 if photo.get("is_thumbnail") else 0, now)
                        )

                        if photo.get("is_thumbnail"):
                            thumbnail_id = new_photo_id

                    # Update thumbnail reference
                    if thumbnail_id:
                        cursor.execute("UPDATE observations SET thumbnail_photo = ? WHERE id = ?",
                                       (thumbnail_id, new_obs_id))

                # Close zip file if opened
                if zip_file:
                    zip_file.close()

                conn.commit()

                # Refresh UI
                self.load_lifelists()

                messagebox.showinfo("Import Complete",
                                    f"Lifelist '{lifelist['name']}' imported successfully with {len(import_data['observations'])} observations")

            except Exception as e:
                conn.rollback()
                messagebox.showerror("Import Error", str(e))
            finally:
                conn.close()

        except Exception as e:
            messagebox.showerror("Import Error", str(e))


def main():
    root = tk.Tk()
    app = LifelistManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()