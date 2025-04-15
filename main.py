# main.py
"""
Lifelist Manager - A tool for tracking species observations
"""
import customtkinter as ctk
import atexit

from LifelistTracker.di_container import container
from LifelistTracker.views.app import LifelistApp
from LifelistTracker.services.database_service import IDatabaseService, DatabaseService
from LifelistTracker.services.app_state_service import IAppStateService, AppStateService
from LifelistTracker.services.lifelist_service import ILifelistService, LifelistService
from LifelistTracker.services.observation_service import IObservationService, ObservationService
from LifelistTracker.services.photo_service import IPhotoService, PhotoService
from LifelistTracker.services.config_service import IConfigService, ConfigService
from LifelistTracker.services.taxonomy_service import ITaxonomyService, TaxonomyService
from LifelistTracker.services.file_service import IFileService, FileService
from LifelistTracker.viewmodels.welcome_viewmodel import WelcomeViewModel
from LifelistTracker.viewmodels.lifelist_viewmodel import LifelistViewModel
from LifelistTracker.viewmodels.observation_viewmodel import ObservationViewModel
from LifelistTracker.viewmodels.observation_form_viewmodel import ObservationFormViewModel
from LifelistTracker.viewmodels.taxonomy_viewmodel import TaxonomyViewModel

def register_services():
    """Register all services with the dependency injection container"""
    # Register services
    # First register the FileService
    container.register(IFileService, FileService)

    # Then register ConfigService which depends on FileService
    container.register(IConfigService, ConfigService)

    # Get database path from config
    config_service = container.resolve(IConfigService)
    db_path = config_service.get_database_path()

    # Register database service with path from config
    database_service = DatabaseService(db_path)
    container.register(IDatabaseService, instance=database_service)

    # Register other services
    container.register(IAppStateService, AppStateService)
    container.register(ILifelistService, LifelistService)
    container.register(IObservationService, ObservationService)
    container.register(IPhotoService, PhotoService)
    container.register(ITaxonomyService, TaxonomyService)

    # Register ViewModels
    container.register(WelcomeViewModel)
    container.register(LifelistViewModel)
    container.register(ObservationViewModel)
    container.register(ObservationFormViewModel)
    container.register(TaxonomyViewModel)


def main():
    """Main application entry point"""
    # Register services
    register_services()

    # Get configuration service
    config_service = container.resolve(IConfigService)

    # Set appearance mode and default theme
    ctk.set_appearance_mode(config_service.get_theme())
    ctk.set_default_color_theme(config_service.get_color_theme())

    # Create the main window
    root = ctk.CTk()

    # Create the application
    app = LifelistApp(root)

    # Register cleanup function to close database connections
    database_service = container.resolve(IDatabaseService)
    atexit.register(database_service.close)

    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()