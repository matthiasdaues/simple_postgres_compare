"""Extractor for constraint metadata."""

from typing import Any
from .base import BaseExtractor


class ConstraintExtractor(BaseExtractor):
    """Extract constraint metadata including PK, FK, CHECK, UNIQUE, EXCLUDE."""
    
    @property
    def object_type(self) -> str:
        return "constraints"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all constraints grouped by schema.table."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS table_name,
                con.conname AS constraint_name,
                CASE con.contype
                    WHEN 'p' THEN 'primary_key'
                    WHEN 'f' THEN 'foreign_key'
                    WHEN 'c' THEN 'check'
                    WHEN 'u' THEN 'unique'
                    WHEN 'x' THEN 'exclusion'
                    WHEN 't' THEN 'trigger'
                END AS constraint_type,
                pg_get_constraintdef(con.oid) AS definition,
                con.condeferrable AS is_deferrable,
                con.condeferred AS is_deferred,
                con.convalidated AS is_validated,
                -- For foreign keys
                fn.nspname AS fk_ref_schema,
                fc.relname AS fk_ref_table,
                ARRAY(
                    SELECT a.attname 
                    FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
                    ORDER BY k.ord
                ) AS columns,
                ARRAY(
                    SELECT a.attname 
                    FROM unnest(con.confkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a ON a.attrelid = fc.oid AND a.attnum = k.attnum
                    ORDER BY k.ord
                ) AS fk_columns,
                CASE con.confupdtype
                    WHEN 'a' THEN 'no action'
                    WHEN 'r' THEN 'restrict'
                    WHEN 'c' THEN 'cascade'
                    WHEN 'n' THEN 'set null'
                    WHEN 'd' THEN 'set default'
                END AS fk_on_update,
                CASE con.confdeltype
                    WHEN 'a' THEN 'no action'
                    WHEN 'r' THEN 'restrict'
                    WHEN 'c' THEN 'cascade'
                    WHEN 'n' THEN 'set null'
                    WHEN 'd' THEN 'set default'
                END AS fk_on_delete
            FROM pg_constraint con
            JOIN pg_class c ON con.conrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            LEFT JOIN pg_class fc ON con.confrelid = fc.oid
            LEFT JOIN pg_namespace fn ON fc.relnamespace = fn.oid
            WHERE n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname, con.conname
        """
        
        params = tuple(schemas) if schemas else None
        constraints = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            table_name = row['table_name']
            constraint_name = row['constraint_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{table_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            table_key = f"{schema_name}.{table_name}"
            if table_key not in constraints:
                constraints[table_key] = {}
            
            constraint_info = {
                "type": row['constraint_type'],
                "columns": row['columns'],
                "is_deferrable": row['is_deferrable'],
                "is_deferred": row['is_deferred'],
                "is_validated": row['is_validated'],
            }
            
            # Add FK-specific info
            if row['constraint_type'] == 'foreign_key':
                constraint_info['references'] = {
                    "schema": row['fk_ref_schema'],
                    "table": row['fk_ref_table'],
                    "columns": row['fk_columns'],
                }
                constraint_info['on_update'] = row['fk_on_update']
                constraint_info['on_delete'] = row['fk_on_delete']
            
            # Add check constraint definition
            if row['constraint_type'] == 'check':
                constraint_info['definition'] = row['definition']
            
            constraints[table_key][constraint_name] = constraint_info
        
        return constraints
