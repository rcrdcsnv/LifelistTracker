# views/utils.py
"""
UI utilities - Common UI functions and dialogs
"""
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from os import path
import re
from typing import Tuple, Callable, Optional

from LifelistTracker.services.lifelist_service import ILifelistService
from LifelistTracker.services.file_service import IFileService


def show_message(title: str, message: str, message_type: str = "info") -> None:
    """
    Show a message dialog with the given title and message

    Args:
        title: Dialog title
        message: Message to display
        message_type: Type of message - "info", "error", or "warning"
    """
    if message_type == "info":
        messagebox.showinfo(title, message)
    elif message_type == "error":
        messagebox.showerror(title, message)
    elif message_type == "warning":
        messagebox.showwarning(title, message)


def center_window(window) -> None:
    """
    Center a window on the screen

    Args:
        window: Window to center
    """
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_scrollable_container(parent) -> Tuple[tk.Canvas, ctk.CTkFrame]:
    """
    Create a scrollable container

    Args:
        parent: Parent widget

    Returns:
        tuple: (canvas, inner_frame) where inner_frame is the container to put content in
    """
    # Create a canvas with scrollbar
    canvas = tk.Canvas(parent, bg="#2b2b2b", highlightthickness=0)
    scrollbar = ctk.CTkScrollbar(parent, orientation="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create a frame inside the canvas
    inner_frame = ctk.CTkFrame(canvas)
    window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

    # Configure the scrolling
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def configure_window_size(event):
        canvas.itemconfig(window, width=event.width)

    inner_frame.bind("<Configure>", configure_scroll_region)
    canvas.bind("<Configure>", configure_window_size)

    return canvas, inner_frame


def create_labeled_entry(parent, label_text: str, width: int = 300, placeholder_text: str = "") -> Tuple[ctk.CTkFrame, ctk.CTkEntry]:
    """
    Create a labeled entry field

    Args:
        parent: Parent widget
        label_text: Label text
        width: Width of the entry field
        placeholder_text: Placeholder text for the entry

    Returns:
        tuple: (frame, entry) where entry is the CTkEntry widget
    """
    frame = ctk.CTkFrame(parent)
    frame.pack(fill=tk.X, pady=2)

    label = ctk.CTkLabel(frame, text=label_text, width=150)
    label.pack(side=tk.LEFT, padx=5)

    entry = ctk.CTkEntry(frame, width=width, placeholder_text=placeholder_text)
    entry.pack(side=tk.LEFT, padx=5)

    return frame, entry


def export_lifelist_dialog(root, lifelist_service: ILifelistService,
                          file_service: IFileService,
                          lifelist_id: int, lifelist_name: str) -> None:
    """
    Show dialog to export a lifelist

    Args:
        root: Root window
        lifelist_service: Service for lifelist operations
        file_service: Service for file operations
        lifelist_id: ID of the lifelist to export
        lifelist_name: Name of the lifelist
    """
    if not lifelist_id:
        show_message("Error", "No lifelist selected", "error")
        return

    # Ask for export location
    export_dir = filedialog.askdirectory(
        title=f"Select Export Location for '{lifelist_name}'"
    )

    if not export_dir:
        return

    # Create a directory for this export
    export_name = re.sub(r'[^\w\s-]', '', lifelist_name).strip().replace(' ', '_')
    export_path = path.join(export_dir, export_name)

    # Ensure directory exists
    file_service.ensure_directory(export_path)

    # Ask if photos should be included
    include_photos = messagebox.askyesno(
        "Export Photos?",
        "Would you like to include photos in the export? This may increase the export size significantly."
    )

    try:
        # Export the lifelist
        success = lifelist_service.export_lifelist(lifelist_id, export_path, include_photos)

        if success:
            show_message(
                "Export Successful",
                f"Lifelist '{lifelist_name}' has been exported to:\n{export_path}"
            )
        else:
            show_message("Export Error", f"Failed to export lifelist '{lifelist_name}'", "error")

    except Exception as e:
        show_message("Export Error", f"An error occurred: {str(e)}", "error")


def import_lifelist_dialog(root, lifelist_service: ILifelistService,
                          file_service: IFileService,
                          callback: Callable) -> None:
    """
    Show dialog to import a lifelist

    Args:
        root: Root window
        lifelist_service: Service for lifelist operations
        file_service: Service for file operations
        callback: Function to call after import
    """
    # Ask for JSON file
    json_file = filedialog.askopenfilename(
        title="Select Lifelist JSON File",
        filetypes=[("JSON files", "*.json")]
    )

    if not json_file:
        return

    # Check for photos directory
    photos_dir = None
    json_dir = path.dirname(json_file)
    potential_photos_dir = path.join(json_dir, "photos")

    if path.isdir(potential_photos_dir):
        include_photos = messagebox.askyesno(
            "Import Photos?",
            "A 'photos' directory was found. Would you like to include photos in the import?"
        )

        if include_photos:
            photos_dir = potential_photos_dir

    try:
        # Import the lifelist
        success, message = lifelist_service.import_lifelist(json_file, photos_dir)

        if success:
            show_message("Import Successful", message)
            # Refresh sidebar
            if callback:
                callback()
        else:
            show_message("Import Error", message, "error")

    except Exception as e:
        show_message("Import Error", f"An error occurred: {str(e)}", "error")


def create_action_button(parent, text: str, command: Callable, width: int = 70,
                        side=tk.LEFT, padx: int = 2) -> ctk.CTkButton:
    """
    Create a button for an action

    Args:
        parent: Parent widget
        text: Button text
        command: Function to call when button is clicked
        width: Button width
        side: Side to pack the button on
        padx: Horizontal padding

    Returns:
        CTkButton: The created button
    """
    button = ctk.CTkButton(
        parent,
        text=text,
        width=width,
        command=command
    )
    button.pack(side=side, padx=padx)
    return button


def create_tag_widget(parent, tag_name: str, remove_command: Optional[Callable] = None) -> ctk.CTkFrame:
    """
    Create a tag widget with optional remove button

    Args:
        parent: Parent widget
        tag_name: Name of the tag
        remove_command: Function to call when remove button is clicked

    Returns:
        CTkFrame: The tag frame
    """
    tag_frame = ctk.CTkFrame(parent)
    tag_frame.pack(side=tk.LEFT, padx=2, pady=2)

    tag_label = ctk.CTkLabel(tag_frame, text=tag_name, padx=5)
    tag_label.pack(side=tk.LEFT)

    if remove_command:
        remove_btn = ctk.CTkButton(
            tag_frame,
            text="✕",
            width=20,
            height=20,
            command=remove_command
        )
        remove_btn.pack(side=tk.LEFT)

    return tag_frame