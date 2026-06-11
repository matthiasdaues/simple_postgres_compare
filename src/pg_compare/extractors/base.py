"""Base class for metadata extractors."""

from abc import ABC, abstractmethod
from typing import Any
from ..connection import DatabaseConnection


class BaseExtractor(ABC):
    """Abstract base class for database metadata extractors."""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    @property
    @abstractmethod
    def object_type(self) -> str:
        """Return the type of database object this extractor handles."""
        pass
    
    @abstractmethod
    def extract(self) -> dict[str, Any]:
        """Extract metadata from the database."""
        pass
    
    def _execute(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as dictionaries."""
        return self.connection.execute_dict(query, params)
    
    def _execute_scalar(self, query: str, params: tuple = None) -> Any:
        """Execute a query and return a single value."""
        return self.connection.execute_one(query, params)
