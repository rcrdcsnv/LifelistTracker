# navigation_controller.py
"""
NavigationController - Handles view transitions and UI component coordination
"""
import tkinter as tk
from typing import Optional, Type

from LifelistTracker.services.app_state_service import IAppStateService


class NavigationController:
    """
    Controls navigation between different views in the application
    """

    def __init__(self, content_frame: tk.Widget, app_state_service: IAppStateService):
        """
        Initialize the navigation controller

        Args:
            content_frame: The frame where views will be displayed
            app_state_service: The application state service
        """
        self.content_frame = content_frame
        self.app_state = app_state_service
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

    def show_view(self, view_name: str, **kwargs) -> None:
        """
        Show a specific view

        Args:
            view_name: Name of the view to show
            **kwargs: Arguments to pass to the view's show method
        """
        if view_name not in self.views:
            raise ValueError(f"View '{view_name}' is not registered")

        # Clear the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Get or create the view instance
        view_info = self.views[view_name]
        if view_info['instance'] is None:
            # Create instance with appropriate dependencies
            view_kwargs = view_info['kwargs'].copy() if 'kwargs' in view_info else {}

            # We no longer pass database directly to views
            # Instead, relevant viewmodels are passed in kwargs
            view_instance = view_info['class'](**view_kwargs)

            view_info['instance'] = view_instance

        # Show the view
        view_instance = view_info['instance']
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
                              species_name: Optional[str] = None) -> None:
        """
        Show the observation form for adding or editing an observation

        Args:
            lifelist_id: ID of the lifelist (defaults to current)
            observation_id: ID of the observation to edit (None for new)
            species_name: Optional species name to pre-fill
        """
        if lifelist_id is None:
            lifelist_id = self.app_state.get_current_lifelist_id()

        if observation_id is not None:
            self.app_state.set_current_observation(observation_id)

        self.show_view('observation_form', lifelist_id=lifelist_id,
                       observation_id=observation_id, species_name=species_name)

    def show_taxonomy_manager(self):
        """Show the taxonomy manager dialog"""
        taxonomy_view = self.get_view('taxonomy_view')
        if taxonomy_view:
            taxonomy_view.show_dialog()

    def show_welcome(self) -> None:
        """Show the welcome screen"""
        self.app_state.set_current_lifelist(None)
        self.app_state.set_current_observation(None)
        self.show_view('welcome_view')