"""Tests for SQL normalizers."""

import pytest
from src.pg_compare.normalizers.sql import (
    normalize_sql,
    normalize_check_constraint,
    hash_normalized_sql,
)


class TestNormalizeSql:
    """Tests for SQL normalization."""
    
    def test_whitespace_normalization(self):
        """Should normalize whitespace."""
        sql1 = "SELECT   id,    name   FROM   users"
        sql2 = "SELECT id, name FROM users"
        
        assert normalize_sql(sql1) == normalize_sql(sql2)
    
    def test_newline_normalization(self):
        """Should handle newlines."""
        sql1 = """
            SELECT id, name
            FROM users
            WHERE active = true
        """
        sql2 = "SELECT id, name FROM users WHERE active = true"
        
        assert normalize_sql(sql1) == normalize_sql(sql2)
    
    def test_comment_removal_single_line(self):
        """Should remove single-line comments."""
        sql1 = "SELECT id FROM users -- get user ids"
        sql2 = "SELECT id FROM users"
        
        assert normalize_sql(sql1) == normalize_sql(sql2)
    
    def test_comment_removal_multi_line(self):
        """Should remove multi-line comments."""
        sql1 = "SELECT /* columns */ id, name FROM users"
        sql2 = "SELECT id, name FROM users"
        
        assert normalize_sql(sql1) == normalize_sql(sql2)
    
    def test_trailing_semicolon_removal(self):
        """Should remove trailing semicolons."""
        sql1 = "SELECT id FROM users;"
        sql2 = "SELECT id FROM users"
        
        assert normalize_sql(sql1) == normalize_sql(sql2)
    
    def test_empty_string(self):
        """Should handle empty strings."""
        assert normalize_sql("") == ""
        assert normalize_sql(None) == ""
    
    def test_preserves_string_literals(self):
        """Should preserve content in string literals."""
        sql = "SELECT * FROM users WHERE name = 'John   Doe'"
        normalized = normalize_sql(sql)
        
        # The literal should be preserved
        assert "'John   Doe'" in normalized


class TestNormalizeCheckConstraint:
    """Tests for CHECK constraint normalization."""
    
    def test_removes_check_wrapper(self):
        """Should remove CHECK() wrapper."""
        constraint = "CHECK ((value > 0))"
        normalized = normalize_check_constraint(constraint)
        
        assert "CHECK" not in normalized
        assert "(value > 0)" in normalized
    
    def test_normalizes_whitespace(self):
        """Should normalize whitespace in constraint."""
        constraint1 = "CHECK   (value   >   0)"
        constraint2 = "CHECK (value > 0)"
        
        assert normalize_check_constraint(constraint1) == normalize_check_constraint(constraint2)
    
    def test_empty_constraint(self):
        """Should handle empty constraints."""
        assert normalize_check_constraint("") == ""
        assert normalize_check_constraint(None) == ""


class TestHashNormalizedSql:
    """Tests for SQL hashing."""
    
    def test_same_sql_same_hash(self):
        """Same SQL should produce same hash."""
        sql = "SELECT id FROM users"
        
        hash1 = hash_normalized_sql(sql)
        hash2 = hash_normalized_sql(sql)
        
        assert hash1 == hash2
    
    def test_different_formatting_same_hash(self):
        """Different formatting should produce same hash."""
        sql1 = "SELECT   id   FROM   users"
        sql2 = "SELECT id FROM users"
        
        hash1 = hash_normalized_sql(sql1)
        hash2 = hash_normalized_sql(sql2)
        
        assert hash1 == hash2
    
    def test_different_sql_different_hash(self):
        """Different SQL should produce different hash."""
        sql1 = "SELECT id FROM users"
        sql2 = "SELECT name FROM users"
        
        hash1 = hash_normalized_sql(sql1)
        hash2 = hash_normalized_sql(sql2)
        
        assert hash1 != hash2
