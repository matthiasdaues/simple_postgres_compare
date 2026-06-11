"""Extractor for function and procedure metadata."""

from typing import Any
from .base import BaseExtractor


class FunctionExtractor(BaseExtractor):
    """Extract function and procedure metadata."""
    
    @property
    def object_type(self) -> str:
        return "functions"
    
    def extract(self, schemas: list[str] = None, exclude_patterns: list[str] = None) -> dict[str, Any]:
        """Extract all functions and procedures grouped by schema."""
        exclude_patterns = exclude_patterns or []
        
        schema_filter = ""
        if schemas:
            placeholders = ",".join(["%s"] * len(schemas))
            schema_filter = f"AND n.nspname IN ({placeholders})"
        
        query = f"""
            SELECT 
                n.nspname AS schema_name,
                p.proname AS function_name,
                r.rolname AS owner,
                CASE p.prokind
                    WHEN 'f' THEN 'function'
                    WHEN 'p' THEN 'procedure'
                    WHEN 'a' THEN 'aggregate'
                    WHEN 'w' THEN 'window'
                END AS kind,
                l.lanname AS language,
                pg_get_function_arguments(p.oid) AS arguments,
                pg_get_function_result(p.oid) AS return_type,
                CASE p.provolatile
                    WHEN 'i' THEN 'immutable'
                    WHEN 's' THEN 'stable'
                    WHEN 'v' THEN 'volatile'
                END AS volatility,
                CASE p.proparallel
                    WHEN 's' THEN 'safe'
                    WHEN 'r' THEN 'restricted'
                    WHEN 'u' THEN 'unsafe'
                END AS parallel_safety,
                p.proisstrict AS is_strict,
                p.prosecdef AS security_definer,
                p.proleakproof AS is_leakproof,
                p.procost AS estimated_cost,
                p.prorows AS estimated_rows,
                p.prosrc AS source_code,
                pg_get_functiondef(p.oid) AS full_definition
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            JOIN pg_roles r ON p.proowner = r.oid
            JOIN pg_language l ON p.prolang = l.oid
            WHERE n.nspname NOT LIKE 'pg_%'
              AND n.nspname != 'information_schema'
              {schema_filter}
            ORDER BY n.nspname, p.proname, pg_get_function_arguments(p.oid)
        """
        
        params = tuple(schemas) if schemas else None
        functions = {}
        
        for row in self._execute(query, params):
            schema_name = row['schema_name']
            function_name = row['function_name']
            arguments = row['arguments']
            
            # Skip excluded patterns
            full_name = f"{schema_name}.{function_name}"
            if any(pattern in full_name for pattern in exclude_patterns):
                continue
            
            if schema_name not in functions:
                functions[schema_name] = {}
            
            # Use function_name(arguments) as key to handle overloaded functions
            func_key = f"{function_name}({arguments})" if arguments else function_name
            
            func_info = {
                "name": function_name,
                "owner": row['owner'],
                "kind": row['kind'],
                "language": row['language'],
                "arguments": arguments,
                "return_type": row['return_type'],
                "volatility": row['volatility'],
                "parallel_safety": row['parallel_safety'],
                "is_strict": row['is_strict'],
                "security_definer": row['security_definer'],
                "is_leakproof": row['is_leakproof'],
            }
            
            # Store source for comparison (will be normalized later)
            if row['source_code']:
                func_info['source_hash'] = self._hash_source(row['source_code'])
            
            functions[schema_name][func_key] = func_info
        
        return functions
    
    def _hash_source(self, source: str) -> str:
        """Create a hash of normalized source code for comparison."""
        import hashlib
        # Normalize whitespace and create hash
        normalized = ' '.join(source.split())
        return hashlib.md5(normalized.encode()).hexdigest()
