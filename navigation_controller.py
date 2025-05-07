"""
NavigationController - Handles view transitions and UI component coordination
"""
import tkinter as tk
from typing import Optional, Type, Callable


class NavigationController:
    """
    Controls navigation between different views in the application
    """

    def __init__(self, content_frame: tk.Widget, app_state, db):
        """
        Initialize the navigation controller

        Args:
            content_frame: The frame where views will be displayed
            app_state: The application state manager
            db: Database connection
        """
        self.content_frame = content_frame
        self.app_state = app_state
        self.db = db
        self.views = {}  # Will store view instances
        self.root = content_frame.winfo_toplevel()

        # Current view being displayed
        self.current_view = None

    def register_view(self, view_name: str, view_class: Type, **kwargs) -> None:
        """
        Register a view class with the navigation controller

        Args:
            view_name: Name identifier for the view
            view_class: The class of the view component
            **kwargs: Additional arguments to pass when instantiating the view
        """
        # We'll instantiate views lazily when they're first needed
        self.views[view_name] = {
            'class': view_class,
            'instance': None,
            'kwargs': kwargs
        }

    def _initialize_view_if_needed(self, view_name):
        """Initialize a view if it hasn't been initialized yet"""
        if view_name not in self.views:
            raise ValueError(f"View '{view_name}' is not registered")

        view_info = self.views[view_name]
        if view_info['instance'] is None:
            # Create instance with appropriate dependencies
            view_kwargs = view_info['kwargs'].copy() if 'kwargs' in view_info else {}
            view_kwargs.update({
                'controller': self,
                'app_state': self.app_state,
                'db': self.db,
                'content_frame': self.content_frame
            })
            view_info['instance'] = view_info['class'](**view_kwargs)

    def get_view(self, view_name):
        """Get a view instance, initializing it if necessary"""
        self._initialize_view_if_needed(view_name)
        return self.views[view_name]['instance']

    def show_view(self, view_name, **kwargs):
        """Show a specific view"""
        # Initialize the view if needed
        self._initialize_view_if_needed(view_name)

        # Clear the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Show the view
        view_instance = self.views[view_name]['instance']
        if hasattr(view_instance, 'show'):
            view_instance.show(**kwargs)

        self.current_view = view_name

    def open_lifelist(self, lifelist_id: int) -> None:
        """
        Open a lifelist

        Args:
            lifelist_id: ID of the lifelist to open
        """
        self.app_state.set_current_lifelist(lifelist_id)
        lifelist_name = self.app_state.get_lifelist_name()
        self.show_view('lifelist_view', lifelist_id=lifelist_id, lifelist_name=lifelist_name)

    def show_observation(self, observation_id: int) -> None:
        """
        Show an observation

        Args:
            observation_id: ID of the observation to show
        """
        self.app_state.set_current_observation(observation_id)
        self.show_view('observation_view', observation_id=observation_id)

    def show_observation_form(self, lifelist_id: Optional[int] = None,
                              observation_id: Optional[int] = None,
                              entry_name: Optional[str] = None) -> None:
        """
        Show the observation form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist (defaults to current)
            observation_id: ID of the observation to edit (None for new)
            entry_name: Optional entry name to pre-fill
        """
        if lifelist_id is None:
            lifelist_id = self.app_state.get_current_lifelist_id()

        if observation_id is not None:
            self.app_state.set_current_observation(observation_id)

        self.show_view('observation_form', lifelist_id=lifelist_id,
                       observation_id=observation_id, entry_name=entry_name)

    def show_classification_manager(self) -> None:
        """Show the classification manager dialog"""
        if hasattr(self, 'classification_manager'):
            self.classification_manager.show_dialog()

    def show_lifelist_wizard(self, callback: Optional[Callable] = None) -> None:
        """
        Show the lifelist creation wizard

        Args:
            callback: Optional callback function to call after lifelist creation
        """
        from ui.lifelist_wizard import LifelistWizard
        LifelistWizard(self.root, self, callback)

    def show_welcome(self) -> None:
        """Show the welcome screen"""
        self.app_state.set_current_lifelist(None)
        self.app_state.set_current_observation(None)
        self.show_view('welcome_view')