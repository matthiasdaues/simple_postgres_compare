"""Main metadata extractor that orchestrates all extraction operations."""

from dataclasses import dataclass, field
from typing import Any, Optional
from .connection import DatabaseConnection
from .extractors.database import DatabaseExtractor
from .extractors.schemas import SchemaExtractor
from .extractors.tables import TableExtractor
from .extractors.columns import ColumnExtractor
from .extractors.indices import IndexExtractor
from .extractors.constraints import ConstraintExtractor
from .extractors.sequences import SequenceExtractor
from .extractors.functions import FunctionExtractor
from .extractors.triggers import TriggerExtractor
from .extractors.views import ViewExtractor
from .extractors.grants import GrantExtractor
from .extractors.roles import RoleExtractor
from .extractors.extensions import ExtensionExtractor


@dataclass
class ExtractionConfig:
    """Configuration for metadata extraction."""
    # Schemas to include (None = all non-system schemas)
    include_schemas: Optional[list[str]] = None
    # Patterns to exclude from extraction
    exclude_patterns: list[str] = field(default_factory=list)
    # Object types to extract (None = all)
    object_types: Optional[list[str]] = None
    # Whether to exclude system roles
    exclude_system_roles: bool = True


class MetadataExtractor:
    """Orchestrates extraction of all database metadata."""
    
    # All available object types
    ALL_OBJECT_TYPES = [
        "database",
        "extensions", 
        "roles",
        "schemas",
        "tables",
        "columns",
        "indices",
        "constraints",
        "sequences",
        "functions",
        "triggers",
        "views",
        "grants",
    ]
    
    def __init__(self, connection: DatabaseConnection, config: Optional[ExtractionConfig] = None):
        self.connection = connection
        self.config = config or ExtractionConfig()
        
        # Initialize all extractors
        self._extractors = {
            "database": DatabaseExtractor(connection),
            "schemas": SchemaExtractor(connection),
            "tables": TableExtractor(connection),
            "columns": ColumnExtractor(connection),
            "indices": IndexExtractor(connection),
            "constraints": ConstraintExtractor(connection),
            "sequences": SequenceExtractor(connection),
            "functions": FunctionExtractor(connection),
            "triggers": TriggerExtractor(connection),
            "views": ViewExtractor(connection),
            "grants": GrantExtractor(connection),
            "roles": RoleExtractor(connection),
            "extensions": ExtensionExtractor(connection),
        }
    
    def extract_all(self) -> dict[str, Any]:
        """Extract all metadata from the database."""
        object_types = self.config.object_types or self.ALL_OBJECT_TYPES
        
        metadata = {}
        
        for obj_type in object_types:
            if obj_type not in self._extractors:
                continue
            
            extractor = self._extractors[obj_type]
            
            # Call extract with appropriate parameters
            if obj_type == "database":
                metadata[obj_type] = extractor.extract()
            elif obj_type == "roles":
                metadata[obj_type] = extractor.extract(
                    exclude_system=self.config.exclude_system_roles
                )
            elif obj_type == "extensions":
                metadata[obj_type] = extractor.extract()
            elif obj_type == "schemas":
                metadata[obj_type] = extractor.extract(
                    exclude_patterns=self.config.exclude_patterns
                )
            else:
                # Schema-scoped extractors
                metadata[obj_type] = extractor.extract(
                    schemas=self.config.include_schemas,
                    exclude_patterns=self.config.exclude_patterns
                )
        
        return metadata
    
    def extract_type(self, object_type: str) -> dict[str, Any]:
        """Extract metadata for a specific object type."""
        if object_type not in self._extractors:
            raise ValueError(f"Unknown object type: {object_type}")
        
        extractor = self._extractors[object_type]
        
        if object_type == "database":
            return extractor.extract()
        elif object_type == "roles":
            return extractor.extract(exclude_system=self.config.exclude_system_roles)
        elif object_type == "extensions":
            return extractor.extract()
        elif object_type == "schemas":
            return extractor.extract(exclude_patterns=self.config.exclude_patterns)
        else:
            return extractor.extract(
                schemas=self.config.include_schemas,
                exclude_patterns=self.config.exclude_patterns
            )
