"""Extractor for database-level metadata."""

from typing import Any
from .base import BaseExtractor


class DatabaseExtractor(BaseExtractor):
    """Extract database-level metadata including version and settings."""
    
    @property
    def object_type(self) -> str:
        return "database"
    
    def extract(self) -> dict[str, Any]:
        """Extract database metadata."""
        return {
            "name": self._get_database_name(),
            "version": self._get_version(),
            "encoding": self._get_encoding(),
            "collation": self._get_collation(),
            "ctype": self._get_ctype(),
        }
    
    def _get_database_name(self) -> str:
        return self._execute_scalar("SELECT current_database()")
    
    def _get_version(self) -> str:
        """Extract just the version number."""
        version = self._execute_scalar("SELECT version()")
        # Extract version like "15.4" from full string
        import re
        match = re.search(r'PostgreSQL (\d+\.\d+)', version)
        return match.group(1) if match else version
    
    def _get_encoding(self) -> str:
        return self._execute_scalar("""
            SELECT pg_encoding_to_char(encoding) 
            FROM pg_database 
            WHERE datname = current_database()
        """)
    
    def _get_collation(self) -> str:
        return self._execute_scalar("""
            SELECT datcollate 
            FROM pg_database 
            WHERE datname = current_database()
        """)
    
    def _get_ctype(self) -> str:
        return self._execute_scalar("""
            SELECT datctype 
            FROM pg_database 
            WHERE datname = current_database()
        """)
