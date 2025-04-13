"""
Lifelist Manager - A tool for tracking species observations
"""
import customtkinter as ctk
import atexit
from database_factory import DatabaseFactory
from ui.app import LifelistApp


def main():
    """Main application entry point"""
    # Set appearance mode and default theme
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Create the main window
    root = ctk.CTk()

    # Register cleanup function to close database connections
    atexit.register(DatabaseFactory.close_all)

    # Create the application
    app = LifelistApp(root)

    # Start the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()