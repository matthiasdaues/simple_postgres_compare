"""Extractor for column metadata."""

from typing import Any
from .base import BaseExtractor


class ColumnExtractor(BaseExtractor):
    """Extract column metadata for all tables."""
    
    @property
    def object_type(self) -> str:
        return "columns"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all columns grouped by schema.table."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS table_name,
                a.attname AS column_name,
                a.attnum AS ordinal_position,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                a.attnotnull AS is_not_null,
                pg_get_expr(d.adbin, d.adrelid) AS column_default,
                a.attidentity AS identity_type,
                a.attgenerated AS generated_type,
                pg_catalog.col_description(c.oid, a.attnum) AS description,
                CASE
                    WHEN a.attidentity = 'a' THEN 'always'
                    WHEN a.attidentity = 'd' THEN 'by default'
                    ELSE NULL
                END AS identity_generation,
                CASE
                    WHEN a.attgenerated = 's' THEN 'stored'
                    ELSE NULL
                END AS generated_stored
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_attribute a ON c.oid = a.attrelid
            LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            WHERE c.relkind IN ('r', 'p')
              AND a.attnum > 0
              AND NOT a.attisdropped
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname, a.attnum
        """
        
        params = tuple(schemas) if schemas else None
        columns = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            table_name = row['table_name']
            column_name = row['column_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{table_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            table_key = f"{schema_name}.{table_name}"
            if table_key not in columns:
                columns[table_key] = {}
            
            column_info = {
                "ordinal_position": row['ordinal_position'],
                "data_type": row['data_type'],
                "is_nullable": not row['is_not_null'],
                "column_default": row['column_default'],
                "description": row['description'],
            }
            
            # Add identity info if applicable
            if row['identity_generation']:
                column_info['identity'] = row['identity_generation']
            
            # Add generated column info if applicable
            if row['generated_stored']:
                column_info['generated'] = row['generated_stored']
            
            columns[table_key][column_name] = column_info
        
        return columns
