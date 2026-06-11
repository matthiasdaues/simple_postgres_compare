"""Extractor for extension metadata."""

from typing import Any
from .base import BaseExtractor


class ExtensionExtractor(BaseExtractor):
    """Extract installed extension metadata."""
    
    @property
    def object_type(self) -> str:
        return "extensions"
    
    def extract(self) -> dict[str, Any]:
        """Extract all installed extensions."""
        query = """
            SELECT 
                e.extname AS extension_name,
                e.extversion AS version,
                n.nspname AS schema_name,
                r.rolname AS owner,
                e.extrelocatable AS is_relocatable,
                pg_catalog.obj_description(e.oid, 'pg_extension') AS description
            FROM pg_extension e
            JOIN pg_namespace n ON e.extnamespace = n.oid
            JOIN pg_roles r ON e.extowner = r.oid
            ORDER BY e.extname
        """
        
        extensions = {}
        for row in self._execute(query):
            ext_name = row['extension_name']
            
            extensions[ext_name] = {
                "version": row['version'],
                "schema": row['schema_name'],
                "owner": row['owner'],
                "is_relocatable": row['is_relocatable'],
                "description": row['description'],
            }
        
        return extensions
