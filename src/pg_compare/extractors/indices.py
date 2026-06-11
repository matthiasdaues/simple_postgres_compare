"""Extractor for index metadata."""

from typing import Any
from .base import BaseExtractor


class IndexExtractor(BaseExtractor):
    """Extract index metadata for all tables."""
    
    @property
    def object_type(self) -> str:
        return "indices"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all indices grouped by schema.table."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                t.relname AS table_name,
                i.relname AS index_name,
                am.amname AS index_type,
                ix.indisunique AS is_unique,
                ix.indisprimary AS is_primary,
                ix.indisclustered AS is_clustered,
                ix.indisvalid AS is_valid,
                pg_get_indexdef(ix.indexrelid) AS index_definition,
                ARRAY(
                    SELECT a.attname
                    FROM unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
                    ORDER BY k.ord
                ) AS columns,
                ix.indexprs IS NOT NULL AS has_expressions,
                ix.indpred IS NOT NULL AS is_partial,
                pg_get_expr(ix.indpred, ix.indrelid) AS predicate,
                pg_catalog.obj_description(i.oid, 'pg_class') AS description
            FROM pg_index ix
            JOIN pg_class i ON ix.indexrelid = i.oid
            JOIN pg_class t ON ix.indrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            JOIN pg_am am ON i.relam = am.oid
            WHERE n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, t.relname, i.relname
        """
        
        params = tuple(schemas) if schemas else None
        indices = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            table_name = row['table_name']
            index_name = row['index_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{table_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            table_key = f"{schema_name}.{table_name}"
            if table_key not in indices:
                indices[table_key] = {}
            
            index_info = {
                "index_type": row['index_type'],
                "is_unique": row['is_unique'],
                "is_primary": row['is_primary'],
                "columns": row['columns'],
                "is_valid": row['is_valid'],
                "description": row['description'],
            }
            
            # Add partial index predicate if applicable
            if row['is_partial']:
                index_info['is_partial'] = True
                index_info['predicate'] = row['predicate']
            
            # Add expression index flag
            if row['has_expressions']:
                index_info['has_expressions'] = True
                # Store normalized definition for expression indexes
                index_info['definition'] = row['index_definition']
            
            if row['is_clustered']:
                index_info['is_clustered'] = True
            
            indices[table_key][index_name] = index_info
        
        return indices
