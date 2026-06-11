"""Extractor for schema metadata."""

from typing import Any
from .base import BaseExtractor


class SchemaExtractor(BaseExtractor):
    """Extract schema metadata."""
    
    # System schemas to exclude from comparison
    SYSTEM_SCHEMAS = frozenset([
        'pg_catalog',
        'pg_toast', 
        'information_schema',
        'pg_temp_1',
        'pg_toast_temp_1',
    ])
    
    @property
    def object_type(self) -> str:
        return "schemas"
    
    def extract(self, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all non-system schemas with their properties."""
        exclude_patterns = exclude_patterns or []
        
        query = """
            SELECT 
                n.nspname AS schema_name,
                r.rolname AS owner,
                pg_catalog.obj_description(n.oid, 'pg_namespace') AS description
            FROM pg_namespace n
            JOIN pg_roles r ON n.nspowner = r.oid
            WHERE n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
            ORDER BY n.nspname
        """
        
        schemas = {}
        for row in self._execute(query):
            schema_name = row['schema_name']
            
            # Skip excluded patterns
            if any(pattern in schema_name for pattern in exclude_patterns):
                continue
                
            schemas[schema_name] = {
                "owner": row['owner'],
                "description": row['description'],
            }
        
        return schemas
