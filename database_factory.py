"""
DatabaseFactory - Factory for creating database connections
"""
from typing import Optional
from database import Database


class DatabaseFactory:
    """
    Factory class for creating and managing database connections
    """
    _instance = None
    _default_db_path = "lifelists.db"
    _default_instance = None

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(DatabaseFactory, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'DatabaseFactory':
        """
        Get the singleton instance of the DatabaseFactory

        Returns:
            DatabaseFactory: Singleton instance
        """
        if cls._instance is None:
            cls._instance = DatabaseFactory()
        return cls._instance

    @classmethod
    def get_database(cls, db_path: Optional[str] = None) -> Database:
        """
        Get a database connection

        Args:
            db_path: Optional path to the database file

        Returns:
            Database: Database connection
        """
        if db_path is None:
            db_path = cls._default_db_path

            # Create default instance if it doesn't exist
            if cls._default_instance is None:
                cls._default_instance = Database(db_path)
            return cls._default_instance
        else:
            return Database(db_path)

    @classmethod
    def close_all(cls) -> None:
        """Close all database connections"""
        if cls._default_instance is not None:
            cls._default_instance.close()
            cls._default_instance = None