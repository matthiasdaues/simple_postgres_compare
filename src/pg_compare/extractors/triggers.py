"""Extractor for trigger metadata."""

from typing import Any
from .base import BaseExtractor


class TriggerExtractor(BaseExtractor):
    """Extract trigger metadata."""
    
    @property
    def object_type(self) -> str:
        return "triggers"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all triggers grouped by schema.table."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS table_name,
                t.tgname AS trigger_name,
                CASE 
                    WHEN t.tgtype & 2 = 2 THEN 'before'
                    WHEN t.tgtype & 2 = 0 THEN 'after'
                    WHEN t.tgtype & 64 = 64 THEN 'instead of'
                END AS timing,
                CASE 
                    WHEN t.tgtype & 4 = 4 THEN true ELSE false 
                END AS on_insert,
                CASE 
                    WHEN t.tgtype & 8 = 8 THEN true ELSE false 
                END AS on_delete,
                CASE 
                    WHEN t.tgtype & 16 = 16 THEN true ELSE false 
                END AS on_update,
                CASE 
                    WHEN t.tgtype & 32 = 32 THEN true ELSE false 
                END AS on_truncate,
                CASE 
                    WHEN t.tgtype & 1 = 1 THEN 'row'
                    ELSE 'statement'
                END AS orientation,
                pn.nspname AS function_schema,
                p.proname AS function_name,
                t.tgenabled AS is_enabled,
                pg_get_triggerdef(t.oid) AS definition,
                t.tgconstraint != 0 AS is_constraint_trigger,
                t.tgdeferrable AS is_deferrable,
                t.tginitdeferred AS is_deferred
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_proc p ON t.tgfoid = p.oid
            JOIN pg_namespace pn ON p.pronamespace = pn.oid
            WHERE NOT t.tgisinternal
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, c.relname, t.tgname
        """
        
        params = tuple(schemas) if schemas else None
        triggers = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            table_name = row['table_name']
            trigger_name = row['trigger_name']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{table_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            table_key = f"{schema_name}.{table_name}"
            if table_key not in triggers:
                triggers[table_key] = {}
            
            # Build events list
            events = []
            if row['on_insert']:
                events.append('INSERT')
            if row['on_update']:
                events.append('UPDATE')
            if row['on_delete']:
                events.append('DELETE')
            if row['on_truncate']:
                events.append('TRUNCATE')
            
            trigger_info = {
                "timing": row['timing'],
                "events": events,
                "orientation": row['orientation'],
                "function": f"{row['function_schema']}.{row['function_name']}",
                "is_enabled": row['is_enabled'] == 'O',  # 'O' = origin/enabled
            }
            
            if row['is_constraint_trigger']:
                trigger_info['is_constraint'] = True
                trigger_info['is_deferrable'] = row['is_deferrable']
                trigger_info['is_deferred'] = row['is_deferred']
            
            triggers[table_key][trigger_name] = trigger_info
        
        return triggers
