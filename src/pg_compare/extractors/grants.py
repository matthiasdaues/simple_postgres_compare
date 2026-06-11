"""Extractor for grant/permission metadata."""

from typing import Any
from .base import BaseExtractor


class GrantExtractor(BaseExtractor):
    """Extract grants and permissions metadata."""
    
    @property
    def object_type(self) -> str:
        return "grants"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all grants grouped by object type."""
        exclude_patterns = exclude_patterns or []
        
        grants = {
            "schemas": self._extract_schema_grants(schemas, exclude_patterns),
            "tables": self._extract_table_grants(schemas, exclude_patterns),
            "columns": self._extract_column_grants(schemas, exclude_patterns),
            "sequences": self._extract_sequence_grants(schemas, exclude_patterns),
            "functions": self._extract_function_grants(schemas, exclude_patterns),
        }
        
        return grants
    
    def _extract_schema_grants(self, schemas: list[str], exclude_patterns: list[str]) -> dict:
        """Extract schema-level grants."""
        query = """
            SELECT 
                n.nspname AS schema_name,
                r.rolname AS grantee,
                privilege_type,
                is_grantable
            FROM pg_namespace n
            CROSS JOIN LATERAL (
                SELECT 
                    grantee::regrole::text AS grantee_name,
                    privilege_type,
                    is_grantable::boolean
                FROM aclexplode(n.nspacl) AS acl
                JOIN pg_roles gr ON acl.grantee = gr.oid
            ) AS perms
            JOIN pg_roles r ON r.rolname = perms.grantee_name
            WHERE n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
            ORDER BY n.nspname, r.rolname, privilege_type
        """
        
        result = {}
        try:
            for row in self._execute(query):
                schema_name = row['schema_name']
                if any(pattern in schema_name for pattern in exclude_patterns):
                    continue
                
                if schema_name not in result:
                    result[schema_name] = []
                
                result[schema_name].append({
                    "grantee": row['grantee'],
                    "privilege": row['privilege_type'],
                    "is_grantable": row['is_grantable'],
                })
        except Exception:
            # Some versions might not support aclexplode properly
            pass
        
        return result
    
    def _extract_table_grants(self, schemas: list[str], exclude_patterns: list[str]) -> dict:
        """Extract table-level grants."""
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND table_schema IN ({placeholders})"
        
        query = f"""
            SELECT 
                table_schema,
                table_name,
                grantee,
                privilege_type,
                is_grantable
            FROM information_schema.table_privileges
            WHERE table_schema NOT LIKE 'pg_%'
              AND table_schema != 'information_schema'
              AND grantee NOT LIKE 'pg_%'
              {schema_filter}
            ORDER BY table_schema, table_name, grantee, privilege_type
        """
        
        params = tuple(schemas) if schemas else None
        result = {}
        
        for row in self._execute(query, params):
            full_name = f"{row['table_schema']}.{row['table_name']}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if full_name not in result:
                result[full_name] = []
            
            result[full_name].append({
                "grantee": row['grantee'],
                "privilege": row['privilege_type'],
                "is_grantable": row['is_grantable'] == 'YES',
            })
        
        return result
    
    def _extract_column_grants(self, schemas: list[str], exclude_patterns: list[str]) -> dict:
        """Extract column-level grants."""
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND table_schema IN ({placeholders})"
        
        query = f"""
            SELECT 
                table_schema,
                table_name,
                column_name,
                grantee,
                privilege_type,
                is_grantable
            FROM information_schema.column_privileges
            WHERE table_schema NOT LIKE 'pg_%'
              AND table_schema != 'information_schema'
              AND grantee NOT LIKE 'pg_%'
              {schema_filter}
            ORDER BY table_schema, table_name, column_name, grantee, privilege_type
        """
        
        params = tuple(schemas) if schemas else None
        result = {}
        
        for row in self._execute(query, params):
            full_name = f"{row['table_schema']}.{row['table_name']}.{row['column_name']}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if full_name not in result:
                result[full_name] = []
            
            result[full_name].append({
                "grantee": row['grantee'],
                "privilege": row['privilege_type'],
                "is_grantable": row['is_grantable'] == 'YES',
            })
        
        return result
    
    def _extract_sequence_grants(self, schemas: list[str], exclude_patterns: list[str]) -> dict:
        """Extract sequence-level grants."""
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                c.relname AS sequence_name,
                r.rolname AS grantee,
                CASE
                    WHEN has_sequence_privilege(r.oid, c.oid, 'USAGE') THEN 'USAGE'
                    WHEN has_sequence_privilege(r.oid, c.oid, 'SELECT') THEN 'SELECT'
                    WHEN has_sequence_privilege(r.oid, c.oid, 'UPDATE') THEN 'UPDATE'
                END AS privilege_type
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            CROSS JOIN pg_roles r
            WHERE c.relkind = 'S'
              AND n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              AND r.rolname NOT LIKE 'pg_%'
              AND (has_sequence_privilege(r.oid, c.oid, 'USAGE')
                OR has_sequence_privilege(r.oid, c.oid, 'SELECT')
                OR has_sequence_privilege(r.oid, c.oid, 'UPDATE'))
              {schema_filter}
            ORDER BY n.nspname, c.relname, r.rolname
        """
        
        params = tuple(schemas) if schemas else None
        result = {}
        
        try:
            for row in self._execute(query, params):
                full_name = f"{row['schema_name']}.{row['sequence_name']}"
                if any(pattern in full_name for pattern in exclude_patterns):
                    continue
                
                if full_name not in result:
                    result[full_name] = []
                
                if row['privilege_type']:
                    result[full_name].append({
                        "grantee": row['grantee'],
                        "privilege": row['privilege_type'],
                    })
        except Exception:
            pass
        
        return result
    
    def _extract_function_grants(self, schemas: list[str], exclude_patterns: list[str]) -> dict:
        """Extract function-level grants."""
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND routine_schema IN ({placeholders})"
        
        query = f"""
            SELECT 
                routine_schema,
                routine_name,
                grantee,
                privilege_type,
                is_grantable
            FROM information_schema.routine_privileges
            WHERE routine_schema NOT LIKE 'pg_%'
              AND routine_schema != 'information_schema'
              AND grantee NOT LIKE 'pg_%'
              {schema_filter}
            ORDER BY routine_schema, routine_name, grantee, privilege_type
        """
        
        params = tuple(schemas) if schemas else None
        result = {}
        
        for row in self._execute(query, params):
            full_name = f"{row['routine_schema']}.{row['routine_name']}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if full_name not in result:
                result[full_name] = []
            
            result[full_name].append({
                "grantee": row['grantee'],
                "privilege": row['privilege_type'],
                "is_grantable": row['is_grantable'] == 'YES',
            })
        
        return result
