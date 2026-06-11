"""Tests for the database comparator."""

import pytest
from src.pg_compare.comparator import (
    DatabaseComparator,
    ComparisonConfig,
    ComparisonResult,
    Difference,
    DifferenceType,
)


class TestDatabaseComparator:
    """Tests for DatabaseComparator."""
    
    def test_empty_databases_no_differences(self):
        """Two empty metadata sets should have no differences."""
        comparator = DatabaseComparator()
        result = comparator.compare({}, {})
        
        assert not result.has_differences
        assert len(result.differences) == 0
    
    def test_identical_databases_no_differences(self):
        """Identical metadata should produce no differences."""
        source = {
            "database": {"version": "15.0", "encoding": "UTF8"},
            "schemas": {"public": {"owner": "postgres"}},
            "tables": {"public": {"users": {"owner": "postgres"}}},
        }
        target = {
            "database": {"version": "15.0", "encoding": "UTF8"},
            "schemas": {"public": {"owner": "postgres"}},
            "tables": {"public": {"users": {"owner": "postgres"}}},
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert not result.has_differences
    
    def test_detect_added_table(self):
        """Should detect a table that exists only in target."""
        source = {
            "tables": {"public": {"users": {"owner": "postgres"}}},
        }
        target = {
            "tables": {
                "public": {
                    "users": {"owner": "postgres"},
                    "orders": {"owner": "postgres"},
                }
            },
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert result.has_differences
        assert result.added_count == 1
        
        added = result.filter_by_diff_type(DifferenceType.ADDED)
        assert len(added) == 1
        assert added[0].path == "public.orders"
    
    def test_detect_removed_table(self):
        """Should detect a table that exists only in source."""
        source = {
            "tables": {
                "public": {
                    "users": {"owner": "postgres"},
                    "old_table": {"owner": "postgres"},
                }
            },
        }
        target = {
            "tables": {"public": {"users": {"owner": "postgres"}}},
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert result.has_differences
        assert result.removed_count == 1
        
        removed = result.filter_by_diff_type(DifferenceType.REMOVED)
        assert len(removed) == 1
        assert removed[0].path == "public.old_table"
    
    def test_detect_modified_column(self):
        """Should detect a column with different data type."""
        source = {
            "columns": {
                "public.users": {
                    "email": {"data_type": "varchar(100)", "is_nullable": False}
                }
            },
        }
        target = {
            "columns": {
                "public.users": {
                    "email": {"data_type": "varchar(255)", "is_nullable": False}
                }
            },
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert result.has_differences
        assert result.modified_count == 1
        
        modified = result.filter_by_diff_type(DifferenceType.MODIFIED)
        assert len(modified) == 1
        assert "data_type" in modified[0].details["modified_attributes"]
    
    def test_ignore_owners_option(self):
        """Should ignore owner differences when configured."""
        source = {
            "tables": {"public": {"users": {"owner": "user1", "kind": "table"}}},
        }
        target = {
            "tables": {"public": {"users": {"owner": "user2", "kind": "table"}}},
        }
        
        # Without ignore_owners
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        assert result.has_differences
        
        # With ignore_owners
        config = ComparisonConfig(ignore_owners=True)
        comparator = DatabaseComparator(config)
        result = comparator.compare(source, target)
        assert not result.has_differences
    
    def test_extension_version_difference(self):
        """Should detect extension version differences."""
        source = {
            "extensions": {"pgcrypto": {"version": "1.0", "schema": "public"}},
        }
        target = {
            "extensions": {"pgcrypto": {"version": "1.1", "schema": "public"}},
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert result.has_differences
        ext_diffs = result.filter_by_type("extension")
        assert len(ext_diffs) == 1
        assert ext_diffs[0].diff_type == DifferenceType.MODIFIED
    
    def test_missing_extension(self):
        """Should detect missing extensions."""
        source = {
            "extensions": {
                "pgcrypto": {"version": "1.0"},
                "uuid-ossp": {"version": "1.1"},
            },
        }
        target = {
            "extensions": {"pgcrypto": {"version": "1.0"}},
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        assert result.removed_count == 1
        removed = result.filter_by_diff_type(DifferenceType.REMOVED)
        assert removed[0].path == "uuid-ossp"
    
    def test_summary_by_type(self):
        """Should produce correct summary statistics."""
        source = {
            "tables": {"public": {"t1": {}, "t2": {}}},
            "columns": {"public.t1": {"c1": {"data_type": "int"}}},
        }
        target = {
            "tables": {"public": {"t1": {}, "t3": {}}},  # t2 removed, t3 added
            "columns": {"public.t1": {"c1": {"data_type": "bigint"}}},  # modified
        }
        
        comparator = DatabaseComparator()
        result = comparator.compare(source, target)
        
        summary = result.summary()
        
        assert "table" in summary
        assert summary["table"]["removed"] == 1
        assert summary["table"]["added"] == 1
        assert "column" in summary
        assert summary["column"]["modified"] == 1


class TestComparisonResult:
    """Tests for ComparisonResult."""
    
    def test_filter_by_type(self):
        """Should filter differences by object type."""
        result = ComparisonResult(
            source_name="db1",
            target_name="db2",
            differences=[
                Difference("table", "public.t1", DifferenceType.ADDED),
                Difference("column", "public.t1.c1", DifferenceType.ADDED),
                Difference("table", "public.t2", DifferenceType.REMOVED),
            ],
        )
        
        tables = result.filter_by_type("table")
        assert len(tables) == 2
        
        columns = result.filter_by_type("column")
        assert len(columns) == 1
    
    def test_counts(self):
        """Should compute correct counts."""
        result = ComparisonResult(
            source_name="db1",
            target_name="db2",
            differences=[
                Difference("table", "t1", DifferenceType.ADDED),
                Difference("table", "t2", DifferenceType.ADDED),
                Difference("table", "t3", DifferenceType.REMOVED),
                Difference("column", "c1", DifferenceType.MODIFIED),
            ],
        )
        
        assert result.added_count == 2
        assert result.removed_count == 1
        assert result.modified_count == 1
        assert len(result.differences) == 4


class TestDifference:
    """Tests for Difference class."""
    
    def test_str_added(self):
        """String representation for added items."""
        diff = Difference("table", "public.users", DifferenceType.ADDED)
        assert "[+]" in str(diff)
        assert "table" in str(diff)
        assert "public.users" in str(diff)
    
    def test_str_removed(self):
        """String representation for removed items."""
        diff = Difference("table", "public.users", DifferenceType.REMOVED)
        assert "[-]" in str(diff)
    
    def test_str_modified(self):
        """String representation for modified items."""
        diff = Difference("column", "public.users.email", DifferenceType.MODIFIED)
        assert "[~]" in str(diff)
