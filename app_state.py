"""
AppState - Manages application state and provides centralized access to state data
"""
from typing import Optional, Callable


class AppState:
    """
    Manages application state and provides methods for state access and modification
    """

    def __init__(self, db):
        """
        Initialize the application state

        Args:
            db: Database connection
        """
        self.db = db
        self.current_lifelist_id = None
        self.current_observation_id = None
        self._on_state_change_callbacks = []

    def get_current_lifelist_id(self) -> Optional[int]:
        """Get the current lifelist ID"""
        return self.current_lifelist_id

    def get_current_observation_id(self) -> Optional[int]:
        """Get the current observation ID"""
        return self.current_observation_id

    def get_lifelist_name(self) -> str:
        """Get the name of the current lifelist"""
        if not self.current_lifelist_id:
            return ""

        with self.db as db:
            db.cursor.execute("SELECT name FROM lifelists WHERE id = ?", (self.current_lifelist_id,))
            result = db.cursor.fetchone()

            if result:
                return result[0]
        return ""

    def set_current_lifelist(self, lifelist_id: Optional[int]) -> None:
        """
        Set the current lifelist ID

        Args:
            lifelist_id: ID of the lifelist to set as current
        """
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None
        self._notify_state_change()

    def set_current_observation(self, observation_id: Optional[int]) -> None:
        """
        Set the current observation ID

        Args:
            observation_id: ID of the observation to set as current
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