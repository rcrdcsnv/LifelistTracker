"""
Classification manager - Import and manage classifications
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import tempfile
import requests
from os import path

from database_factory import DatabaseFactory
from ui.utils import center_window
from file_utils import FileUtils


class ClassificationManager:
    """
    UI Component for managing classifications (formerly taxonomies)
    """

    def __init__(self, controller, db, root):
        """
        Initialize the classification manager

        Args:
            controller: Navigation controller
            db: Database connection
            root: Root window
        """
        self.controller = controller
        self.db = db
        self.root = root
        self.app_state = controller.app_state if hasattr(controller, 'app_state') else None

        # Dictionary of standard classification download endpoints and mapping information
        self.classification_endpoints = {
            "eBird Taxonomy v2023": {
                "url": "https://media.ebird.org/catalog/resource/eBird_Taxonomy_v2023.csv",
                "mapping": {
                    "name": "SCI_NAME",
                    "alternate_name": "PRIMARY_COM_NAME",
                    "category": "FAMILY",
                    "parent_id": None,
                    "code": "SPECIES_CODE",
                    "rank": "CATEGORY"
                }
            },
            "IOC World Bird List v13.1": {
                "url": "https://www.worldbirdnames.org/IOC_names_export_13.1.csv",
                "mapping": {
                    "name": "Scientific name",
                    "alternate_name": "English name",
                    "category": "Family",
                    "parent_id": None,
                    "code": None,
                    "rank": "Order"
                }
            },
            "Mammal Species of the World": {
                "url": "https://www.mammaldiversity.org/assets/data/MDD_v1.11_6818species.csv",
                "mapping": {
                    "name": "sciName",
                    "alternate_name": "vernacularName",
                    "category": "familyNameValid",
                    "parent_id": None,
                    "code": None,
                    "rank": "orderNameValid"
                }
            },
            "The Plant List": {
                "url": "https://raw.githubusercontent.com/crazybilly/tpldata/master/data/namesAccepted.csv",
                "mapping": {
                    "name": "ScientificName",
                    "alternate_name": None,
                    "category": "Family",
                    "parent_id": None,
                    "code": None,
                    "rank": "Genus"
				}
            },
            "Catalog of Life": {
                "url": "https://api.checklistbank.org/dataset/9820/export.csv?format=SimpleDwC",
                "mapping": {
                    "scientific_name": "scientificName",
                    "common_name": "vernacularName",
                    "family": "family",
                    "order_name": "order",
                    "genus": "genus",
                    "species": "specificEpithet",
                    "rank": "taxonRank"
                }
            }
        }

        # Define standard classifications with their info
        self.standard_classifications = [
            {
                "name": "eBird Taxonomy v2023",
                "description": "The eBird/Clements taxonomy, updated 2023",
                "url": "https://www.birds.cornell.edu/clementschecklist/download/",
                "type": "Wildlife"
            },
            {
                "name": "IOC World Bird List v13.1",
                "description": "International Ornithological Congress bird list",
                "url": "https://www.worldbirdnames.org/new/ioc-lists/master-list-2/",
                "type": "Wildlife"
            },
            {
                "name": "Mammal Species of the World",
                "description": "Comprehensive mammal taxonomy",
                "url": "https://www.departments.bucknell.edu/biology/resources/msw3/",
                "type": "Wildlife"
            },
            {
                "name": "The Plant List",
                "description": "Working list of all known plant species",
                "url": "http://www.theplantlist.org/",
                "type": "Plants"
            },
            {
                "name": "Catalog of Life",
                "description": "Global index of all known species",
                "url": "https://www.catalogueoflife.org/data/download",
                "type": "comprehensive"
            },
        ]

    def show_dialog(self):
        """Show the classification management dialog"""
        lifelist_id = self.app_state.get_current_lifelist_id() if self.app_state else None

        if not lifelist_id:
            messagebox.showerror("Error", "No lifelist selected")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Manage Classifications")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()

        center_window(dialog)

        # Get lifelist type
        lifelist_type = self.app_state.get_current_lifelist_type()
        entry_term = self.app_state.get_entry_term()

        # Create a tabbed interface
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        classifications_tab = tabview.add("My Classifications")
        import_tab = tabview.add("Import Classification")
        download_tab = tabview.add("Download Standard Classifications")

        # Set default tab
        tabview.set("My Classifications")

        # My Classifications tab
        self._create_classifications_tab(classifications_tab, dialog, lifelist_id, entry_term)

        # Import Classification tab
        self._create_import_tab(import_tab, dialog, lifelist_id, entry_term)

        # Download Standard Classifications tab
        self._create_download_tab(download_tab, lifelist_id, lifelist_type)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

    def _create_classifications_tab(self, parent, dialog, lifelist_id, entry_term):
        """
        Create the My Classifications tab

        Args:
            parent: Tab widget
            dialog: Dialog window
            lifelist_id: Current lifelist ID
            entry_term: Term used for entries in this lifelist
        """
        classifications_frame = ctk.CTkFrame(parent)
        classifications_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get current classifications
        if classifications := self.db.get_classifications(lifelist_id):
            # Create a list of classifications
            headers = ctk.CTkFrame(classifications_frame)
            headers.pack(fill=tk.X, pady=5)

            ctk.CTkLabel(headers, text="Name", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Version", width=100, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Source", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Entries", width=80, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Status", width=80, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)

            classification_list = ctk.CTkScrollableFrame(classifications_frame)
            classification_list.pack(fill=tk.BOTH, expand=True, pady=5)

            for tax_id, name, version, source, description, is_active in classifications:
                # Count entries in this classification
                self.db.cursor.execute("SELECT COUNT(*) FROM classification_entries WHERE classification_id = ?", (tax_id,))
                count = self.db.cursor.fetchone()[0]

                row = ctk.CTkFrame(classification_list)
                row.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(row, text=name, width=150).pack(side=tk.LEFT, padx=5)
                ctk.CTkLabel(row, text=version or "", width=100).pack(side=tk.LEFT, padx=5)
                ctk.CTkLabel(row, text=source or "", width=150).pack(side=tk.LEFT, padx=5)
                ctk.CTkLabel(row, text=str(count), width=80).pack(side=tk.LEFT, padx=5)

                # Status (active/inactive)
                status_text = "Active" if is_active else "Inactive"
                status_color = "green" if is_active else "gray50"
                status_label = ctk.CTkLabel(row, text=status_text, width=80, text_color=status_color)
                status_label.pack(side=tk.LEFT, padx=5)

                # Action buttons
                actions_frame = ctk.CTkFrame(row)
                actions_frame.pack(side=tk.RIGHT, padx=5)

                if not is_active:
                    activate_btn = ctk.CTkButton(
                        actions_frame,
                        text="Set Active",
                        width=80,
                        command=lambda t_id=tax_id, lid=lifelist_id: self._activate_classification(t_id, lid, dialog)
                    )
                    activate_btn.pack(side=tk.LEFT, padx=2)

                delete_btn = ctk.CTkButton(
                    actions_frame,
                    text="Delete",
                    width=70,
                    fg_color="red3",
                    hover_color="red4",
                    command=lambda t_id=tax_id, lid=lifelist_id: self._delete_classification(t_id, lid, dialog)
                )
                delete_btn.pack(side=tk.LEFT, padx=2)
        else:
            # No classifications yet
            no_tax_label = ctk.CTkLabel(
                classifications_frame,
                text=f"No classifications added yet. A classification system helps organize your {entry_term} entries and enables auto-complete features. Use the Import or Download tabs to add a classification.",
                wraplength=500
            )
            no_tax_label.pack(pady=50)

    def _activate_classification(self, classification_id, lifelist_id, dialog):
        """Activate a classification"""
        try:
            db = DatabaseFactory.get_database()

            # Execute activation in a transaction
            if success := db.execute_transaction(
                lambda: db.set_active_classification(
                    classification_id, lifelist_id
                )
            ):
                messagebox.showinfo("Success", "Classification activated successfully")
                dialog.destroy()
                self.show_dialog()  # Reopen with updated info
            else:
                messagebox.showerror("Error", "Failed to activate classification")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _delete_classification(self, classification_id, lifelist_id, dialog):
        """Delete a classification"""
        if confirm := messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this classification? This cannot be undone.",
        ):
            try:
                # Get database without context manager
                db = DatabaseFactory.get_database()

                # Execute deletion in a transaction
                if success := db.execute_transaction(
                    lambda: {
                        db.cursor.execute(
                            "DELETE FROM classifications WHERE id = ?",
                            (classification_id,),
                        )
                    }
                ):
                    messagebox.showinfo("Success", "Classification deleted successfully")
                dialog.destroy()
                self.show_dialog()  # Reopen with updated info

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _create_import_tab(self, parent, dialog, lifelist_id, entry_term):
        """
        Create the Import Classification tab

        Args:
            parent: Tab widget
            dialog: Dialog window
            lifelist_id: Current lifelist ID
            entry_term: Term used for entries in this lifelist
        """
        import_frame = ctk.CTkFrame(parent)
        import_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Step 1: Basic details
        step1_frame = ctk.CTkFrame(import_frame)
        step1_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(step1_frame, text="Step 1: Classification Details", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=5)

        name_frame = ctk.CTkFrame(step1_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ctk.CTkLabel(name_frame, text="Classification Name:", width=150).pack(side=tk.LEFT, padx=5)
        name_entry = ctk.CTkEntry(name_frame, width=300)
        name_entry.pack(side=tk.LEFT, padx=5)

        version_frame = ctk.CTkFrame(step1_frame)
        version_frame.pack(fill=tk.X, pady=2)
        ctk.CTkLabel(version_frame, text="Version:", width=150).pack(side=tk.LEFT, padx=5)
        version_entry = ctk.CTkEntry(version_frame, width=300)
        version_entry.pack(side=tk.LEFT, padx=5)

        source_frame = ctk.CTkFrame(step1_frame)
        source_frame.pack(fill=tk.X, pady=2)
        ctk.CTkLabel(source_frame, text="Source:", width=150).pack(side=tk.LEFT, padx=5)
        source_entry = ctk.CTkEntry(source_frame, width=300)
        source_entry.pack(side=tk.LEFT, padx=5)

        # Step 2: File selection
        step2_frame = ctk.CTkFrame(import_frame)
        step2_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(step2_frame, text="Step 2: Select File", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        file_frame = ctk.CTkFrame(step2_frame)
        file_frame.pack(fill=tk.X, pady=5)

        file_path_var = tk.StringVar()
        ctk.CTkLabel(file_frame, text="CSV File:", width=150).pack(side=tk.LEFT, padx=5)
        file_path_entry = ctk.CTkEntry(file_frame, width=300, textvariable=file_path_var)
        file_path_entry.pack(side=tk.LEFT, padx=5)

        # Step 3: Field mapping
        step3_frame = ctk.CTkFrame(import_frame)
        step3_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(step3_frame, text="Step 3: Map Fields", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        mapping_frame = ctk.CTkScrollableFrame(step3_frame, height=200)
        mapping_frame.pack(fill=tk.X, pady=5)

        # Variable to store field mappings
        field_mappings = {}
        csv_headers = []

        def preview_headers(headers):
            nonlocal csv_headers
            csv_headers = headers

            # Clear existing mappings
            for widget in mapping_frame.winfo_children():
                widget.destroy()

            field_mappings.clear()

            # Database fields to map
            db_fields = [
                ("name", f"{entry_term.capitalize()} Name (required)"),
                ("alternate_name", "Alternate Name"),
                ("category", "Category/Family"),
                ("parent_id", "Parent ID"),
                ("code", "Code/ID"),
                ("rank", "Rank/Level")
            ]

            # Create mapping dropdowns for each database field
            for db_field, display_name in db_fields:
                row = ctk.CTkFrame(mapping_frame)
                row.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(row, text=f"{display_name}:", width=200).pack(
                    side=tk.LEFT, padx=5
                )

                # Create dropdown with CSV headers
                field_var = tk.StringVar()

                # Try to guess the mapping based on common field names
                guess = ""
                for header in headers:
                    header_lower = header.lower()
                    if db_field == "name" and any(x in header_lower for x in ["name", "title", "entry"]):
                        guess = header
                    elif db_field == "alternate_name" and any(x in header_lower for x in ["alternate", "other", "common", "english"]):
                        guess = header
                    elif db_field.lower() in header_lower:
                        guess = header

                if guess:
                    field_var.set(guess)
                    field_mappings[db_field] = guess

                dropdown = ctk.CTkComboBox(
                    row,
                    values=[""] + headers,
                    variable=field_var,
                    width=300,
                    command=lambda f=db_field, v=field_var: update_mapping(f, v.get())
                )
                dropdown.pack(side=tk.LEFT, padx=5)

        def update_mapping(db_field, csv_field):
            if csv_field:
                field_mappings[db_field] = csv_field
            elif db_field in field_mappings:
                del field_mappings[db_field]

        def select_file():
            file = filedialog.askopenfilename(
                title="Select Classification File",
                filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")]
            )
            if file:
                file_path_var.set(file)
                # Try to read headers if it's a CSV
                if file.lower().endswith('.csv'):
                    try:
                        # Use FileUtils instead of direct file operations
                        rows, headers = FileUtils.read_csv_rows(file)
                        if headers:
                            preview_headers(headers)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read CSV headers: {e}")

        browse_btn = ctk.CTkButton(file_frame, text="Browse", width=80, command=select_file)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # Import button
        import_btn = ctk.CTkButton(
            import_frame,
            text="Import Classification",
            command=lambda: self._import_classification(lifelist_id, name_entry, version_entry, source_entry,
                                                  file_path_var, field_mappings, dialog)
        )
        import_btn.pack(pady=15)

    def _import_classification(self, lifelist_id, name_entry, version_entry, source_entry, file_path_var, field_mappings, dialog):
        """
        Import a classification from a file

        Args:
            lifelist_id: ID of the lifelist
            name_entry: Classification name entry widget
            version_entry: Version entry widget
            source_entry: Source entry widget
            file_path_var: File path variable
            field_mappings: Dictionary of field mappings
            dialog: Dialog window to close after import
        """
        # Validate inputs
        name = name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Classification name is required")
            return

        file_path = file_path_var.get()
        if not file_path or not path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file")
            return

        if "name" not in field_mappings or not field_mappings["name"]:
            messagebox.showerror("Error", "Name mapping is required")
            return

        try:
            # Get database without context manager
            db = DatabaseFactory.get_database()

            def import_operations():
                # Create the classification
                classification_id = db.add_classification(
                    lifelist_id,
                    name,
                    version_entry.get().strip() or None,
                    source_entry.get().strip() or None
                )

                if not classification_id:
                    raise Exception("Failed to create classification")

                # Import the data
                # First, read the CSV file
                rows, headers = FileUtils.read_csv_rows(file_path)
                
                # Process each row
                count = 0
                for row in rows:
                    entry_data = {}
                    
                    # Map CSV fields to database fields
                    for db_field, csv_field in field_mappings.items():
                        if csv_field and csv_field in headers:
                            index = headers.index(csv_field)
                            if index < len(row):
                                entry_data[db_field] = row[index]
                    
                    # Check if we have at least a name
                    if "name" in entry_data and entry_data["name"]:
                        # Convert any unmapped fields to additional_data
                        additional_data = {}
                        for i, header in enumerate(headers):
                            if i < len(row) and row[i] and header not in field_mappings.values():
                                additional_data[header] = row[i]
                        
                        # Add the entry to the database
                        db.add_classification_entry(
                            classification_id,
                            entry_data.get("name"),
                            entry_data.get("alternate_name"),
                            entry_data.get("parent_id"),
                            entry_data.get("category"),
                            entry_data.get("code"),
                            entry_data.get("rank"),
                            0,  # is_custom
                            additional_data or None
                        )
                        count += 1

                # Set this as the active classification if it's the first one
                if not db.get_active_classification(lifelist_id):
                    db.set_active_classification(classification_id, lifelist_id)

                return count

            # Execute all import operations in a transaction
            count = db.execute_transaction(import_operations)

            if count >= 0:
                messagebox.showinfo("Success", f"Successfully imported {count} classification entries")
                dialog.destroy()
                self.show_dialog()  # Reopen with updated info
            else:
                messagebox.showerror("Error", "Failed to import classification data")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _create_download_tab(self, parent, lifelist_id, lifelist_type):
        """
        Create the Download Standard Classifications tab

        Args:
            parent: Tab widget
            lifelist_id: Current lifelist ID
            lifelist_type: Type of the current lifelist
        """
        download_frame = ctk.CTkFrame(parent)
        download_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            parent,
            text="Download Standard Classifications",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            parent,
            text="Select a standard classification to download and import automatically.",
            wraplength=500
        ).pack(pady=5)

        # List of standard classifications
        standards_frame = ctk.CTkScrollableFrame(parent)
        standards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Filter classifications based on lifelist type if provided
        filtered_classifications = self.standard_classifications
        if lifelist_type:
            filtered_classifications = [tax for tax in self.standard_classifications if tax["type"] == lifelist_type]

        if not filtered_classifications:
            no_tax_label = ctk.CTkLabel(
                standards_frame,
                text=f"No standard classifications available for {lifelist_type} lifelists.",
                wraplength=500
            )
            no_tax_label.pack(pady=50)
            return

        for tax in filtered_classifications:
            tax_frame = ctk.CTkFrame(standards_frame)
            tax_frame.pack(fill=tk.X, pady=5, padx=5)

            info_frame = ctk.CTkFrame(tax_frame)
            info_frame.pack(fill=tk.X, side=tk.TOP, pady=5, padx=5)

            ctk.CTkLabel(
                info_frame,
                text=tax["name"],
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_frame,
                text=tax["description"],
                wraplength=500
            ).pack(anchor="w", pady=2)

            ctk.CTkLabel(
                info_frame,
                text=f"Type: {tax['type']}",
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w", pady=2)

            btn_frame = ctk.CTkFrame(tax_frame)
            btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5, padx=5)

            import webbrowser
            visit_btn = ctk.CTkButton(
                btn_frame,
                text="Visit Website",
                width=120,
                command=lambda url=tax["url"]: webbrowser.open(url)
            )
            visit_btn.pack(side=tk.LEFT, padx=5)

            download_btn = ctk.CTkButton(
                btn_frame,
                text="Download & Import",
                width=120,
                command=lambda t=tax, lid=lifelist_id: self.download_standard_classification(t, lid)
            )
            download_btn.pack(side=tk.RIGHT, padx=5)

    def download_standard_classification(self, taxonomy_info, lifelist_id):
        """
        Download and import a standard classification

        Args:
            taxonomy_info: Dictionary with classification information
            lifelist_id: ID of the lifelist
        """
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Downloading {taxonomy_info['name']}")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        center_window(dialog)

        # Progress display
        status_label = ctk.CTkLabel(
            dialog,
            text=f"Downloading {taxonomy_info['name']}...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        status_label.pack(pady=20)

        progress_bar = ctk.CTkProgressBar(dialog, width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        info_label = ctk.CTkLabel(dialog, text="Starting download...")
        info_label.pack(pady=10)

        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_btn.pack(pady=10)

        # Configure the download based on the selected classification
        endpoint_info = self.classification_endpoints.get(taxonomy_info["name"])

        if not endpoint_info:
            status_label.configure(text="Error: Classification information not found")
            info_label.configure(text="Please try a different classification")
            return

        def download_task():
            try:
                # Update status
                dialog.after(0, lambda: status_label.configure(text=f"Downloading {taxonomy_info['name']}..."))
                dialog.after(0, lambda: info_label.configure(text="Connecting to server..."))

                # Create a temporary file to store the download
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
                temp_file_path = temp_file.name
                temp_file.close()

                # Download the file with progress tracking
                response = requests.get(endpoint_info["url"], stream=True)
                response.raise_for_status()

                # Get total file size
                total_size = int(response.headers.get('content-length', 0))

                # Download with progress updates
                downloaded = 0
                with open(temp_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress
                            if total_size:
                                progress = downloaded / total_size
                                dialog.after(0, lambda p=progress: progress_bar.set(p))
                                dialog.after(0, lambda d=downloaded, t=total_size:
                                info_label.configure(
                                    text=f"Downloaded {d / 1024 / 1024:.1f} MB of {t / 1024 / 1024:.1f} MB"))

                # Update status
                dialog.after(0, lambda: status_label.configure(text="Processing data..."))
                dialog.after(0, lambda: info_label.configure(text="This may take a few moments..."))
                dialog.after(0, lambda: progress_bar.set(0))

                # Process the downloaded CSV
                # Create the classification
                with DatabaseFactory.get_database() as db:
                    try:
                        def import_operations():
                            # Create the classification
                            classification_id = db.add_classification(
                                lifelist_id,
                                taxonomy_info["name"],
                                version=taxonomy_info.get("version", ""),
                                source=taxonomy_info.get("url", ""),
                                description=taxonomy_info.get("description", "")
                            )

                            if not classification_id:
                                raise Exception("Failed to create classification")

                            # Read the CSV file
                            rows, headers = FileUtils.read_csv_rows(temp_file_path)

                            # Process each row
                            count = 0
                            for row in rows:
                                entry_data = {}

                                # Map CSV fields to database fields
                                for db_field, csv_field in endpoint_info["mapping"].items():
                                    if csv_field and csv_field in headers:
                                        index = headers.index(csv_field)
                                        if index < len(row):
                                            entry_data[db_field] = row[index]

                                # Check if we have at least a name
                                if "name" in entry_data and entry_data["name"]:
                                    # Convert any unmapped fields to additional_data
                                    additional_data = {}
                                    for i, header in enumerate(headers):
                                        mapped_fields = [f for f in endpoint_info["mapping"].values() if f is not None]
                                        if i < len(row) and row[i] and header not in mapped_fields:
                                            additional_data[header] = row[i]

                                    # Add the entry to the database
                                    db.add_classification_entry(
                                        classification_id,
                                        entry_data.get("name"),
                                        entry_data.get("alternate_name"),
                                        entry_data.get("parent_id"),
                                        entry_data.get("category"),
                                        entry_data.get("code"),
                                        entry_data.get("rank"),
                                        0,  # is_custom
                                        additional_data or None
                                    )
                                    count += 1

                            # Set as active classification if it's the first one
                            if not db.get_active_classification(lifelist_id):
                                db.set_active_classification(classification_id, lifelist_id)

                            return count

                        count = db.execute_transaction(import_operations)
                    except Exception as e:
                        print(f"Error importing classification: {e}")
                        raise Exception("Failed to create classification")

                # Clean up the temporary file
                try:
                    FileUtils.delete_file(temp_file_path)
                except Exception:
                    pass

                if count >= 0:
                    dialog.after(0, lambda: status_label.configure(text="Download Complete"))
                    dialog.after(0,
                                 lambda: info_label.configure(text=f"Successfully imported {count} classification entries"))
                    dialog.after(0, lambda: progress_bar.set(1))
                    dialog.after(0, lambda: cancel_btn.configure(text="Close"))

                    # Close dialog and reopen classification manager after a delay
                    dialog.after(3000, lambda: (dialog.destroy(), self.show_dialog()))
                else:
                    dialog.after(0, lambda: status_label.configure(text="Error: Import Failed"))
                    dialog.after(0, lambda: info_label.configure(text="Failed to import classification data"))
                    dialog.after(0, lambda: cancel_btn.configure(text="Close"))

            except Exception as e:
                dialog.after(0, lambda: status_label.configure(text="Error"))
                dialog.after(0, lambda: info_label.configure(text=f"Download failed: {str(e)}"))
                dialog.after(0, lambda: cancel_btn.configure(text="Close"))

        # Start the download in a separate thread
        download_thread = threading.Thread(target=download_task)
        download_thread.daemon = True
        download_thread.start()