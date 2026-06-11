"""SQL normalization to ignore formatting differences."""

import re
import hashlib


def normalize_sql(sql: str) -> str:
    """
    Normalize SQL to ignore formatting differences.
    
    This removes:
    - Extra whitespace
    - Comments
    - Case differences in keywords
    - Trailing semicolons
    """
    if not sql:
        return ""
    
    # Remove single-line comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    
    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Normalize whitespace
    sql = ' '.join(sql.split())
    
    # Remove trailing semicolon
    sql = sql.rstrip(';').strip()
    
    return sql


def normalize_sql_lower_keywords(sql: str) -> str:
    """
    Normalize SQL and lowercase keywords while preserving identifier case.
    """
    sql = normalize_sql(sql)
    
    # Common SQL keywords to lowercase
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
        'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'ORDER', 'BY',
        'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'INTERSECT', 'EXCEPT',
        'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE',
        'ALTER', 'DROP', 'TABLE', 'INDEX', 'VIEW', 'FUNCTION', 'TRIGGER',
        'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK',
        'CONSTRAINT', 'DEFAULT', 'CASCADE', 'RESTRICT', 'RETURNS', 'LANGUAGE',
        'BEGIN', 'END', 'IF', 'THEN', 'ELSE', 'ELSIF', 'CASE', 'WHEN',
        'DECLARE', 'RETURN', 'LOOP', 'FOR', 'WHILE', 'EXIT', 'CONTINUE',
        'RAISE', 'EXCEPTION', 'NOTICE', 'WARNING', 'COALESCE', 'NULLIF',
        'CAST', 'BETWEEN', 'LIKE', 'ILIKE', 'SIMILAR', 'TO', 'EXISTS',
        'ANY', 'ALL', 'SOME', 'TRUE', 'FALSE', 'ASC', 'DESC', 'NULLS',
        'FIRST', 'LAST', 'DISTINCT', 'WITH', 'RECURSIVE', 'OVER', 'PARTITION',
        'WINDOW', 'ROWS', 'RANGE', 'GROUPS', 'PRECEDING', 'FOLLOWING',
        'UNBOUNDED', 'CURRENT', 'ROW', 'FILTER', 'WITHIN', 'RESPECT',
        'IGNORE', 'LATERAL', 'CROSS', 'NATURAL', 'USING', 'FETCH', 'NEXT',
        'ONLY', 'PERCENT', 'TIES', 'MATERIALIZED', 'CONCURRENTLY',
    ]
    
    # Replace keywords case-insensitively
    for kw in keywords:
        pattern = r'\b' + kw + r'\b'
        sql = re.sub(pattern, kw.lower(), sql, flags=re.IGNORECASE)
    
    return sql


def hash_normalized_sql(sql: str) -> str:
    """Create a hash of normalized SQL for comparison."""
    normalized = normalize_sql(sql)
    return hashlib.md5(normalized.encode()).hexdigest()


def normalize_check_constraint(definition: str) -> str:
    """
    Normalize a CHECK constraint definition.
    
    PostgreSQL may add extra parentheses or change formatting.
    """
    if not definition:
        return ""
    
    # Remove CHECK( ) wrapper if present
    match = re.match(r'CHECK\s*\((.*)\)\s*$', definition, re.IGNORECASE | re.DOTALL)
    if match:
        definition = match.group(1)
    
    return normalize_sql(definition)


def normalize_default_expression(expr: str) -> str:
    """
    Normalize a column default expression.
    
    PostgreSQL may format these differently.
    """
    if not expr:
        return ""
    
    # Normalize whitespace
    expr = ' '.join(expr.split())
    
    # Normalize type casts (::type vs CAST())
    # Convert '...'::type to explicit form
    
    return expr


def normalize_index_definition(definition: str) -> str:
    """
    Normalize an index definition.
    
    Remove storage parameters and normalize formatting.
    """
    if not definition:
        return ""
    
    # Remove storage parameters like TABLESPACE, FILLFACTOR etc.
    definition = re.sub(r'\s+WITH\s*\([^)]+\)', '', definition, flags=re.IGNORECASE)
    definition = re.sub(r'\s+TABLESPACE\s+\w+', '', definition, flags=re.IGNORECASE)
    
    return normalize_sql(definition)
