# services/app_state_service.py
"""
AppState Service - Manages application state
"""
from typing import Optional, Callable, List
from LifelistTracker.services.database_service import IDatabaseService

class IAppStateService:
    """Interface for application state service"""

    def get_current_lifelist_id(self) -> Optional[int]:
        pass

    def get_current_observation_id(self) -> Optional[int]:
        pass

    def get_lifelist_name(self) -> str:
        pass

    def set_current_lifelist(self, lifelist_id: Optional[int]) -> None:
        pass

    def set_current_observation(self, observation_id: Optional[int]) -> None:
        pass

    def register_state_change_callback(self, callback: Callable) -> None:
        pass

    def unregister_state_change_callback(self, callback: Callable) -> None:
        pass


class AppStateService(IAppStateService):
    """Service for managing application state"""

    def __init__(self, database_service: IDatabaseService):
        """
        Initialize the application state service

        Args:
            database_service: Database service for querying lifelist data
        """
        self.db = database_service
        self.current_lifelist_id: Optional[int] = None
        self.current_observation_id: Optional[int] = None
        self._on_state_change_callbacks: List[Callable] = []

    def get_current_lifelist_id(self) -> Optional[int]:
        """
        Get the current lifelist ID

        Returns:
            The current lifelist ID, or None if no lifelist is selected
        """
        return self.current_lifelist_id

    def get_current_observation_id(self) -> Optional[int]:
        """
        Get the current observation ID

        Returns:
            The current observation ID, or None if no observation is selected
        """
        return self.current_observation_id

    def get_lifelist_name(self) -> str:
        """
        Get the name of the current lifelist

        Returns:
            The name of the current lifelist, or an empty string if none selected
        """
        if not self.current_lifelist_id:
            return ""

        query = "SELECT name FROM lifelists WHERE id = ?"
        result = self.db.execute_query(query, (self.current_lifelist_id,))

        if result:
            return result[0]["name"]
        return ""

    def set_current_lifelist(self, lifelist_id: Optional[int]) -> None:
        """
        Set the current lifelist ID

        Args:
            lifelist_id: ID of the lifelist to set as current, or None to clear
        """
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None
        self._notify_state_change()

    def set_current_observation(self, observation_id: Optional[int]) -> None:
        """
        Set the current observation ID

        Args:
            observation_id: ID of the observation to set as current, or None to clear
        """
        self.current_observation_id = observation_id
        self._notify_state_change()

    def register_state_change_callback(self, callback: Callable) -> None:
        """
        Register a callback function to be called when state changes

        Args:
            callback: Function to call on state change
        """
        if callback not in self._on_state_change_callbacks:
            self._on_state_change_callbacks.append(callback)

    def unregister_state_change_callback(self, callback: Callable) -> None:
        """
        Unregister a previously registered callback function

        Args:
            callback: Function to remove from callback list
        """
        if callback in self._on_state_change_callbacks:
            self._on_state_change_callbacks.remove(callback)

    def _notify_state_change(self) -> None:
        """Notify all registered callbacks of a state change"""
        for callback in self._on_state_change_callbacks:
            callback()