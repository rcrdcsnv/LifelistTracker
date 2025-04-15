# viewmodels/welcome_viewmodel.py
"""
Welcome ViewModel - Provides data and commands for the Welcome View
"""
from typing import List, Callable
from LifelistTracker.models.lifelist import Lifelist
from LifelistTracker.services.lifelist_service import ILifelistService


class WelcomeViewModel:
    """ViewModel for the Welcome View"""

    def __init__(self, lifelist_service: ILifelistService):
        self.lifelist_service = lifelist_service
        self.recent_lifelists: List[Lifelist] = []
        self.on_state_changed: List[Callable] = []

    def load_recent_lifelists(self, max_count: int = 3) -> None:
        """
        Load the most recent lifelists

        Args:
            max_count: Maximum number of lifelists to load
        """
        lifelists = self.lifelist_service.get_all_lifelists()
        self.recent_lifelists = lifelists[:max_count]
        self._notify_state_changed()

    def register_state_change_callback(self, callback: Callable) -> None:
        """
        Register a callback for state changes

        Args:
            callback: Function to call on state change
        """
        if callback not in self.on_state_changed:
            self.on_state_changed.append(callback)

    def unregister_state_change_callback(self, callback: Callable) -> None:
        """
        Unregister a previously registered callback

        Args:
            callback: Function to remove from callback list
        """
        if callback in self.on_state_changed:
            self.on_state_changed.remove(callback)

    def _notify_state_changed(self) -> None:
        """Notify all registered callbacks of a state change"""
        for callback in self.on_state_changed:
            callback()