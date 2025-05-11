from contextlib import contextmanager
from typing import TypeVar
from .base import DatabaseManager

T = TypeVar('T')


class SessionManager:
    """Advanced session management for different use cases"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._view_sessions = {}  # view_id -> session

    @contextmanager
    def list_session(self):
        """Short-lived session for list operations"""
        session = self.db_manager.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @contextmanager
    def detail_session(self, view_id: str):
        """Long-lived session for detail views"""
        # Reuse existing session if available
        if view_id in self._view_sessions:
            yield self._view_sessions[view_id]
            return

        # Create new session for view
        session = self.db_manager.Session()
        self._view_sessions[view_id] = session

        try:
            yield session
        except Exception as e:
            session.rollback()
            raise e
        # Note: Don't close - keep alive for view

    def close_view_session(self, view_id: str):
        """Explicitly close a view session"""
        if view_id in self._view_sessions:
            session = self._view_sessions.pop(view_id)
            session.close()

    @contextmanager
    def chunked_operation(self, chunk_size: int = 1000):
        """Session for chunked operations with periodic cleanup"""
        session = self.db_manager.Session()
        try:
            chunk_count = 0
            yield session

            # Periodic cleanup
            if chunk_count % chunk_size == 0:
                session.commit()
                session.expire_all()

            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()