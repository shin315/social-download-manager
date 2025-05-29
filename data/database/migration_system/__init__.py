"""
Migration System for Social Download Manager

This module provides comprehensive migration capabilities including:
- Version detection and schema analysis
- Safe schema transformation between versions
- Data conversion with platform detection and metadata parsing
- Data integrity validation with multiple validation levels
- Complete migration orchestration with safety mechanisms

Components:
- VersionManager: High-level version detection and migration planning
- SchemaTransformationManager: Database schema transformation orchestration
- DataConversionManager: Data format conversion between schema versions
- DataIntegrityManager: Comprehensive integrity validation system
"""

# Version Detection System
from .version_detection import (
    DatabaseVersion,
    VersionInfo,
    VersionDetector,
    VersionManager
)

# Schema Transformation Engine  
from .schema_transformation import (
    TransformationType,
    TransformationStep,
    TransformationPlan,
    ISchemaTransformer,
    SQLiteSchemaTransformer,
    SchemaTransformationManager
)

# Data Conversion Logic
from .data_conversion import (
    ConversionStats,
    V1DownloadRecord,
    V2ContentRecord,
    V2DownloadRecord,
    PlatformDetector,
    MetadataParser,
    SQLiteDataConverter,
    DataConversionManager
)

# Data Integrity Validation
from .data_integrity import (
    ValidationLevel,
    ValidationResult,
    ValidationIssue,
    TableChecksum,
    IntegrityReport,
    IDataIntegrityValidator,
    SQLiteIntegrityValidator,
    DataIntegrityManager
)

__all__ = [
    # Version Detection
    'DatabaseVersion',
    'VersionInfo', 
    'VersionDetector',
    'VersionManager',
    
    # Schema Transformation
    'TransformationType',
    'TransformationStep',
    'TransformationPlan',
    'ISchemaTransformer',
    'SQLiteSchemaTransformer',
    'SchemaTransformationManager',
    
    # Data Conversion
    'ConversionStats',
    'V1DownloadRecord',
    'V2ContentRecord',
    'V2DownloadRecord',
    'PlatformDetector',
    'MetadataParser',
    'SQLiteDataConverter',
    'DataConversionManager',
    
    # Data Integrity
    'ValidationLevel',
    'ValidationResult',
    'ValidationIssue',
    'TableChecksum',
    'IntegrityReport',
    'IDataIntegrityValidator',
    'SQLiteIntegrityValidator',
    'DataIntegrityManager'
] 