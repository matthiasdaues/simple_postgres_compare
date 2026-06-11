"""Database comparison engine."""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class DifferenceType(str, Enum):
    """Types of differences that can be detected."""
    ADDED = "added"          # Present in target, not in source
    REMOVED = "removed"      # Present in source, not in target
    MODIFIED = "modified"    # Different values between source and target


@dataclass
class Difference:
    """Represents a single difference between two databases."""
    object_type: str         # e.g., "table", "column", "index"
    path: str                # Full path to the object, e.g., "public.users.email"
    diff_type: DifferenceType
    source_value: Any = None
    target_value: Any = None
    details: dict = field(default_factory=dict)
    
    def __str__(self) -> str:
        if self.diff_type == DifferenceType.ADDED:
            return f"[+] {self.object_type}: {self.path}"
        elif self.diff_type == DifferenceType.REMOVED:
            return f"[-] {self.object_type}: {self.path}"
        else:
            return f"[~] {self.object_type}: {self.path}"


@dataclass
class ComparisonResult:
    """Result of comparing two databases."""
    source_name: str
    target_name: str
    differences: list[Difference] = field(default_factory=list)
    
    @property
    def has_differences(self) -> bool:
        return len(self.differences) > 0
    
    @property
    def added_count(self) -> int:
        return sum(1 for d in self.differences if d.diff_type == DifferenceType.ADDED)
    
    @property
    def removed_count(self) -> int:
        return sum(1 for d in self.differences if d.diff_type == DifferenceType.REMOVED)
    
    @property
    def modified_count(self) -> int:
        return sum(1 for d in self.differences if d.diff_type == DifferenceType.MODIFIED)
    
    def filter_by_type(self, object_type: str) -> list[Difference]:
        """Get differences for a specific object type."""
        return [d for d in self.differences if d.object_type == object_type]
    
    def filter_by_diff_type(self, diff_type: DifferenceType) -> list[Difference]:
        """Get differences of a specific type."""
        return [d for d in self.differences if d.diff_type == diff_type]
    
    def summary(self) -> dict:
        """Get a summary of differences by object type."""
        summary = {}
        for diff in self.differences:
            if diff.object_type not in summary:
                summary[diff.object_type] = {"added": 0, "removed": 0, "modified": 0}
            summary[diff.object_type][diff.diff_type.value] += 1
        return summary


@dataclass
class ComparisonConfig:
    """Configuration for database comparison."""
    # Keys to ignore during comparison
    ignore_keys: list[str] = field(default_factory=lambda: [
        "oid", "created_at", "updated_at", "xmin"
    ])
    # Whether to compare grants
    compare_grants: bool = True
    # Whether to compare roles
    compare_roles: bool = True
    # Whether to ignore owner differences
    ignore_owners: bool = False
    # Whether to ignore description differences
    ignore_descriptions: bool = False


class DatabaseComparator:
    """Compares metadata extracted from two PostgreSQL databases."""
    
    def __init__(self, config: Optional[ComparisonConfig] = None):
        self.config = config or ComparisonConfig()
    
    def compare(
        self, 
        source_metadata: dict[str, Any], 
        target_metadata: dict[str, Any],
        source_name: str = "source",
        target_name: str = "target"
    ) -> ComparisonResult:
        """
        Compare two sets of database metadata.
        
        Args:
            source_metadata: Metadata from the source database
            target_metadata: Metadata from the target database
            source_name: Name/label for the source database
            target_name: Name/label for the target database
            
        Returns:
            ComparisonResult containing all differences
        """
        result = ComparisonResult(source_name=source_name, target_name=target_name)
        
        # Compare each object type
        self._compare_database(source_metadata, target_metadata, result)
        self._compare_extensions(source_metadata, target_metadata, result)
        
        if self.config.compare_roles:
            self._compare_roles(source_metadata, target_metadata, result)
        
        self._compare_schemas(source_metadata, target_metadata, result)
        self._compare_tables(source_metadata, target_metadata, result)
        self._compare_columns(source_metadata, target_metadata, result)
        self._compare_indices(source_metadata, target_metadata, result)
        self._compare_constraints(source_metadata, target_metadata, result)
        self._compare_sequences(source_metadata, target_metadata, result)
        self._compare_functions(source_metadata, target_metadata, result)
        self._compare_triggers(source_metadata, target_metadata, result)
        self._compare_views(source_metadata, target_metadata, result)
        
        if self.config.compare_grants:
            self._compare_grants(source_metadata, target_metadata, result)
        
        return result
    
    def _compare_database(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare database-level settings."""
        src_db = source.get("database", {})
        tgt_db = target.get("database", {})
        
        for key in ["version", "encoding", "collation", "ctype"]:
            src_val = src_db.get(key)
            tgt_val = tgt_db.get(key)
            
            if src_val != tgt_val:
                result.differences.append(Difference(
                    object_type="database",
                    path=f"database.{key}",
                    diff_type=DifferenceType.MODIFIED,
                    source_value=src_val,
                    target_value=tgt_val,
                ))
    
    def _compare_extensions(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare installed extensions."""
        src_ext = source.get("extensions", {})
        tgt_ext = target.get("extensions", {})
        
        # Extensions only in source
        for ext_name in set(src_ext.keys()) - set(tgt_ext.keys()):
            result.differences.append(Difference(
                object_type="extension",
                path=ext_name,
                diff_type=DifferenceType.REMOVED,
                source_value=src_ext[ext_name],
            ))
        
        # Extensions only in target
        for ext_name in set(tgt_ext.keys()) - set(src_ext.keys()):
            result.differences.append(Difference(
                object_type="extension",
                path=ext_name,
                diff_type=DifferenceType.ADDED,
                target_value=tgt_ext[ext_name],
            ))
        
        # Extensions in both - compare versions
        for ext_name in set(src_ext.keys()) & set(tgt_ext.keys()):
            src_ver = src_ext[ext_name].get("version")
            tgt_ver = tgt_ext[ext_name].get("version")
            
            if src_ver != tgt_ver:
                result.differences.append(Difference(
                    object_type="extension",
                    path=ext_name,
                    diff_type=DifferenceType.MODIFIED,
                    source_value=src_ver,
                    target_value=tgt_ver,
                    details={"attribute": "version"},
                ))
    
    def _compare_roles(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare roles and users."""
        src_roles = source.get("roles", {})
        tgt_roles = target.get("roles", {})
        
        # Roles only in source
        for role_name in set(src_roles.keys()) - set(tgt_roles.keys()):
            result.differences.append(Difference(
                object_type="role",
                path=role_name,
                diff_type=DifferenceType.REMOVED,
                source_value=src_roles[role_name],
            ))
        
        # Roles only in target
        for role_name in set(tgt_roles.keys()) - set(src_roles.keys()):
            result.differences.append(Difference(
                object_type="role",
                path=role_name,
                diff_type=DifferenceType.ADDED,
                target_value=tgt_roles[role_name],
            ))
        
        # Roles in both - compare attributes
        for role_name in set(src_roles.keys()) & set(tgt_roles.keys()):
            self._compare_dicts(
                src_roles[role_name],
                tgt_roles[role_name],
                "role",
                role_name,
                result,
            )
    
    def _compare_schemas(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare schemas."""
        src_schemas = source.get("schemas", {})
        tgt_schemas = target.get("schemas", {})
        
        # Schemas only in source
        for schema_name in set(src_schemas.keys()) - set(tgt_schemas.keys()):
            result.differences.append(Difference(
                object_type="schema",
                path=schema_name,
                diff_type=DifferenceType.REMOVED,
                source_value=src_schemas[schema_name],
            ))
        
        # Schemas only in target
        for schema_name in set(tgt_schemas.keys()) - set(src_schemas.keys()):
            result.differences.append(Difference(
                object_type="schema",
                path=schema_name,
                diff_type=DifferenceType.ADDED,
                target_value=tgt_schemas[schema_name],
            ))
        
        # Schemas in both - compare attributes
        for schema_name in set(src_schemas.keys()) & set(tgt_schemas.keys()):
            self._compare_dicts(
                src_schemas[schema_name],
                tgt_schemas[schema_name],
                "schema",
                schema_name,
                result,
            )
    
    def _compare_tables(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare tables."""
        src_tables = source.get("tables", {})
        tgt_tables = target.get("tables", {})
        
        all_schemas = set(src_tables.keys()) | set(tgt_tables.keys())
        
        for schema in all_schemas:
            src_schema_tables = src_tables.get(schema, {})
            tgt_schema_tables = tgt_tables.get(schema, {})
            
            # Tables only in source
            for table_name in set(src_schema_tables.keys()) - set(tgt_schema_tables.keys()):
                result.differences.append(Difference(
                    object_type="table",
                    path=f"{schema}.{table_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_schema_tables[table_name],
                ))
            
            # Tables only in target
            for table_name in set(tgt_schema_tables.keys()) - set(src_schema_tables.keys()):
                result.differences.append(Difference(
                    object_type="table",
                    path=f"{schema}.{table_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_schema_tables[table_name],
                ))
            
            # Tables in both - compare attributes
            for table_name in set(src_schema_tables.keys()) & set(tgt_schema_tables.keys()):
                self._compare_dicts(
                    src_schema_tables[table_name],
                    tgt_schema_tables[table_name],
                    "table",
                    f"{schema}.{table_name}",
                    result,
                )
    
    def _compare_columns(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare columns."""
        src_columns = source.get("columns", {})
        tgt_columns = target.get("columns", {})
        
        all_tables = set(src_columns.keys()) | set(tgt_columns.keys())
        
        for table in all_tables:
            src_table_cols = src_columns.get(table, {})
            tgt_table_cols = tgt_columns.get(table, {})
            
            # Columns only in source
            for col_name in set(src_table_cols.keys()) - set(tgt_table_cols.keys()):
                result.differences.append(Difference(
                    object_type="column",
                    path=f"{table}.{col_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_table_cols[col_name],
                ))
            
            # Columns only in target
            for col_name in set(tgt_table_cols.keys()) - set(src_table_cols.keys()):
                result.differences.append(Difference(
                    object_type="column",
                    path=f"{table}.{col_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_table_cols[col_name],
                ))
            
            # Columns in both - compare attributes
            for col_name in set(src_table_cols.keys()) & set(tgt_table_cols.keys()):
                self._compare_dicts(
                    src_table_cols[col_name],
                    tgt_table_cols[col_name],
                    "column",
                    f"{table}.{col_name}",
                    result,
                )
    
    def _compare_indices(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare indices."""
        src_indices = source.get("indices", {})
        tgt_indices = target.get("indices", {})
        
        all_tables = set(src_indices.keys()) | set(tgt_indices.keys())
        
        for table in all_tables:
            src_table_idx = src_indices.get(table, {})
            tgt_table_idx = tgt_indices.get(table, {})
            
            # Indices only in source
            for idx_name in set(src_table_idx.keys()) - set(tgt_table_idx.keys()):
                result.differences.append(Difference(
                    object_type="index",
                    path=f"{table}.{idx_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_table_idx[idx_name],
                ))
            
            # Indices only in target
            for idx_name in set(tgt_table_idx.keys()) - set(src_table_idx.keys()):
                result.differences.append(Difference(
                    object_type="index",
                    path=f"{table}.{idx_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_table_idx[idx_name],
                ))
            
            # Indices in both - compare attributes
            for idx_name in set(src_table_idx.keys()) & set(tgt_table_idx.keys()):
                self._compare_dicts(
                    src_table_idx[idx_name],
                    tgt_table_idx[idx_name],
                    "index",
                    f"{table}.{idx_name}",
                    result,
                )
    
    def _compare_constraints(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare constraints."""
        src_constraints = source.get("constraints", {})
        tgt_constraints = target.get("constraints", {})
        
        all_tables = set(src_constraints.keys()) | set(tgt_constraints.keys())
        
        for table in all_tables:
            src_table_con = src_constraints.get(table, {})
            tgt_table_con = tgt_constraints.get(table, {})
            
            # Constraints only in source
            for con_name in set(src_table_con.keys()) - set(tgt_table_con.keys()):
                result.differences.append(Difference(
                    object_type="constraint",
                    path=f"{table}.{con_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_table_con[con_name],
                ))
            
            # Constraints only in target
            for con_name in set(tgt_table_con.keys()) - set(src_table_con.keys()):
                result.differences.append(Difference(
                    object_type="constraint",
                    path=f"{table}.{con_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_table_con[con_name],
                ))
            
            # Constraints in both - compare attributes
            for con_name in set(src_table_con.keys()) & set(tgt_table_con.keys()):
                self._compare_dicts(
                    src_table_con[con_name],
                    tgt_table_con[con_name],
                    "constraint",
                    f"{table}.{con_name}",
                    result,
                )
    
    def _compare_sequences(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare sequences."""
        src_seqs = source.get("sequences", {})
        tgt_seqs = target.get("sequences", {})
        
        all_schemas = set(src_seqs.keys()) | set(tgt_seqs.keys())
        
        for schema in all_schemas:
            src_schema_seqs = src_seqs.get(schema, {})
            tgt_schema_seqs = tgt_seqs.get(schema, {})
            
            # Sequences only in source
            for seq_name in set(src_schema_seqs.keys()) - set(tgt_schema_seqs.keys()):
                result.differences.append(Difference(
                    object_type="sequence",
                    path=f"{schema}.{seq_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_schema_seqs[seq_name],
                ))
            
            # Sequences only in target
            for seq_name in set(tgt_schema_seqs.keys()) - set(src_schema_seqs.keys()):
                result.differences.append(Difference(
                    object_type="sequence",
                    path=f"{schema}.{seq_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_schema_seqs[seq_name],
                ))
            
            # Sequences in both - compare attributes
            for seq_name in set(src_schema_seqs.keys()) & set(tgt_schema_seqs.keys()):
                self._compare_dicts(
                    src_schema_seqs[seq_name],
                    tgt_schema_seqs[seq_name],
                    "sequence",
                    f"{schema}.{seq_name}",
                    result,
                )
    
    def _compare_functions(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare functions and procedures."""
        src_funcs = source.get("functions", {})
        tgt_funcs = target.get("functions", {})
        
        all_schemas = set(src_funcs.keys()) | set(tgt_funcs.keys())
        
        for schema in all_schemas:
            src_schema_funcs = src_funcs.get(schema, {})
            tgt_schema_funcs = tgt_funcs.get(schema, {})
            
            # Functions only in source
            for func_name in set(src_schema_funcs.keys()) - set(tgt_schema_funcs.keys()):
                result.differences.append(Difference(
                    object_type="function",
                    path=f"{schema}.{func_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_schema_funcs[func_name],
                ))
            
            # Functions only in target
            for func_name in set(tgt_schema_funcs.keys()) - set(src_schema_funcs.keys()):
                result.differences.append(Difference(
                    object_type="function",
                    path=f"{schema}.{func_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_schema_funcs[func_name],
                ))
            
            # Functions in both - compare attributes
            for func_name in set(src_schema_funcs.keys()) & set(tgt_schema_funcs.keys()):
                self._compare_dicts(
                    src_schema_funcs[func_name],
                    tgt_schema_funcs[func_name],
                    "function",
                    f"{schema}.{func_name}",
                    result,
                )
    
    def _compare_triggers(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare triggers."""
        src_triggers = source.get("triggers", {})
        tgt_triggers = target.get("triggers", {})
        
        all_tables = set(src_triggers.keys()) | set(tgt_triggers.keys())
        
        for table in all_tables:
            src_table_trg = src_triggers.get(table, {})
            tgt_table_trg = tgt_triggers.get(table, {})
            
            # Triggers only in source
            for trg_name in set(src_table_trg.keys()) - set(tgt_table_trg.keys()):
                result.differences.append(Difference(
                    object_type="trigger",
                    path=f"{table}.{trg_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_table_trg[trg_name],
                ))
            
            # Triggers only in target
            for trg_name in set(tgt_table_trg.keys()) - set(src_table_trg.keys()):
                result.differences.append(Difference(
                    object_type="trigger",
                    path=f"{table}.{trg_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_table_trg[trg_name],
                ))
            
            # Triggers in both - compare attributes
            for trg_name in set(src_table_trg.keys()) & set(tgt_table_trg.keys()):
                self._compare_dicts(
                    src_table_trg[trg_name],
                    tgt_table_trg[trg_name],
                    "trigger",
                    f"{table}.{trg_name}",
                    result,
                )
    
    def _compare_views(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare views and materialized views."""
        src_views = source.get("views", {})
        tgt_views = target.get("views", {})
        
        all_schemas = set(src_views.keys()) | set(tgt_views.keys())
        
        for schema in all_schemas:
            src_schema_views = src_views.get(schema, {})
            tgt_schema_views = tgt_views.get(schema, {})
            
            # Views only in source
            for view_name in set(src_schema_views.keys()) - set(tgt_schema_views.keys()):
                result.differences.append(Difference(
                    object_type="view",
                    path=f"{schema}.{view_name}",
                    diff_type=DifferenceType.REMOVED,
                    source_value=src_schema_views[view_name],
                ))
            
            # Views only in target
            for view_name in set(tgt_schema_views.keys()) - set(src_schema_views.keys()):
                result.differences.append(Difference(
                    object_type="view",
                    path=f"{schema}.{view_name}",
                    diff_type=DifferenceType.ADDED,
                    target_value=tgt_schema_views[view_name],
                ))
            
            # Views in both - compare attributes
            for view_name in set(src_schema_views.keys()) & set(tgt_schema_views.keys()):
                self._compare_dicts(
                    src_schema_views[view_name],
                    tgt_schema_views[view_name],
                    "view",
                    f"{schema}.{view_name}",
                    result,
                )
    
    def _compare_grants(
        self, source: dict, target: dict, result: ComparisonResult
    ):
        """Compare grants/permissions."""
        src_grants = source.get("grants", {})
        tgt_grants = target.get("grants", {})
        
        for grant_type in ["schemas", "tables", "columns", "sequences", "functions"]:
            src_type_grants = src_grants.get(grant_type, {})
            tgt_type_grants = tgt_grants.get(grant_type, {})
            
            all_objects = set(src_type_grants.keys()) | set(tgt_type_grants.keys())
            
            for obj_name in all_objects:
                src_obj_grants = set(self._grant_to_tuple(g) for g in src_type_grants.get(obj_name, []))
                tgt_obj_grants = set(self._grant_to_tuple(g) for g in tgt_type_grants.get(obj_name, []))
                
                # Grants only in source
                for grant in src_obj_grants - tgt_obj_grants:
                    result.differences.append(Difference(
                        object_type="grant",
                        path=f"{grant_type}.{obj_name}",
                        diff_type=DifferenceType.REMOVED,
                        source_value=grant,
                    ))
                
                # Grants only in target
                for grant in tgt_obj_grants - src_obj_grants:
                    result.differences.append(Difference(
                        object_type="grant",
                        path=f"{grant_type}.{obj_name}",
                        diff_type=DifferenceType.ADDED,
                        target_value=grant,
                    ))
    
    def _grant_to_tuple(self, grant: dict) -> tuple:
        """Convert a grant dict to a hashable tuple."""
        return (grant.get("grantee"), grant.get("privilege"), grant.get("is_grantable", False))
    
    def _compare_dicts(
        self, 
        source: dict, 
        target: dict, 
        object_type: str, 
        path: str, 
        result: ComparisonResult
    ):
        """Compare two dictionaries and record differences."""
        all_keys = set(source.keys()) | set(target.keys())
        
        modified_attrs = {}
        
        for key in all_keys:
            # Skip ignored keys
            if key in self.config.ignore_keys:
                continue
            if self.config.ignore_owners and key == "owner":
                continue
            if self.config.ignore_descriptions and key == "description":
                continue
            
            src_val = source.get(key)
            tgt_val = target.get(key)
            
            if src_val != tgt_val:
                modified_attrs[key] = {"source": src_val, "target": tgt_val}
        
        if modified_attrs:
            result.differences.append(Difference(
                object_type=object_type,
                path=path,
                diff_type=DifferenceType.MODIFIED,
                source_value=source,
                target_value=target,
                details={"modified_attributes": modified_attrs},
            ))
