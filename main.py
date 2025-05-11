# main.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt

from config import Config
from db.base import DatabaseManager
from db.session_manager import SessionManager
from services.photo_manager import PhotoManager
from services.data_service import DataService
from ui.main_window import MainWindow

def main():
    # Set application info
    QCoreApplication.setApplicationName("Lifelist Tracker")
    QCoreApplication.setOrganizationName("Lifelist")

    # Create the application
    app = QApplication(sys.argv)

    # Load configuration
    config = Config.load()

    # Set up the themes
    app.setStyle("Fusion")

    if config.ui.theme == "Dark":
        from ui.styles.dark_theme import apply_dark_theme
        apply_dark_theme(app)
    elif config.ui.theme == "Light":
        from ui.styles.light_theme import apply_light_theme
        apply_light_theme(app)

    # Create storage directory
    storage_dir = Path("storage")
    storage_dir.mkdir(exist_ok=True)

    # Set up database
    db_path = config.database.path
    db_manager = DatabaseManager(db_path)
    db_manager.create_tables()

    # Create session manager
    session_manager = SessionManager(db_manager)

    # Create services
    photo_manager = PhotoManager(storage_dir)
    data_service = DataService(photo_manager)

    # Create main window with session manager
    window = MainWindow(config, db_manager, photo_manager, data_service, session_manager)
    window.show()

    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()