"""Extractor for table metadata."""

from typing import Any
from .base import BaseExtractor


class TableExtractor(BaseExtractor):
    """Extract table metadata including table properties."""
    
    @property
    def object_type(self) -> str:
        return "tables"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all tables grouped by schema."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS table_name,
                r.rolname AS owner,
                c.relkind AS kind,
                CASE c.relpersistence
                    WHEN 'p' THEN 'permanent'
                    WHEN 't' THEN 'temporary'
                    WHEN 'u' THEN 'unlogged'
                END AS persistence,
                c.relispartition AS is_partition,
                pg_catalog.obj_description(c.oid, 'pg_class') AS description,
                CASE 
                    WHEN c.relispartition THEN pg_get_expr(c.relpartbound, c.oid)
                    ELSE NULL
                END AS partition_bound,
                CASE
                    WHEN p.partstrat IS NOT NULL THEN 
                        CASE p.partstrat
                            WHEN 'r' THEN 'range'
                            WHEN 'l' THEN 'list'
                            WHEN 'h' THEN 'hash'
                        END
                    ELSE NULL
                END AS partition_strategy,
                pg_get_partkeydef(c.oid) AS partition_key
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_roles r ON c.relowner = r.oid
            LEFT JOIN pg_partitioned_table p ON c.oid = p.partrelid
            WHERE c.relkind IN ('r', 'p')  -- regular tables and partitioned tables
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname
        """
        
        params = tuple(schemas) if schemas else None
        tables = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            table_name = row['table_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{table_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if schema_name not in tables:
                tables[schema_name] = {}
            
            table_info = {
                "owner": row['owner'],
                "kind": "table" if row['kind'] == 'r' else "partitioned_table",
                "persistence": row['persistence'],
                "description": row['description'],
            }
            
            # Add partition info if applicable
            if row['is_partition']:
                table_info['is_partition'] = True
                table_info['partition_bound'] = row['partition_bound']
            
            if row['partition_strategy']:
                table_info['partition_strategy'] = row['partition_strategy']
                table_info['partition_key'] = row['partition_key']
            
            tables[schema_name][table_name] = table_info
        
        return tables
