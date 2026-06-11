"""Extractor for role and user metadata."""

from typing import Any
from .base import BaseExtractor


class RoleExtractor(BaseExtractor):
    """Extract role and user metadata."""
    
    @property
    def object_type(self) -> str:
        return "roles"
    
    def extract(self, exclude_system: bool = True) -> dict[str, Any]:
        """Extract all roles and their properties."""
        query = """
            SELECT 
                r.rolname AS role_name,
                r.rolsuper AS is_superuser,
                r.rolinherit AS inherit_privileges,
                r.rolcreaterole AS can_create_roles,
                r.rolcreatedb AS can_create_db,
                r.rolcanlogin AS can_login,
                r.rolreplication AS is_replication_role,
                r.rolbypassrls AS bypass_rls,
                r.rolconnlimit AS connection_limit,
                r.rolvaliduntil AS valid_until,
                ARRAY(
                    SELECT b.rolname
                    FROM pg_auth_members m
                    JOIN pg_roles b ON m.roleid = b.oid
                    WHERE m.member = r.oid
                ) AS member_of,
                ARRAY(
                    SELECT b.rolname
                    FROM pg_auth_members m
                    JOIN pg_roles b ON m.member = b.oid
                    WHERE m.roleid = r.oid
                ) AS members
            FROM pg_roles r
            WHERE 1=1
        """
        
        if exclude_system:
            query += " AND r.rolname NOT LIKE 'pg_%'"
        
        query += " ORDER BY r.rolname"
        
        roles = {}
        for row in self._execute(query):
            role_name = row['role_name']
            
            roles[role_name] = {
                "is_superuser": row['is_superuser'],
                "inherit_privileges": row['inherit_privileges'],
                "can_create_roles": row['can_create_roles'],
                "can_create_db": row['can_create_db'],
                "can_login": row['can_login'],
                "is_replication_role": row['is_replication_role'],
                "bypass_rls": row['bypass_rls'],
                "connection_limit": row['connection_limit'],
                "member_of": sorted(row['member_of']) if row['member_of'] else [],
                "members": sorted(row['members']) if row['members'] else [],
            }
            
            # Only include valid_until if set
            if row['valid_until']:
                roles[role_name]['valid_until'] = str(row['valid_until'])
        
        return roles
