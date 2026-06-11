"""
pg_compare - PostgreSQL Database Comparison Tool

A utility to perform in-depth comparison between two PostgreSQL databases,
identifying material differences in static DB setup while ignoring formatting differences.
"""

__version__ = "0.1.0"

from .connection import DatabaseConnection, ConnectionConfig, dual_connection
from .extractor import MetadataExtractor, ExtractionConfig
from .comparator import DatabaseComparator, ComparisonConfig, ComparisonResult, Difference, DifferenceType
from .reporter import ComparisonReporter
from .api import compare_databases, generate_report, extract_metadata

__all__ = [
    # High-level API
    "compare_databases",
    "generate_report",
    "extract_metadata",
    # Core classes
    "DatabaseConnection",
    "ConnectionConfig",
    "dual_connection",
    "MetadataExtractor",
    "ExtractionConfig",
    "DatabaseComparator",
    "ComparisonConfig",
    "ComparisonResult",
    "Difference",
    "DifferenceType",
    "ComparisonReporter",
]
