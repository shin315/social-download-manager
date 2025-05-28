"""
Base Model Classes for Social Download Manager v2.0

Provides abstract base models with common CRUD operations, validation,
type conversions, and entity lifecycle management.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import sqlite3

# Type aliases for better readability
EntityId = Union[int, str]
Timestamp = datetime
JsonData = Dict[str, Any]

T = TypeVar('T', bound='BaseEntity')


class ModelError(Exception):
    """Base exception for model-related errors"""
    pass


class ValidationError(ModelError):
    """Exception for data validation errors"""
    
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Validation error for {field}: {message}")


@dataclass
class BaseEntity:
    """
    Abstract base entity with common fields and operations
    
    Provides basic fields that all entities should have including
    ID, timestamps, and lifecycle management.
    """
    id: Optional[EntityId] = None
    created_at: Optional[Timestamp] = None
    updated_at: Optional[Timestamp] = None
    version: int = 1
    is_deleted: bool = False
    metadata: JsonData = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamps if not provided"""
        current_time = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = current_time
        if self.updated_at is None:
            self.updated_at = current_time
    
    def mark_updated(self) -> None:
        """Mark entity as updated with current timestamp"""
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1
    
    def mark_deleted(self) -> None:
        """Soft delete the entity"""
        self.is_deleted = True
        self.mark_updated()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary with proper type conversion"""
        data = asdict(self)
        
        # Convert timestamps to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        
        # Convert metadata to JSON string
        if self.metadata:
            data['metadata'] = json.dumps(self.metadata)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEntity':
        """Create entity from dictionary with proper type conversion"""
        # Convert timestamp strings back to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        # Convert JSON string back to dict
        if 'metadata' in data and isinstance(data['metadata'], str):
            try:
                data['metadata'] = json.loads(data['metadata'])
            except (json.JSONDecodeError, TypeError):
                data['metadata'] = {}
        
        return cls(**data)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'BaseEntity':
        """Create entity from database row"""
        # Convert sqlite3.Row to dict properly
        data = {key: row[key] for key in row.keys()}
        return cls.from_dict(data)


class BaseModel(ABC, Generic[T]):
    """
    Abstract base model providing common database operations
    
    Implements the Active Record pattern with CRUD operations,
    validation, and entity lifecycle management.
    """
    
    def __init__(self, connection_manager=None):
        """
        Initialize base model
        
        Args:
            connection_manager: Database connection manager instance
        """
        self._connection_manager = connection_manager
        self._logger = logging.getLogger(self.__class__.__name__)
        self._table_name = self.get_table_name()
        self._entity_class = self.get_entity_class()
    
    @abstractmethod
    def get_table_name(self) -> str:
        """Get the database table name for this model"""
        pass
    
    @abstractmethod
    def get_entity_class(self) -> type:
        """Get the entity class this model manages"""
        pass
    
    @abstractmethod
    def get_schema(self) -> str:
        """Get the CREATE TABLE SQL schema for this model"""
        pass
    
    def validate_entity(self, entity: T) -> List[ValidationError]:
        """
        Validate entity data
        
        Args:
            entity: Entity to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic validation - can be overridden in subclasses
        if hasattr(entity, 'id') and entity.id is not None:
            if not isinstance(entity.id, (int, str)):
                errors.append(ValidationError('id', entity.id, 'ID must be int or string'))
        
        return errors
    
    def _get_connection(self):
        """Get database connection from manager"""
        if not self._connection_manager:
            from ..database import get_connection_manager
            self._connection_manager = get_connection_manager()
        
        return self._connection_manager.get_connection()
    
    def _return_connection(self, connection):
        """Return database connection to manager"""
        if self._connection_manager:
            self._connection_manager.return_connection(connection)
    
    def create_table(self) -> bool:
        """
        Create the table for this model if it doesn't exist
        
        Returns:
            True if table created or already exists
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                
                # Split schema into individual statements
                schema = self.get_schema()
                statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
                
                # Execute each statement separately
                for statement in statements:
                    cursor.execute(statement)
                
                connection.commit()
                cursor.close()
                self._logger.info(f"Table {self._table_name} created successfully")
                return True
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to create table {self._table_name}: {e}")
            return False
    
    def save(self, entity: T) -> Optional[T]:
        """
        Save entity to database (insert or update)
        
        Args:
            entity: Entity to save
            
        Returns:
            Saved entity with updated ID and timestamps, None if failed
        """
        # Validate entity
        validation_errors = self.validate_entity(entity)
        if validation_errors:
            for error in validation_errors:
                self._logger.error(f"Validation error: {error}")
            return None
        
        try:
            if entity.id is None:
                return self._insert(entity)
            else:
                return self._update(entity)
        except Exception as e:
            self._logger.error(f"Failed to save entity: {e}")
            return None
    
    def _insert(self, entity: T) -> Optional[T]:
        """Insert new entity"""
        entity.mark_updated()  # Set timestamps
        
        connection = self._get_connection()
        try:
            cursor = connection.cursor()
            
            # Build INSERT statement
            data = entity.to_dict()
            if 'id' in data and data['id'] is None:
                del data['id']  # Let database generate ID
            
            columns = list(data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = [data[col] for col in columns]
            
            sql = f"INSERT INTO {self._table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            cursor.execute(sql, values)
            entity.id = cursor.lastrowid
            connection.commit()
            cursor.close()
            
            self._logger.debug(f"Inserted entity with ID {entity.id}")
            return entity
            
        except Exception as e:
            connection.rollback()
            self._logger.error(f"Failed to insert entity: {e}")
            return None
        finally:
            self._return_connection(connection)
    
    def _update(self, entity: T) -> Optional[T]:
        """Update existing entity"""
        entity.mark_updated()
        
        connection = self._get_connection()
        try:
            cursor = connection.cursor()
            
            # Build UPDATE statement
            data = entity.to_dict()
            entity_id = data.pop('id')  # Remove ID from data
            
            set_clauses = [f"{col} = ?" for col in data.keys()]
            values = list(data.values()) + [entity_id]
            
            sql = f"UPDATE {self._table_name} SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(sql, values)
            connection.commit()
            cursor.close()
            
            self._logger.debug(f"Updated entity with ID {entity_id}")
            return entity
            
        except Exception as e:
            connection.rollback()
            self._logger.error(f"Failed to update entity: {e}")
            return None
        finally:
            self._return_connection(connection)
    
    def find_by_id(self, entity_id: EntityId) -> Optional[T]:
        """
        Find entity by ID
        
        Args:
            entity_id: Entity ID to search for
            
        Returns:
            Entity if found, None otherwise
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(f"SELECT * FROM {self._table_name} WHERE id = ? AND is_deleted = 0", (entity_id,))
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    return self._entity_class.from_row(row)
                return None
                
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to find entity by ID {entity_id}: {e}")
            return None
    
    def find_all(self, include_deleted: bool = False) -> List[T]:
        """
        Find all entities
        
        Args:
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            List of entities
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                
                if include_deleted:
                    cursor.execute(f"SELECT * FROM {self._table_name} ORDER BY created_at DESC")
                else:
                    cursor.execute(f"SELECT * FROM {self._table_name} WHERE is_deleted = 0 ORDER BY created_at DESC")
                
                rows = cursor.fetchall()
                cursor.close()
                
                return [self._entity_class.from_row(row) for row in rows]
                
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to find all entities: {e}")
            return []
    
    def find_by_criteria(self, criteria: Dict[str, Any], include_deleted: bool = False) -> List[T]:
        """
        Find entities by criteria
        
        Args:
            criteria: Search criteria as column-value pairs
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            List of matching entities
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                
                # Build WHERE clause
                where_clauses = [f"{col} = ?" for col in criteria.keys()]
                if not include_deleted:
                    where_clauses.append("is_deleted = 0")
                
                where_clause = " AND ".join(where_clauses)
                values = list(criteria.values())
                
                sql = f"SELECT * FROM {self._table_name} WHERE {where_clause} ORDER BY created_at DESC"
                
                cursor.execute(sql, values)
                rows = cursor.fetchall()
                cursor.close()
                
                return [self._entity_class.from_row(row) for row in rows]
                
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to find entities by criteria: {e}")
            return []
    
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        """
        Delete entity by ID
        
        Args:
            entity_id: Entity ID to delete
            soft_delete: If True, perform soft delete; if False, hard delete
            
        Returns:
            True if deletion successful
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                
                if soft_delete:
                    # Soft delete
                    current_time = datetime.now(timezone.utc).isoformat()
                    cursor.execute(
                        f"UPDATE {self._table_name} SET is_deleted = 1, updated_at = ? WHERE id = ?",
                        (current_time, entity_id)
                    )
                else:
                    # Hard delete
                    cursor.execute(f"DELETE FROM {self._table_name} WHERE id = ?", (entity_id,))
                
                affected_rows = cursor.rowcount
                connection.commit()
                cursor.close()
                
                if affected_rows > 0:
                    self._logger.debug(f"Deleted entity with ID {entity_id} (soft={soft_delete})")
                    return True
                else:
                    self._logger.warning(f"No entity found with ID {entity_id} for deletion")
                    return False
                    
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to delete entity {entity_id}: {e}")
            return False
    
    def count(self, include_deleted: bool = False) -> int:
        """
        Count entities in table
        
        Args:
            include_deleted: Whether to include soft-deleted entities
            
        Returns:
            Count of entities
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                
                if include_deleted:
                    cursor.execute(f"SELECT COUNT(*) FROM {self._table_name}")
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM {self._table_name} WHERE is_deleted = 0")
                
                count = cursor.fetchone()[0]
                cursor.close()
                return count
                
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to count entities: {e}")
            return 0
    
    def exists(self, entity_id: EntityId) -> bool:
        """
        Check if entity exists by ID
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if entity exists and not soft-deleted
        """
        try:
            connection = self._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    f"SELECT 1 FROM {self._table_name} WHERE id = ? AND is_deleted = 0",
                    (entity_id,)
                )
                result = cursor.fetchone()
                cursor.close()
                return result is not None
                
            finally:
                self._return_connection(connection)
        except Exception as e:
            self._logger.error(f"Failed to check existence of entity {entity_id}: {e}")
            return False 