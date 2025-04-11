"""
Lifelist Manager - A tool for tracking species observations
"""
import os
import tkinter as tk
import customtkinter as ctk
from ui.app import LifelistApp

def main():
    # Set appearance mode and default theme
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Create the main window
    root = ctk.CTk()
    app = LifelistApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()