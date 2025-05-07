"""
Lifelist Wizard - Guide users through creating new lifelists
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from database_factory import DatabaseFactory
from config_manager import ConfigManager
from ui.utils import center_window, create_labeled_entry

class LifelistWizard:
    """
    UI Component for guiding users through creating new lifelists
    """

    def __init__(self, parent, controller, callback=None):
        """
        Initialize the lifelist wizard

        Args:
            parent: Parent widget
            controller: Navigation controller
            callback: Function to call after successful creation
        """
        self.parent = parent
        self.controller = controller
        self.callback = callback
        self.config = ConfigManager.get_instance()
        
        # State variables
        self.selected_type_id = None
        self.custom_field_entries = []
        self.tier_entries = []
        self.db = DatabaseFactory.get_database()
        
        # Create and show the wizard dialog
        self.create_wizard_dialog()
        
    def create_wizard_dialog(self):
        """Create the wizard dialog"""
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Create New Lifelist")
        self.dialog.geometry("700x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        center_window(self.dialog)
        
        # Create a tabbed interface for the wizard
        self.tabview = ctk.CTkTabview(self.dialog)
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs for each step
        self.tab_type = self.tabview.add("1. Type")
        self.tab_info = self.tabview.add("2. Info")
        self.tab_fields = self.tabview.add("3. Fields")
        self.tab_tiers = self.tabview.add("4. Tiers")
        self.tab_summary = self.tabview.add("5. Summary")
        
        # Create the content for each tab
        self.create_type_tab()
        self.create_info_tab()
        self.create_fields_tab()
        self.create_tiers_tab()
        self.create_summary_tab()
        
        # Set the initial tab
        self.tabview.set("1. Type")
        
        # Create navigation buttons at the bottom
        self.buttons_frame = ctk.CTkFrame(self.dialog)
        self.buttons_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.cancel_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            command=self.dialog.destroy
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        self.prev_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Previous",
            command=self.go_previous
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.prev_btn.configure(state="disabled")
        
        self.next_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Next",
            command=self.go_next
        )
        self.next_btn.pack(side=tk.RIGHT, padx=5)
        
        self.finish_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Create Lifelist",
            command=self.create_lifelist
        )
        
        # Track current tab index
        self.current_tab_index = 0
        self.total_tabs = 5
        
    def create_type_tab(self):
        """Create the lifelist type selection tab"""
        ctk.CTkLabel(
            self.tab_type,
            text="What type of lifelist do you want to create?",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            self.tab_type,
            text="Choose a lifelist type to get started with appropriate fields and settings.",
            wraplength=500
        ).pack(pady=(0, 20))
        
        # Create a scrollable frame for type options
        types_frame = ctk.CTkScrollableFrame(self.tab_type)
        types_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Get all lifelist types from the database
        lifelist_types = self.db.get_lifelist_types()
        
        # Variable to track the selected type
        self.selected_type_var = tk.IntVar(value=0)
        
        # Create a selection for each type
        for type_id, type_name, type_desc, _ in lifelist_types:
            # Get default template for this type
            template = self.config.get_lifelist_type_template(type_name)
            entry_term = template.get("entry_term", "item")
            
            # Create a frame for this type option
            type_frame = ctk.CTkFrame(types_frame)
            type_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Create a radio button
            type_radio = ctk.CTkRadioButton(
                type_frame,
                text=type_name,
                variable=self.selected_type_var,
                value=type_id,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            type_radio.pack(anchor="w", padx=10, pady=(10, 5))
            
            # Description
            desc_label = ctk.CTkLabel(
                type_frame,
                text=type_desc,
                wraplength=500,
                justify="left"
            )
            desc_label.pack(anchor="w", padx=30, pady=(0, 5))
            
            # Example text
            example_text = f"Example entries: Track {entry_term}s like..."
            example_label = ctk.CTkLabel(
                type_frame,
                text=example_text,
                wraplength=500,
                justify="left",
                font=ctk.CTkFont(size=12, slant="italic")
            )
            example_label.pack(anchor="w", padx=30, pady=(0, 10))
            
    def create_info_tab(self):
        """Create the basic information tab"""
        ctk.CTkLabel(
            self.tab_info,
            text="Basic Information",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        # Name field
        self.name_frame, self.name_entry = create_labeled_entry(
            self.tab_info, "Lifelist Name:", 300)
        self.name_frame.pack(pady=10)
        
        # Description field
        desc_frame = ctk.CTkFrame(self.tab_info)
        desc_frame.pack(fill=tk.X, pady=10)
        
        ctk.CTkLabel(desc_frame, text="Description:", width=150).pack(side=tk.LEFT, padx=5, anchor="n")
        
        self.desc_text = ctk.CTkTextbox(desc_frame, width=300, height=100)
        self.desc_text.pack(side=tk.LEFT, padx=5)
        
        # Classification field
        self.class_frame, self.class_entry = create_labeled_entry(
            self.tab_info, "Classification System:", 300, 
            "(Optional) e.g., 'Clements Checklist' for birds")
        self.class_frame.pack(pady=10)
        
    def create_fields_tab(self):
        """Create the custom fields tab"""
        ctk.CTkLabel(
            self.tab_fields,
            text="Custom Fields",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        self.fields_desc_label = ctk.CTkLabel(
            self.tab_fields,
            text="Define custom fields to track additional information for each entry.",
            wraplength=500
        )
        self.fields_desc_label.pack(pady=(0, 20))
        
        # Frame for field list
        self.fields_container = ctk.CTkFrame(self.tab_fields)
        self.fields_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Scrollable frame for fields
        self.fields_scroll = ctk.CTkScrollableFrame(self.fields_container)
        self.fields_scroll.pack(fill=tk.BOTH, expand=True)
        
        # Button to add a new field
        self.add_field_btn = ctk.CTkButton(
            self.tab_fields,
            text="+ Add Custom Field",
            command=self.add_custom_field_row
        )
        self.add_field_btn.pack(pady=10)
        
    def create_tiers_tab(self):
        """Create the tiers tab"""
        ctk.CTkLabel(
            self.tab_tiers,
            text="Observation Tiers",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        self.tiers_desc_label = ctk.CTkLabel(
            self.tab_tiers,
            text="Define tiers to categorize your observations.",
            wraplength=500
        )
        self.tiers_desc_label.pack(pady=(0, 20))
        
        # Frame for tier list
        self.tiers_container = ctk.CTkFrame(self.tab_tiers)
        self.tiers_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Scrollable frame for tiers
        self.tiers_scroll = ctk.CTkScrollableFrame(self.tiers_container)
        self.tiers_scroll.pack(fill=tk.BOTH, expand=True)
        
        # Button to add a new tier
        self.add_tier_btn = ctk.CTkButton(
            self.tab_tiers,
            text="+ Add Tier",
            command=self.add_tier_row
        )
        self.add_tier_btn.pack(pady=10)
        
    def create_summary_tab(self):
        """Create the summary tab"""
        ctk.CTkLabel(
            self.tab_summary,
            text="Summary",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        # Scrollable frame for summary
        self.summary_scroll = ctk.CTkScrollableFrame(self.tab_summary)
        self.summary_scroll.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Summary sections will be populated when this tab is shown
        
    def add_custom_field_row(self, field_name="", field_type="text", is_required=False, field_options=None):
        """Add a row for a custom field"""
        row_frame = ctk.CTkFrame(self.fields_scroll)
        row_frame.pack(fill=tk.X, pady=5)
        
        # Field name
        name_entry = ctk.CTkEntry(row_frame, width=150, placeholder_text="Field Name")
        name_entry.pack(side=tk.LEFT, padx=5)
        if field_name:
            name_entry.insert(0, field_name)
        
        # Field type
        field_types = ["text", "number", "date", "boolean", "choice", "rating", "color"]
        type_var = tk.StringVar(value=field_type)
        type_dropdown = ctk.CTkComboBox(
            row_frame, 
            values=field_types,
            variable=type_var,
            width=120
        )
        type_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Required checkbox
        required_var = tk.BooleanVar(value=is_required)
        required_check = ctk.CTkCheckBox(
            row_frame, 
            text="Required", 
            variable=required_var
        )
        required_check.pack(side=tk.LEFT, padx=5)
        
        # Options button (for choice and rating fields)
        options_btn = ctk.CTkButton(
            row_frame,
            text="Options",
            width=70,
            command=lambda: self.show_field_options_dialog(field_options, type_var)
        )
        options_btn.pack(side=tk.LEFT, padx=5)
        
        # Remove button
        remove_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            command=lambda: self.remove_field_row(row_frame)
        )
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # Store the row data
        self.custom_field_entries.append({
            "frame": row_frame,
            "name": name_entry,
            "type": type_var,
            "required": required_var,
            "options": field_options,
            "options_btn": options_btn
        })
        
    def show_field_options_dialog(self, current_options, type_var):
        """Show dialog to configure field options"""
        field_type = type_var.get()
        
        # Create dialog
        options_dialog = ctk.CTkToplevel(self.dialog)
        options_dialog.title(f"Configure {field_type.capitalize()} Field")
        options_dialog.geometry("500x400")
        options_dialog.transient(self.dialog)
        options_dialog.grab_set()
        
        center_window(options_dialog)
        
        # Different options based on field type
        if field_type == "choice":
            # Choice field options
            ctk.CTkLabel(
                options_dialog,
                text="Define Choice Options",
                font=ctk.CTkFont(size=16, weight="bold")
            ).pack(pady=(20, 10))
            
            # Scrollable frame for options
            options_scroll = ctk.CTkScrollableFrame(options_dialog)
            options_scroll.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            option_entries = []
            
            def add_option_row(value="", label=""):
                row = ctk.CTkFrame(options_scroll)
                row.pack(fill=tk.X, pady=2)
                
                value_entry = ctk.CTkEntry(row, width=150, placeholder_text="Value")
                value_entry.pack(side=tk.LEFT, padx=5)
                if value:
                    value_entry.insert(0, value)
                
                label_entry = ctk.CTkEntry(row, width=150, placeholder_text="Display Label (optional)")
                label_entry.pack(side=tk.LEFT, padx=5)
                if label:
                    label_entry.insert(0, label)
                
                remove_btn = ctk.CTkButton(
                    row,
                    text="✕",
                    width=30,
                    command=lambda: remove_option_row(row)
                )
                remove_btn.pack(side=tk.LEFT, padx=5)
                
                option_entries.append((row, value_entry, label_entry))
            
            def remove_option_row(row):
                for i, (r, _, _) in enumerate(option_entries):
                    if r == row:
                        option_entries.pop(i)
                        break
                row.destroy()
            
            # Add existing options if any
            if current_options and isinstance(current_options, dict) and "options" in current_options:
                for option in current_options["options"]:
                    add_option_row(option.get("value", ""), option.get("label", ""))
            
            if not option_entries:
                add_option_row()  # Add at least one empty row
            
            # Button to add more options
            add_btn = ctk.CTkButton(
                options_dialog,
                text="+ Add Option",
                command=lambda: add_option_row()
            )
            add_btn.pack(pady=10)
            
            # Save button
            def save_choice_options():
                options_list = []
                for _, value_entry, label_entry in option_entries:
                    value = value_entry.get().strip()
                    label = label_entry.get().strip()
                    
                    if value:
                        option = {"value": value}
                        if label:
                            option["label"] = label
                        options_list.append(option)
                
                # Find this field in custom_field_entries and update its options
                for field in self.custom_field_entries:
                    if field["options_btn"].winfo_toplevel() == options_dialog.master:
                        field["options"] = {"options": options_list}
                        break
                
                options_dialog.destroy()
            
            save_btn = ctk.CTkButton(
                options_dialog,
                text="Save Options",
                command=save_choice_options
            )
            save_btn.pack(pady=10)
            
        elif field_type == "rating":
            # Rating field options
            ctk.CTkLabel(
                options_dialog,
                text="Configure Rating",
                font=ctk.CTkFont(size=16, weight="bold")
            ).pack(pady=(20, 10))
            
            options_frame = ctk.CTkFrame(options_dialog)
            options_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Max rating value
            max_label = ctk.CTkLabel(options_frame, text="Maximum Rating:", width=150)
            max_label.pack(side=tk.LEFT, padx=5)
            
            max_var = tk.StringVar(value="5")
            if current_options and "max" in current_options:
                max_var.set(str(current_options["max"]))
                
            max_values = [str(i) for i in range(1, 11)]
            max_dropdown = ctk.CTkComboBox(
                options_frame,
                values=max_values,
                variable=max_var,
                width=100
            )
            max_dropdown.pack(side=tk.LEFT, padx=5)
            
            # Save button
            def save_rating_options():
                try:
                    max_value = int(max_var.get())
                    
                    # Find this field in custom_field_entries and update its options
                    for field in self.custom_field_entries:
                        if field["options_btn"].winfo_toplevel() == options_dialog.master:
                            field["options"] = {"max": max_value}
                            break
                    
                    options_dialog.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Maximum rating must be a number")
            
            save_btn = ctk.CTkButton(
                options_dialog,
                text="Save Options",
                command=save_rating_options
            )
            save_btn.pack(pady=10)
            
        elif field_type == "color":
            # Color field options
            ctk.CTkLabel(
                options_dialog,
                text="Configure Color Field",
                font=ctk.CTkFont(size=16, weight="bold")
            ).pack(pady=(20, 10))
            
            options_frame = ctk.CTkFrame(options_dialog)
            options_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Allow custom colors
            custom_var = tk.BooleanVar(value=True)
            if current_options and "allow_custom" in current_options:
                custom_var.set(current_options["allow_custom"])
                
            custom_check = ctk.CTkCheckBox(
                options_frame,
                text="Allow custom colors",
                variable=custom_var
            )
            custom_check.pack(anchor="w", padx=5, pady=5)
            
            # Predefined colors
            ctk.CTkLabel(
                options_dialog,
                text="Predefined Colors (one per line):",
                anchor="w"
            ).pack(anchor="w", padx=20, pady=(10, 5))
            
            colors_text = ctk.CTkTextbox(options_dialog, width=400, height=200)
            colors_text.pack(padx=20, pady=5)
            
            # Insert existing colors if any
            if current_options and "colors" in current_options:
                colors_text.insert("1.0", "\n".join(current_options["colors"]))
            
            # Save button
            def save_color_options():
                colors = [line.strip() for line in colors_text.get("1.0", "end").split("\n") if line.strip()]
                
                # Find this field in custom_field_entries and update its options
                for field in self.custom_field_entries:
                    if field["options_btn"].winfo_toplevel() == options_dialog.master:
                        field["options"] = {
                            "allow_custom": custom_var.get(),
                            "colors": colors
                        }
                        break
                
                options_dialog.destroy()
            
            save_btn = ctk.CTkButton(
                options_dialog,
                text="Save Options",
                command=save_color_options
            )
            save_btn.pack(pady=10)
        
    def remove_field_row(self, row_frame):
        """Remove a custom field row"""
        for i, field in enumerate(self.custom_field_entries):
            if field["frame"] == row_frame:
                self.custom_field_entries.pop(i)
                break
        row_frame.destroy()

    def add_tier_row(self, tier_name=""):
        """Add a row for a tier"""
        row_frame = ctk.CTkFrame(self.tiers_scroll)
        row_frame.pack(fill=tk.X, pady=2)
        
        # Entry for tier name
        entry = ctk.CTkEntry(row_frame, width=250, placeholder_text="Tier Name")
        entry.pack(side=tk.LEFT, padx=5)
        if tier_name:
            entry.insert(0, tier_name)
        
        # Up button
        up_btn = ctk.CTkButton(
            row_frame,
            text="↑",
            width=30,
            command=lambda: self.move_tier_up(row_frame)
        )
        up_btn.pack(side=tk.LEFT, padx=2)
        
        # Down button
        down_btn = ctk.CTkButton(
            row_frame,
            text="↓",
            width=30,
            command=lambda: self.move_tier_down(row_frame)
        )
        down_btn.pack(side=tk.LEFT, padx=2)
        
        # Remove button
        remove_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            command=lambda: self.remove_tier_row(row_frame)
        )
        remove_btn.pack(side=tk.LEFT, padx=2)
        
        # Store the row data
        self.tier_entries.append((entry, row_frame))
        
    def move_tier_up(self, row_frame):
        """Move a tier entry up in the list"""
        for i, (_, frame) in enumerate(self.tier_entries):
            if frame == row_frame and i > 0:
                # Swap with the entry above
                self.tier_entries[i], self.tier_entries[i - 1] = self.tier_entries[i - 1], self.tier_entries[i]
                
                # Repack all frames to update the order
                for _, frame in self.tier_entries:
                    frame.pack_forget()
                
                for _, frame in self.tier_entries:
                    frame.pack(fill=tk.X, pady=2)
                
                break
    
    def move_tier_down(self, row_frame):
        """Move a tier entry down in the list"""
        for i, (_, frame) in enumerate(self.tier_entries):
            if frame == row_frame and i < len(self.tier_entries) - 1:
                # Swap with the entry below
                self.tier_entries[i], self.tier_entries[i + 1] = self.tier_entries[i + 1], self.tier_entries[i]
                
                # Repack all frames to update the order
                for _, frame in self.tier_entries:
                    frame.pack_forget()
                
                for _, frame in self.tier_entries:
                    frame.pack(fill=tk.X, pady=2)
                
                break
    
    def remove_tier_row(self, row_frame):
        """Remove a tier entry from the list"""
        for i, (_, frame) in enumerate(self.tier_entries):
            if frame == row_frame:
                # Remove from the list
                self.tier_entries.pop(i)
                break
        row_frame.destroy()
    
    def go_next(self):
        """Go to the next tab"""
        if self.current_tab_index == 0:
            # Validate type selection
            if not self.selected_type_var.get():
                messagebox.showerror("Error", "Please select a lifelist type")
                return
            
            self.selected_type_id = self.selected_type_var.get()
            # Get lifelist type data
            type_data = self.db.get_lifelist_type(self.selected_type_id)
            if not type_data:
                messagebox.showerror("Error", "Invalid lifelist type selected")
                return
                
            type_name = type_data[1]
            
            # Load default tiers and fields based on selected type
            self.load_default_type_settings(type_name)
            
        elif self.current_tab_index == 1:
            # Validate name
            if not self.name_entry.get().strip():
                messagebox.showerror("Error", "Please enter a lifelist name")
                return
                
        elif self.current_tab_index == 3:
            # Update the summary tab before showing it
            self.update_summary_tab()
        
        self.current_tab_index += 1
        if self.current_tab_index >= self.total_tabs:
            self.current_tab_index = self.total_tabs - 1
            
        # Update tab visibility
        self.show_current_tab()
        
    def go_previous(self):
        """Go to the previous tab"""
        self.current_tab_index -= 1
        self.current_tab_index = max(self.current_tab_index, 0)
        # Update tab visibility
        self.show_current_tab()
    
    def show_current_tab(self):
        """Show the current tab and update navigation buttons"""
        # Map index to tab name
        tab_names = ["1. Type", "2. Info", "3. Fields", "4. Tiers", "5. Summary"]
        self.tabview.set(tab_names[self.current_tab_index])
        
        # Update button states
        if self.current_tab_index == 0:
            self.prev_btn.configure(state="disabled")
        else:
            self.prev_btn.configure(state="normal")
            
        if self.current_tab_index == self.total_tabs - 1:
            # Last tab, show Finish button instead of Next
            self.next_btn.pack_forget()
            self.finish_btn.pack(side=tk.RIGHT, padx=5)
        else:
            # Not last tab, show Next button
            self.finish_btn.pack_forget()
            self.next_btn.pack(side=tk.RIGHT, padx=5)
            
    def load_default_type_settings(self, type_name):
        """Load default settings for the selected lifelist type"""
        # Clear existing fields and tiers
        for field in self.custom_field_entries:
            field["frame"].destroy()
        self.custom_field_entries = []
        
        for _, frame in self.tier_entries:
            frame.destroy()
        self.tier_entries = []
        
        # Update tab descriptions with appropriate terminology
        entry_term = self.config.get_entry_term(type_name)
        observation_term = self.config.get_observation_term(type_name)
        
        self.fields_desc_label.configure(
            text=f"Define custom fields to track additional information for each {entry_term}."
        )
        
        self.tiers_desc_label.configure(
            text=f"Define tiers to categorize your {observation_term}s."
        )
        
        # Load default custom fields
        default_fields = self.config.get_default_fields(type_name)
        for field in default_fields:
            self.add_custom_field_row(
                field.get("name", ""),
                field.get("type", "text"),
                bool(field.get("required", 0)),
                field.get("options")
            )
            
        # Load default tiers
        default_tiers = self.config.get_default_tiers(type_name)
        for tier in default_tiers:
            self.add_tier_row(tier)
            
    def update_summary_tab(self):
        """Update the summary tab with current settings"""
        # Clear existing content
        for widget in self.summary_scroll.winfo_children():
            widget.destroy()

        # Get lifelist type data
        type_data = self.db.get_lifelist_type(self.selected_type_id)
        if not type_data:
            return

        type_name = type_data[1]

        # Basic info section
        ctk.CTkLabel(
            self.summary_scroll,
            text="Basic Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        info_frame = ctk.CTkFrame(self.summary_scroll)
        info_frame.pack(fill=tk.X, pady=5)

        # Lifelist name
        ctk.CTkLabel(info_frame, text="Name:", width=150, anchor="w").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info_frame, text=self.name_entry.get().strip(), anchor="w").pack(anchor="w", padx=30, pady=2)

        # Lifelist type
        ctk.CTkLabel(info_frame, text="Type:", width=150, anchor="w").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info_frame, text=type_name, anchor="w").pack(anchor="w", padx=30, pady=2)

        # Description (if any)
        if description := self.desc_text.get("1.0", "end").strip():
            ctk.CTkLabel(info_frame, text="Description:", width=150, anchor="w").pack(anchor="w", padx=10, pady=2)
            ctk.CTkLabel(info_frame, text=description, wraplength=400, anchor="w").pack(anchor="w", padx=30, pady=2)

        # Classification (if any)
        if classification := self.class_entry.get().strip():
            ctk.CTkLabel(info_frame, text="Classification:", width=150, anchor="w").pack(anchor="w", padx=10, pady=2)
            ctk.CTkLabel(info_frame, text=classification, anchor="w").pack(anchor="w", padx=30, pady=2)

        # Custom fields section
        ctk.CTkLabel(
            self.summary_scroll,
            text="Custom Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(20, 5))

        if self.custom_field_entries:
            fields_frame = ctk.CTkFrame(self.summary_scroll)
            fields_frame.pack(fill=tk.X, pady=5)

            for i, field in enumerate(self.custom_field_entries):
                name = field["name"].get().strip()
                field_type = field["type"].get()
                required = "Yes" if field["required"].get() else "No"

                field_text = f"{i+1}. {name} (Type: {field_type}, Required: {required})"
                ctk.CTkLabel(fields_frame, text=field_text, anchor="w").pack(anchor="w", padx=10, pady=2)
        else:
            ctk.CTkLabel(
                self.summary_scroll, 
                text="No custom fields defined",
                anchor="w"
            ).pack(anchor="w", padx=10, pady=5)

        # Tiers section
        ctk.CTkLabel(
            self.summary_scroll,
            text="Observation Tiers",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(20, 5))

        if self.tier_entries:
            tiers_frame = ctk.CTkFrame(self.summary_scroll)
            tiers_frame.pack(fill=tk.X, pady=5)

            for i, (entry, _) in enumerate(self.tier_entries):
                if tier_name := entry.get().strip():
                    ctk.CTkLabel(tiers_frame, text=f"{i+1}. {tier_name}", anchor="w").pack(anchor="w", padx=10, pady=2)
        else:
            ctk.CTkLabel(
                self.summary_scroll, 
                text="No tiers defined",
                anchor="w"
            ).pack(anchor="w", padx=10, pady=5)
            
    def create_lifelist(self):
        """Create the lifelist with all configured settings"""
        # Validate required fields
        lifelist_name = self.name_entry.get().strip()
        if not lifelist_name:
            messagebox.showerror("Error", "Please enter a lifelist name")
            return
            
        if not self.selected_type_id:
            messagebox.showerror("Error", "Please select a lifelist type")
            return
            
        classification = self.class_entry.get().strip() or None
        
        try:
            # Get database connection
            db = DatabaseFactory.get_database()
            
            # Create the lifelist
            lifelist_id = db.create_lifelist(lifelist_name, self.selected_type_id, classification)
            
            if not lifelist_id:
                messagebox.showerror("Error", f"A lifelist named '{lifelist_name}' already exists")
                return
                
            # Add custom tiers if defined
            tiers = []
            for entry, _ in self.tier_entries:
                tier_name = entry.get().strip()
                if tier_name and tier_name not in tiers:
                    tiers.append(tier_name)
                    
            if tiers:
                db.set_lifelist_tiers(lifelist_id, tiers)
                
            # Add custom fields
            for field in self.custom_field_entries:
                field_name = field["name"].get().strip()
                field_type = field["type"].get()
                is_required = 1 if field["required"].get() else 0
                options = field.get("options")
                
                if field_name:
                    db.add_custom_field(
                        lifelist_id,
                        field_name,
                        field_type,
                        options,
                        is_required
                    )
                    
            # Close the dialog and call the callback function
            self.dialog.destroy()
            if self.callback:
                self.callback(lifelist_id)
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")