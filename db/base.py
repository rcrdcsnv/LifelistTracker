# db/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from typing import Optional, Callable, TypeVar, Any

Base = declarative_base()

T = TypeVar('T')
R = TypeVar('R')


class DatabaseManager:
    """Manages database connections and sessions"""

    _instance = None

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize(db_path)
        elif db_path is not None:
            # Reinitialize with new path if specified
            cls._instance._initialize(db_path)
        return cls._instance

    def _initialize(self, db_path: Optional[str] = None):
        """Initialize engine and session factory"""
        db_path = db_path or 'lifelists.db'
        db_url = f"sqlite:///{db_path}"

        self.engine = create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def create_tables(self):
        """Create all defined tables"""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def execute_transaction(self, operation: Callable[[Any], R]) -> R:
        """Execute a function within a transaction"""
        with self.session_scope() as session:
            return operation(session)

    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance