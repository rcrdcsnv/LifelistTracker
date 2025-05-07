"""
AppState - Manages application state and provides centralized access to state data
"""
from typing import Optional, Callable, Tuple

from database_factory import DatabaseFactory
from config_manager import ConfigManager


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
        self.current_lifelist_type = None
        self.config = ConfigManager.get_instance()
        self._on_state_change_callbacks = []

    def get_current_lifelist_id(self) -> Optional[int]:
        """Get the current lifelist ID"""
        return self.current_lifelist_id

    def get_current_observation_id(self) -> Optional[int]:
        """Get the current observation ID"""
        return self.current_observation_id
        
    def get_current_lifelist_type(self) -> Optional[str]:
        """Get the current lifelist type name"""
        return self.current_lifelist_type

    def get_lifelist_info(self) -> Tuple[str, str]:
        """
        Get the name and type of the current lifelist
        
        Returns:
            tuple: (lifelist_name, lifelist_type_name)
        """
        if not self.current_lifelist_id:
            return "", ""

        # Get database without context manager
        db = DatabaseFactory.get_database()
        db.cursor.execute("""
            SELECT l.name, t.name 
            FROM lifelists l
            LEFT JOIN lifelist_types t ON l.lifelist_type_id = t.id
            WHERE l.id = ?
        """, (self.current_lifelist_id,))
        result = db.cursor.fetchone()

        return result or ("", "")

    def get_lifelist_name(self) -> str:
        """Get the name of the current lifelist"""
        name, _ = self.get_lifelist_info()
        return name
        
    def get_entry_term(self) -> str:
        """
        Get the term used for entries in the current lifelist type
        
        Returns:
            str: The term (e.g., 'species', 'book', 'movie')
        """
        _, type_name = self.get_lifelist_info()
        return self.config.get_entry_term(type_name)
        
    def get_observation_term(self) -> str:
        """
        Get the term used for observations in the current lifelist type
        
        Returns:
            str: The term (e.g., 'sighting', 'reading', 'viewing')
        """
        _, type_name = self.get_lifelist_info()
        return self.config.get_observation_term(type_name)

    def set_current_lifelist(self, lifelist_id: Optional[int]) -> None:
        """
        Set the current lifelist ID and update the lifelist type

        Args:
            lifelist_id: ID of the lifelist to set as current
        """
        self.current_lifelist_id = lifelist_id
        self.current_observation_id = None

        # Update the current lifelist type
        if lifelist_id:
            db = DatabaseFactory.get_database()
            db.cursor.execute("""
                SELECT t.name 
                FROM lifelists l
                LEFT JOIN lifelist_types t ON l.lifelist_type_id = t.id
                WHERE l.id = ?
            """, (lifelist_id,))
            result = db.cursor.fetchone()

            self.current_lifelist_type = result[0] if result else None
        else:
            self.current_lifelist_type = None

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