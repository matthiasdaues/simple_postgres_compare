# pg_compare - PostgreSQL Database Comparison Tool

A utility to perform in-depth comparison between two PostgreSQL databases, identifying **material differences** in static DB setup while **ignoring formatting differences**.

## Features

- **Comprehensive Comparison**: Compares schemas, tables, columns, indices, constraints, sequences, triggers, functions, procedures, views, grants, roles, and extensions
- **Ignores Formatting**: SQL and DDL formatting differences are normalized - only semantic differences are reported
- **Multiple Output Formats**: Console, JSON, HTML, and Markdown reports
- **Flexible Filtering**: Compare specific schemas, exclude patterns, or focus on specific object types
- **CLI & API**: Use from command line or integrate programmatically

## Installation

```bash
# Clone and install
git clone <repository-url>
cd simple_postgres_compare
poetry install
```

## Quick Start

### Command Line

```bash
# Compare two databases
poetry run pg-compare \
    "postgresql://user:pass@localhost:5432/source_db" \
    "postgresql://user:pass@localhost:5432/target_db"

# Save report to file
poetry run pg-compare source target -o report.html

# Compare specific schemas only
poetry run pg-compare source target --schemas public app

# Ignore owner differences
poetry run pg-compare source target --ignore-owners

# Output as JSON
poetry run pg-compare source target -f json
```

### Python API

```python
from src.pg_compare import compare_databases, generate_report

# Simple comparison
result = compare_databases(
    "postgresql://user:pass@localhost/db1",
    "postgresql://user:pass@localhost/db2",
)

# Check for differences
if result.has_differences:
    print(f"Found {len(result.differences)} differences")
    for diff in result.differences:
        print(f"  {diff}")

# Generate reports
print(generate_report(result, format="console"))
print(generate_report(result, format="markdown"))

# With options
result = compare_databases(
    source={"host": "localhost", "database": "db1", "user": "postgres", "password": "secret", "port": 5432},
    target={"host": "localhost", "database": "db2", "user": "postgres", "password": "secret", "port": 5432},
    schemas=["public", "app"],           # Only these schemas
    exclude_patterns=["_backup", "tmp"], # Exclude matching objects
    ignore_owners=True,                  # Don't report owner differences
    compare_grants=False,                # Skip permission comparison
)
```

## What Gets Compared

| Object Type | Attributes Compared |
|-------------|---------------------|
| **Database** | Version, encoding, collation |
| **Extensions** | Name, version, schema |
| **Roles** | Privileges, membership, login capability |
| **Schemas** | Name, owner |
| **Tables** | Owner, persistence, partitioning |
| **Columns** | Data type, nullability, defaults, identity, generated |
| **Indices** | Type, columns, uniqueness, partial predicates |
| **Constraints** | Type (PK/FK/CHECK/UNIQUE), columns, references, actions |
| **Sequences** | Start, min, max, increment, cycle |
| **Functions** | Arguments, return type, language, volatility, source hash |
| **Triggers** | Timing, events, function, enabled state |
| **Views** | Type (regular/materialized), definition hash |
| **Grants** | Grantee, privilege, grantable |

## Ignoring Formatting Differences

The tool normalizes SQL and DDL before comparison:

- Whitespace differences are ignored
- SQL comments are stripped
- Keyword case is normalized
- Trailing semicolons are removed

This means two functions with identical logic but different formatting will be considered **equal**.

## CLI Reference

```
usage: pg-compare [-h] [-o OUTPUT] [-f {console,json,html,markdown}] [-v]
                  [--schemas SCHEMAS [SCHEMAS ...]]
                  [--exclude EXCLUDE [EXCLUDE ...]]
                  [--types {database,extensions,roles,...} [...]]
                  [--ignore-owners] [--ignore-descriptions]
                  [--no-grants] [--no-roles]
                  source target

Connection string formats:
  - postgresql://user:password@host:port/database
  - host:port:database:user:password
  - host=X port=Y dbname=Z user=U password=P
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Save report to file (format from extension) |
| `-f, --format` | Output format: console, json, html, markdown |
| `-v, --verbose` | Show detailed values for each difference |
| `--schemas` | Only compare specified schemas |
| `--exclude` | Patterns to exclude from comparison |
| `--types` | Only compare specified object types |
| `--ignore-owners` | Ignore owner differences |
| `--ignore-descriptions` | Ignore description/comment differences |
| `--no-grants` | Skip grant/permission comparison |
| `--no-roles` | Skip role comparison |

## Project Structure

```
├── src/
│   ├── pg_compare/             # Main comparison package
│   │   ├── __init__.py         # Public API exports
│   │   ├── api.py              # High-level API functions
│   │   ├── cli.py              # Command-line interface
│   │   ├── connection.py       # Database connection handling
│   │   ├── extractor.py        # Metadata extraction orchestration
│   │   ├── comparator.py       # Comparison engine
│   │   ├── reporter.py         # Report generation
│   │   ├── extractors/         # Individual object extractors
│   │   │   ├── tables.py
│   │   │   ├── columns.py
│   │   │   ├── indices.py
│   │   │   └── ...
│   │   └── normalizers/        # SQL normalization
│   │       └── sql.py
│   ├── python/                 # Legacy utilities
│   └── sql/                    # SQL query files
├── notebooks/                  # Jupyter notebooks
├── tests/                      # Test suite
└── pyproject.toml
```

## Example Output

### Console Report

```
======================================================================
PostgreSQL Database Comparison Report
======================================================================
Source: production@prod-server
Target: staging@staging-server
Generated: 2024-01-15T10:30:00

----------------------------------------------------------------------
SUMMARY
----------------------------------------------------------------------
Total differences: 5
  - Added (in target only):   2
  - Removed (in source only): 1
  - Modified:                 2

By object type:
  column: 2 difference(s)
  index: 1 difference(s)
  table: 2 difference(s)

----------------------------------------------------------------------
DETAILS
----------------------------------------------------------------------

### TABLE (2)
  [+] public.new_feature_flags
  [-] public.deprecated_settings

### COLUMN (2)
  [~] public.users.email
      data_type:
        source: varchar(100)
        target: varchar(255)
```

## Development

```bash
# Install with dev dependencies
poetry install

# Run tests
poetry run pytest

# Run specific test
poetry run pytest tests/test_comparator.py -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.