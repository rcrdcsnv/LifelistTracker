# services/database_service.py
"""
Database Service - Manages database connections and operations
"""
import sqlite3
from typing import List, Dict, Any, Callable


class IDatabaseService:
    """Interface for database service"""

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        pass

    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        pass

    def execute_scalar(self, query: str, params: tuple = ()) -> Any:
        pass

    def execute_transaction(self, operations_func: Callable) -> Any:
        pass

    def close(self) -> None:
        pass


class DatabaseService(IDatabaseService):
    """Service for database operations"""

    def __init__(self, db_path: str = "lifelists.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        # Create tables for lifelists
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS lifelists (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            taxonomy TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create tables for custom fields
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS custom_fields (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            field_name TEXT,
            field_type TEXT,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        # Create table for lifelist tiers
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS lifelist_tiers (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            tier_name TEXT,
            tier_order INTEGER,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE,
            UNIQUE (lifelist_id, tier_name)
        )
        ''')

        # Create table for observations
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            species_name TEXT,
            observation_date TIMESTAMP,
            location TEXT,
            latitude REAL,
            longitude REAL,
            tier TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        # Create table for observation custom fields
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS observation_custom_fields (
            id INTEGER PRIMARY KEY,
            observation_id INTEGER,
            field_id INTEGER,
            value TEXT,
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE,
            FOREIGN KEY (field_id) REFERENCES custom_fields (id) ON DELETE CASCADE
        )
        ''')

        # Create table for photos
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY,
            observation_id INTEGER,
            file_path TEXT,
            is_primary INTEGER DEFAULT 0,
            latitude REAL,
            longitude REAL,
            taken_date TIMESTAMP,
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE
        )
        ''')

        # Create tables for tags
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS observation_tags (
            observation_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (observation_id, tag_id),
            FOREIGN KEY (observation_id) REFERENCES observations (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
        ''')

        # Create tables for taxonomies
        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS taxonomies (
            id INTEGER PRIMARY KEY,
            lifelist_id INTEGER,
            name TEXT,
            version TEXT,
            source TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lifelist_id) REFERENCES lifelists (id) ON DELETE CASCADE
        )
        ''')

        self.execute_non_query('''
        CREATE TABLE IF NOT EXISTS taxonomy_entries (
            id INTEGER PRIMARY KEY,
            taxonomy_id INTEGER,
            scientific_name TEXT,
            common_name TEXT,
            family TEXT,
            genus TEXT,
            species TEXT,
            subspecies TEXT,
            order_name TEXT,
            class_name TEXT,
            code TEXT,
            rank TEXT,
            is_custom INTEGER DEFAULT 0,
            additional_data TEXT,
            FOREIGN KEY (taxonomy_id) REFERENCES taxonomies (id) ON DELETE CASCADE
        )
        ''')

        # Create indices for fast lookup
        self.execute_non_query(
            'CREATE INDEX IF NOT EXISTS idx_taxonomy_scientific ON taxonomy_entries (taxonomy_id, scientific_name)')
        self.execute_non_query(
            'CREATE INDEX IF NOT EXISTS idx_taxonomy_common ON taxonomy_entries (taxonomy_id, common_name)')
        self.execute_non_query(
            'CREATE INDEX IF NOT EXISTS idx_taxonomy_family ON taxonomy_entries (taxonomy_id, family)')

        self.conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a query that returns rows

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of dictionaries representing rows
        """
        try:
            if not self.conn or not self.cursor:
                self._connect()

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        """
        Execute a query that doesn't return rows (INSERT, UPDATE, DELETE)

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Number of rows affected or last row ID
        """
        try:
            if not self.conn or not self.cursor:
                self._connect()

            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return -1

    def execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a query that returns a single value

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            The first column of the first row
        """
        try:
            if not self.conn or not self.cursor:
                self._connect()

            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def execute_transaction(self, operations_func: Callable) -> Any:
        """
        Execute multiple SQL operations as a single transaction

        Args:
            operations_func: Function that contains database operations to execute

        Returns:
            The result of operations_func execution
        """
        try:
            if not self.conn:
                self._connect()

            self.conn.execute("BEGIN TRANSACTION")
            result = operations_func()
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            print(f"Transaction error: {e}")
            raise e

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None