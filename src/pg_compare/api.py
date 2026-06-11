"""High-level API for programmatic database comparison."""

from typing import Optional, Union
from pathlib import Path

from .connection import ConnectionConfig, DatabaseConnection, dual_connection
from .extractor import MetadataExtractor, ExtractionConfig
from .comparator import DatabaseComparator, ComparisonConfig, ComparisonResult
from .reporter import ComparisonReporter


def compare_databases(
    source: Union[str, dict, ConnectionConfig],
    target: Union[str, dict, ConnectionConfig],
    schemas: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    object_types: Optional[list[str]] = None,
    ignore_owners: bool = False,
    ignore_descriptions: bool = False,
    compare_grants: bool = True,
    compare_roles: bool = True,
) -> ComparisonResult:
    """
    Compare two PostgreSQL databases and return the differences.
    
    Args:
        source: Source database connection (URL string, dict, or ConnectionConfig)
        target: Target database connection (URL string, dict, or ConnectionConfig)
        schemas: List of schemas to compare (None = all non-system schemas)
        exclude_patterns: Patterns to exclude from comparison
        object_types: Object types to compare (None = all)
        ignore_owners: Whether to ignore owner differences
        ignore_descriptions: Whether to ignore description differences
        compare_grants: Whether to compare grants/permissions
        compare_roles: Whether to compare roles
    
    Returns:
        ComparisonResult with all identified differences
    
    Example:
        >>> result = compare_databases(
        ...     "postgresql://user:pass@localhost/db1",
        ...     "postgresql://user:pass@localhost/db2",
        ...     schemas=["public", "app"],
        ... )
        >>> print(f"Found {len(result.differences)} differences")
        >>> if result.has_differences:
        ...     for diff in result.differences:
        ...         print(diff)
    """
    # Parse connection configs
    source_config = _parse_connection(source)
    target_config = _parse_connection(target)
    
    # Configure extraction
    extraction_config = ExtractionConfig(
        include_schemas=schemas,
        exclude_patterns=exclude_patterns or [],
        object_types=object_types,
    )
    
    # Configure comparison
    comparison_config = ComparisonConfig(
        ignore_owners=ignore_owners,
        ignore_descriptions=ignore_descriptions,
        compare_grants=compare_grants,
        compare_roles=compare_roles,
    )
    
    # Connect and compare
    with dual_connection(source_config, target_config) as (source_conn, target_conn):
        source_extractor = MetadataExtractor(source_conn, extraction_config)
        source_metadata = source_extractor.extract_all()
        
        target_extractor = MetadataExtractor(target_conn, extraction_config)
        target_metadata = target_extractor.extract_all()
        
        comparator = DatabaseComparator(comparison_config)
        return comparator.compare(
            source_metadata,
            target_metadata,
            source_name=f"{source_config.database}@{source_config.host}",
            target_name=f"{target_config.database}@{target_config.host}",
        )


def generate_report(
    result: ComparisonResult,
    format: str = "console",
    output_path: Optional[Path] = None,
    verbose: bool = False,
) -> str:
    """
    Generate a report from comparison results.
    
    Args:
        result: ComparisonResult from compare_databases()
        format: Output format ("console", "json", "html", "markdown")
        output_path: Optional path to save report
        verbose: Whether to include detailed information
    
    Returns:
        Report as string
    """
    reporter = ComparisonReporter(result)
    
    if format == "console":
        content = reporter.to_console(verbose=verbose)
    elif format == "json":
        content = reporter.to_json()
    elif format == "html":
        content = reporter.to_html()
    elif format == "markdown":
        content = reporter.to_markdown()
    else:
        raise ValueError(f"Unknown format: {format}")
    
    if output_path:
        output_path.write_text(content)
    
    return content


def extract_metadata(
    connection: Union[str, dict, ConnectionConfig],
    schemas: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    object_types: Optional[list[str]] = None,
) -> dict:
    """
    Extract metadata from a single database.
    
    Useful for saving metadata snapshots or custom comparison logic.
    
    Args:
        connection: Database connection (URL string, dict, or ConnectionConfig)
        schemas: List of schemas to extract (None = all non-system schemas)
        exclude_patterns: Patterns to exclude
        object_types: Object types to extract (None = all)
    
    Returns:
        Dictionary containing all extracted metadata
    """
    config = _parse_connection(connection)
    
    extraction_config = ExtractionConfig(
        include_schemas=schemas,
        exclude_patterns=exclude_patterns or [],
        object_types=object_types,
    )
    
    with DatabaseConnection(config) as conn:
        extractor = MetadataExtractor(conn, extraction_config)
        return extractor.extract_all()


def _parse_connection(conn: Union[str, dict, ConnectionConfig]) -> ConnectionConfig:
    """Parse various connection formats into ConnectionConfig."""
    if isinstance(conn, ConnectionConfig):
        return conn
    elif isinstance(conn, dict):
        return ConnectionConfig.from_dict(conn)
    elif isinstance(conn, str):
        return ConnectionConfig.from_url(conn)
    else:
        raise TypeError(f"Cannot parse connection from {type(conn)}")
