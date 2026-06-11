"""Extractor for view and materialized view metadata."""

from typing import Any
from .base import BaseExtractor


class ViewExtractor(BaseExtractor):
    """Extract view and materialized view metadata."""
    
    @property
    def object_type(self) -> str:
        return "views"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all views and materialized views grouped by schema."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        # Regular views
        view_query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS view_name,
                r.rolname AS owner,
                'view' AS view_type,
                pg_get_viewdef(c.oid, true) AS definition,
                pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                CASE c.relkind
                    WHEN 'v' THEN false
                    ELSE true
                END AS is_materialized
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_roles r ON c.relowner = r.oid
            WHERE c.relkind = 'v'
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname
        """
        
        # Materialized views
        matview_query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS view_name,
                r.rolname AS owner,
                'materialized_view' AS view_type,
                pg_get_viewdef(c.oid, true) AS definition,
                pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                true AS is_materialized,
                c.relispopulated AS is_populated,
                (SELECT array_agg(attname ORDER BY attnum) 
                 FROM pg_attribute a 
                 WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped) AS columns
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_roles r ON c.relowner = r.oid
            WHERE c.relkind = 'm'
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname
        """
        
        params = tuple(schemas) if schemas else None
        views = {}
        
        # Process regular views
        for row in self._execute(view_query, params):
            schema_name = row['schema_name']
            view_name = row['view_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{view_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if schema_name not in views:
                views[schema_name] = {}
            
            views[schema_name][view_name] = {
                "type": "view",
                "owner": row['owner'],
                "definition_hash": self._hash_definition(row['definition']),
                "description": row['description'],
            }
        
        # Process materialized views
        for row in self._execute(matview_query, params):
            schema_name = row['schema_name']
            view_name = row['view_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{view_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if schema_name not in views:
                views[schema_name] = {}
            
            views[schema_name][view_name] = {
                "type": "materialized_view",
                "owner": row['owner'],
                "definition_hash": self._hash_definition(row['definition']),
                "description": row['description'],
                "columns": row.get('columns', []),
            }
        
        return views
    
    def _hash_definition(self, definition: str) -> str:
        """Create a hash of normalized view definition for comparison."""
        import hashlib
        if not definition:
            return ""
        # Normalize whitespace and create hash
        normalized = ' '.join(definition.split())
        return hashlib.md5(normalized.encode()).hexdigest()
