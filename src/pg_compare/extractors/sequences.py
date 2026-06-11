"""Extractor for sequence metadata."""

from typing import Any
from .base import BaseExtractor


class SequenceExtractor(BaseExtractor):
    """Extract sequence metadata."""
    
    @property
    def object_type(self) -> str:
        return "sequences"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all sequences grouped by schema."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND schemaname IN ({placeholders})"
        
        query = f"""
            SELECT 
                schemaname AS schema_name,
                sequencename AS sequence_name,
                sequenceowner AS owner,
                data_type,
                start_value,
                min_value,
                max_value,
                increment_by,
                cycle AS is_cycle,
                cache_size
            FROM pg_sequences
            WHERE schemaname NOT LIKE 'pg_%'
              AND schemaname != 'information_schema'
              {schema_filter}
            ORDER BY schemaname, sequencename
        """
        
        params = tuple(schemas) if schemas else None
        sequences = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            sequence_name = row['sequence_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{sequence_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if schema_name not in sequences:
                sequences[schema_name] = {}
            
            sequences[schema_name][sequence_name] = {
                "owner": row['owner'],
                "data_type": row['data_type'],
                "start_value": row['start_value'],
                "min_value": row['min_value'],
                "max_value": row['max_value'],
                "increment_by": row['increment_by'],
                "is_cycle": row['is_cycle'],
                "cache_size": row['cache_size'],
            }
        
        # Also get sequence ownership (which column owns the sequence)
        ownership_query = """
            SELECT 
                ns.nspname AS schema_name,
                s.relname AS sequence_name,
                nt.nspname AS table_schema,
                t.relname AS table_name,
                a.attname AS column_name
            FROM pg_class s
            JOIN pg_namespace ns ON s.relnamespace = ns.oid
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON d.refobjid = t.oid
            JOIN pg_namespace nt ON t.relnamespace = nt.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE s.relkind = 'S'
              AND d.deptype = 'a'
              AND ns.nspname NOT LIKE 'pg_%'
        """
        
        for row in self._execute(ownership_query):
            schema_name = row['schema_name']
            sequence_name = row['sequence_name']
            
            if schema_name in sequences and sequence_name in sequences[schema_name]:
                sequences[schema_name][sequence_name]['owned_by'] = {
                    "schema": row['table_schema'],
                    "table": row['table_name'],
                    "column": row['column_name'],
                }
        
        return sequences
