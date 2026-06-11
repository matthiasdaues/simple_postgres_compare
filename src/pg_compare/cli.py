"""Command-line interface for pg_compare."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .connection import ConnectionConfig, DatabaseConnection, dual_connection
from .extractor import MetadataExtractor, ExtractionConfig
from .comparator import DatabaseComparator, ComparisonConfig
from .reporter import ComparisonReporter


def parse_connection_string(conn_str: str) -> ConnectionConfig:
    """Parse a connection string into ConnectionConfig."""
    # Support formats:
    # - postgresql://user:pass@host:port/dbname
    # - host:port:dbname:user:password (colon-separated)
    # - host=X port=Y dbname=Z user=U password=P (DSN style)
    
    if conn_str.startswith("postgresql://") or conn_str.startswith("postgres://"):
        return ConnectionConfig.from_url(conn_str)
    
    if "=" in conn_str:
        # DSN style
        parts = {}
        for part in conn_str.split():
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key] = value
        return ConnectionConfig(
            host=parts.get("host", "localhost"),
            port=int(parts.get("port", 5432)),
            database=parts.get("dbname", parts.get("database", "postgres")),
            user=parts.get("user", "postgres"),
            password=parts.get("password", ""),
        )
    
    # Colon-separated: host:port:dbname:user:password
    parts = conn_str.split(":")
    return ConnectionConfig(
        host=parts[0] if len(parts) > 0 else "localhost",
        port=int(parts[1]) if len(parts) > 1 else 5432,
        database=parts[2] if len(parts) > 2 else "postgres",
        user=parts[3] if len(parts) > 3 else "postgres",
        password=parts[4] if len(parts) > 4 else "",
    )


def main(args: Optional[list[str]] = None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pg_compare",
        description="Compare two PostgreSQL databases and identify structural differences",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Connection string formats:
  - postgresql://user:password@host:port/database
  - host:port:database:user:password
  - host=X port=Y dbname=Z user=U password=P

Examples:
  %(prog)s postgresql://user:pass@localhost:5432/db1 postgresql://user:pass@localhost:5432/db2
  %(prog)s localhost:5432:source_db:postgres:secret localhost:5432:target_db:postgres:secret
  %(prog)s "host=localhost dbname=db1 user=postgres" "host=localhost dbname=db2 user=postgres"
        """
    )
    
    parser.add_argument(
        "source",
        help="Source database connection string"
    )
    parser.add_argument(
        "target",
        help="Target database connection string"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (format determined by extension: .json, .html, .md, .txt)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["console", "json", "html", "markdown"],
        default="console",
        help="Output format (default: console)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed information for each difference"
    )
    
    # Filter options
    parser.add_argument(
        "--schemas",
        nargs="+",
        help="Only compare specified schemas"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Patterns to exclude from comparison"
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=[
            "database", "extensions", "roles", "schemas", "tables",
            "columns", "indices", "constraints", "sequences",
            "functions", "triggers", "views", "grants"
        ],
        help="Only compare specified object types"
    )
    
    # Comparison options
    parser.add_argument(
        "--ignore-owners",
        action="store_true",
        help="Ignore owner differences"
    )
    parser.add_argument(
        "--ignore-descriptions",
        action="store_true",
        help="Ignore description/comment differences"
    )
    parser.add_argument(
        "--no-grants",
        action="store_true",
        help="Skip grant/permission comparison"
    )
    parser.add_argument(
        "--no-roles",
        action="store_true",
        help="Skip role comparison"
    )
    
    parsed = parser.parse_args(args)
    
    # Parse connection strings
    try:
        source_config = parse_connection_string(parsed.source)
        target_config = parse_connection_string(parsed.target)
    except Exception as e:
        print(f"Error parsing connection string: {e}", file=sys.stderr)
        return 1
    
    # Configure extraction
    extraction_config = ExtractionConfig(
        include_schemas=parsed.schemas,
        exclude_patterns=parsed.exclude,
        object_types=parsed.types,
    )
    
    # Configure comparison
    comparison_config = ComparisonConfig(
        ignore_owners=parsed.ignore_owners,
        ignore_descriptions=parsed.ignore_descriptions,
        compare_grants=not parsed.no_grants,
        compare_roles=not parsed.no_roles,
    )
    
    try:
        # Connect to both databases
        print(f"Connecting to source: {source_config.database}@{source_config.host}...", file=sys.stderr)
        print(f"Connecting to target: {target_config.database}@{target_config.host}...", file=sys.stderr)
        
        with dual_connection(source_config, target_config) as (source_conn, target_conn):
            # Extract metadata
            print("Extracting metadata from source...", file=sys.stderr)
            source_extractor = MetadataExtractor(source_conn, extraction_config)
            source_metadata = source_extractor.extract_all()
            
            print("Extracting metadata from target...", file=sys.stderr)
            target_extractor = MetadataExtractor(target_conn, extraction_config)
            target_metadata = target_extractor.extract_all()
            
            # Compare
            print("Comparing databases...", file=sys.stderr)
            comparator = DatabaseComparator(comparison_config)
            result = comparator.compare(
                source_metadata,
                target_metadata,
                source_name=f"{source_config.database}@{source_config.host}",
                target_name=f"{target_config.database}@{target_config.host}",
            )
            
            # Generate report
            reporter = ComparisonReporter(result)
            
            if parsed.output:
                reporter.save(parsed.output, format=parsed.format if parsed.format != "console" else "auto")
                print(f"Report saved to: {parsed.output}", file=sys.stderr)
            else:
                if parsed.format == "console":
                    print(reporter.to_console(verbose=parsed.verbose))
                elif parsed.format == "json":
                    print(reporter.to_json())
                elif parsed.format == "html":
                    print(reporter.to_html())
                elif parsed.format == "markdown":
                    print(reporter.to_markdown())
            
            # Return exit code based on differences
            return 1 if result.has_differences else 0
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
