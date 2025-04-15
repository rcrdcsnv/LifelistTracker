# views/taxonomy_manager.py
"""
Taxonomy manager - Import and manage taxonomies
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

from LifelistTracker.navigation_controller import NavigationController
from LifelistTracker.viewmodels.taxonomy_viewmodel import TaxonomyViewModel
from LifelistTracker.views.utils import center_window

class TaxonomyManager:
    """
    UI Component for managing taxonomies
    """

    def __init__(self, controller: NavigationController, viewmodel: TaxonomyViewModel):
        """
        Initialize the taxonomy manager

        Args:
            controller: Navigation controller
            viewmodel: Taxonomy ViewModel
        """
        self.controller = controller
        self.viewmodel = viewmodel

        # Register for viewmodel state changes
        self.viewmodel.register_state_change_callback(self.on_viewmodel_changed)

    def show_dialog(self):
        """Show the taxonomy management dialog"""
        # Get the current lifelist ID from the app state
        lifelist_id = self.controller.app_state.get_current_lifelist_id()

        if not lifelist_id:
            messagebox.showerror("Error", "No lifelist selected")
            return

        # Load taxonomies from viewmodel
        self.viewmodel.load_taxonomies(lifelist_id)

        # Create dialog
        root = self.controller.root
        dialog = ctk.CTkToplevel(root)
        dialog.title("Manage Taxonomies")
        dialog.geometry("800x600")
        dialog.transient(root)
        dialog.grab_set()

        center_window(dialog)

        # Create a tabbed interface
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        taxonomies_tab = tabview.add("My Taxonomies")
        import_tab = tabview.add("Import Taxonomy")
        download_tab = tabview.add("Download Standard Taxonomies")

        # Set default tab
        tabview.set("My Taxonomies")

        # My Taxonomies tab
        self._create_taxonomies_tab(taxonomies_tab, dialog)

        # Import Taxonomy tab
        self._create_import_tab(import_tab, dialog)

        # Download Standard Taxonomies tab
        self._create_download_tab(download_tab, dialog)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

    def on_viewmodel_changed(self):
        """Handle viewmodel state changes"""
        # This would normally refresh the dialog, but since we don't keep a reference to the dialog,
        # we'll handle refreshes in the specific functions that modify the taxonomies
        pass

    def _create_taxonomies_tab(self, parent, dialog):
        """
        Create the My Taxonomies tab

        Args:
            parent: Tab widget
            dialog: Dialog window
        """
        taxonomies_frame = ctk.CTkFrame(parent)
        taxonomies_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get current taxonomies from viewmodel
        taxonomies = self.viewmodel.taxonomies

        if taxonomies:
            # Create a list of taxonomies
            headers = ctk.CTkFrame(taxonomies_frame)
            headers.pack(fill=tk.X, pady=5)

            ctk.CTkLabel(headers, text="Name", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Version", width=100, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Source", width=150, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Entries", width=80, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(headers, text="Status", width=80, font=ctk.CTkFont(weight="bold")).pack(side=tk.LEFT, padx=5)

            taxonomy_list = ctk.CTkScrollableFrame(taxonomies_frame)
            taxonomy_list.pack(fill=tk.BOTH, expand=True, pady=5)

            for taxonomy in taxonomies:
                row = ctk.CTkFrame(taxonomy_list)
                row.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(row, text=taxonomy.name, width=150).pack(side=tk.LEFT, padx=5)
                ctk.CTkLabel(row, text=taxonomy.version or "", width=100).pack(side=tk.LEFT, padx=5)
                ctk.CTkLabel(row, text=taxonomy.source or "", width=150).pack(side=tk.LEFT, padx=5)

                # Get entry count if available
                count = getattr(taxonomy, 'entry_count', 0)
                ctk.CTkLabel(row, text=str(count), width=80).pack(side=tk.LEFT, padx=5)

                # Status (active/inactive)
                status_text = "Active" if taxonomy.is_active else "Inactive"
                status_color = "green" if taxonomy.is_active else "gray50"
                status_label = ctk.CTkLabel(row, text=status_text, width=80, text_color=status_color)
                status_label.pack(side=tk.LEFT, padx=5)

                # Action buttons
                actions_frame = ctk.CTkFrame(row)
                actions_frame.pack(side=tk.RIGHT, padx=5)

                if not taxonomy.is_active:
                    activate_btn = ctk.CTkButton(
                        actions_frame,
                        text="Set Active",
                        width=80,
                        command=lambda t_id=taxonomy.id, d=dialog: self._activate_taxonomy(t_id, d)
                    )
                    activate_btn.pack(side=tk.LEFT, padx=2)

                delete_btn = ctk.CTkButton(
                    actions_frame,
                    text="Delete",
                    width=70,
                    fg_color="red3",
                    hover_color="red4",
                    command=lambda t_id=taxonomy.id, d=dialog: self._delete_taxonomy(t_id, d)
                )
                delete_btn.pack(side=tk.LEFT, padx=2)
        else:
            # No taxonomies yet
            no_tax_label = ctk.CTkLabel(
                taxonomies_frame,
                text="No taxonomies added yet. Use the Import or Download tabs to add a taxonomy.",
                wraplength=500
            )
            no_tax_label.pack(pady=50)

    def _activate_taxonomy(self, taxonomy_id, dialog):
        """Activate a taxonomy"""
        try:
            # Activate the taxonomy in viewmodel
            success = self.viewmodel.activate_taxonomy(taxonomy_id)

            if success:
                messagebox.showinfo("Success", "Taxonomy activated successfully")
                dialog.destroy()
                self.show_dialog()  # Reopen with updated info
            else:
                messagebox.showerror("Error", "Failed to activate taxonomy")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _delete_taxonomy(self, taxonomy_id, dialog):
        """Delete a taxonomy"""
        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this taxonomy? This cannot be undone."
        )

        if confirm:
            try:
                # Delete the taxonomy via viewmodel
                success = self.viewmodel.delete_taxonomy(taxonomy_id)

                if success:
                    messagebox.showinfo("Success", "Taxonomy deleted successfully")
                    dialog.destroy()
                    self.show_dialog()  # Reopen with updated info
                else:
                    messagebox.showerror("Error", "Failed to delete taxonomy")

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _create_import_tab(self, parent, dialog):
        """
        Create the Import Taxonomy tab

        Args:
            parent: Tab widget
            dialog: Dialog window
        """
        import_frame = ctk.CTkFrame(parent)
        import_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Step 1: Basic details
        step1_frame = ctk.CTkFrame(import_frame)
        step1_frame.pack(fill=tk.X, pady=10)

        ctk.CTkLabel(step1_frame, text="Step 1: Taxonomy Details", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=5)

        name_frame = ctk.CTkFrame(step1_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ctk.CTkLabel(name_frame, text="Taxonomy Name:", width=150).pack(side=tk.LEFT, padx=5)
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

        def select_file():
            file = filedialog.askopenfilename(
                title="Select Taxonomy File",
                filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")]
            )
            if file:
                file_path_var.set(file)
                # Try to preview CSV headers
                if file.lower().endswith('.csv'):
                    try:
                        success = self.viewmodel.preview_csv_headers(file)
                        if success:
                            # Update mapping UI
                            update_mapping_ui()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read CSV headers: {e}")

        def update_mapping_ui():
            # Clear existing mappings
            for widget in mapping_frame.winfo_children():
                widget.destroy()

            # Get headers and field mappings from viewmodel
            csv_headers = self.viewmodel.csv_headers
            field_mappings = self.viewmodel.field_mappings

            # Database fields to map
            db_fields = [
                ("scientific_name", "Scientific Name (required)"),
                ("common_name", "Common Name"),
                ("family", "Family"),
                ("genus", "Genus"),
                ("species", "Species"),
                ("order_name", "Order"),
                ("class_name", "Class"),
                ("code", "Code/ID"),
                ("rank", "Rank/Level")
            ]

            # Create mapping dropdowns for each database field
            for db_field, display_name in db_fields:
                row = ctk.CTkFrame(mapping_frame)
                row.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(row, text=display_name + ":", width=200).pack(side=tk.LEFT, padx=5)

                # Create dropdown with CSV headers
                field_var = tk.StringVar()

                # Set initial value if mapping exists
                if db_field in field_mappings:
                    field_var.set(field_mappings[db_field])

                dropdown = ctk.CTkComboBox(
                    row,
                    values=[""] + csv_headers,
                    variable=field_var,
                    width=300,
                    command=lambda f=db_field, v=field_var: self.viewmodel.update_field_mapping(f, v.get())
                )
                dropdown.pack(side=tk.LEFT, padx=5)

        browse_btn = ctk.CTkButton(file_frame, text="Browse", width=80, command=select_file)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # Import button
        def import_taxonomy():
            name = name_entry.get().strip()
            version = version_entry.get().strip()
            source = source_entry.get().strip()
            file_path = file_path_var.get()

            if not name:
                messagebox.showerror("Error", "Taxonomy name is required")
                return

            if not file_path:
                messagebox.showerror("Error", "Please select a file")
                return

            if "scientific_name" not in self.viewmodel.field_mappings:
                messagebox.showerror("Error", "Scientific Name mapping is required")
                return

            # Import taxonomy via viewmodel
            taxonomy_id = self.viewmodel.import_taxonomy(name, version, source, file_path)

            if taxonomy_id:
                messagebox.showinfo("Success", "Taxonomy imported successfully")
                dialog.destroy()
                self.show_dialog()  # Reopen with updated info
            else:
                messagebox.showerror("Error", "Failed to import taxonomy")

        import_btn = ctk.CTkButton(
            import_frame,
            text="Import Taxonomy",
            command=import_taxonomy
        )
        import_btn.pack(pady=15)

    def _create_download_tab(self, parent):
        """
        Create the Download Standard Taxonomies tab

        Args:
            parent: Tab widget
        """
        ctk.CTkLabel(
            parent,
            text="Download Standard Taxonomies",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            parent,
            text="Select a standard taxonomy to download and import automatically.",
            wraplength=500
        ).pack(pady=5)

        # List of standard taxonomies
        standards_frame = ctk.CTkScrollableFrame(parent)
        standards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for tax in self.viewmodel.standard_taxonomies:
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
                command=lambda t=tax: self._download_taxonomy(t)
            )
            download_btn.pack(side=tk.RIGHT, padx=5)

    def _download_taxonomy(self, taxonomy_info):
        """
        Download and import a standard taxonomy

        Args:
            taxonomy_info: Dictionary with taxonomy information
        """
        dialog = ctk.CTkToplevel(self.controller.root)
        dialog.title(f"Downloading {taxonomy_info['name']}")
        dialog.geometry("400x200")
        dialog.transient(self.controller.root)
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

        # Progress callback
        def progress_callback(progress, status):
            dialog.after(0, lambda: progress_bar.set(progress))
            dialog.after(0, lambda: info_label.configure(text=status))

            if progress >= 1:
                dialog.after(0, lambda: status_label.configure(text="Download Complete"))
                dialog.after(0, lambda: cancel_btn.configure(text="Close"))
                dialog.after(3000, lambda: (dialog.destroy(), self.show_dialog()))

        # Start download in a separate thread
        download_thread = threading.Thread(
            target=lambda: self.viewmodel.download_standard_taxonomy(
                taxonomy_info, progress_callback
            )
        )
        download_thread.daemon = True
        download_thread.start()