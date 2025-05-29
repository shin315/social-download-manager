"""
Transaction-Aware Repository Implementation for Social Download Manager v2.0

Provides repository classes with transaction support, unit of work pattern,
and transactional operations for maintaining data consistency.
"""

from typing import List, Optional, Dict, Any, Callable, TypeVar, Generic, Type
from contextlib import contextmanager
from datetime import datetime
import logging

from .base import BaseEntity, EntityId
from .repositories import BaseRepository, IRepository, RepositoryError
from ..database import (
    get_transaction_manager, get_current_transaction,
    TransactionIsolationLevel, TransactionPropagation,
    Transaction, TransactionException
)

T = TypeVar('T', bound=BaseEntity)


class TransactionAwareRepositoryMixin:
    """
    Mixin providing transaction-aware operations for repositories
    
    Adds transaction support to any repository implementation,
    including automatic transaction detection and propagation.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transaction_manager = get_transaction_manager()
        self._logger = logging.getLogger(f"{self.__class__.__name__}.Transaction")
    
    def get_current_transaction(self) -> Optional[Transaction]:
        """Get the current active transaction if any"""
        return get_current_transaction()
    
    def _get_connection_for_transaction(self):
        """Get connection, preferring current transaction connection"""
        current_transaction = self.get_current_transaction()
        if current_transaction and current_transaction.is_active:
            return current_transaction.get_connection()
        else:
            return self._get_connection()
    
    def _should_return_connection(self, connection) -> bool:
        """Check if connection should be returned to pool"""
        current_transaction = self.get_current_transaction()
        if current_transaction and current_transaction.is_active:
            # Connection is managed by transaction
            return False
        return True
    
    @contextmanager
    def transaction(self, 
                   isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                   propagation: TransactionPropagation = TransactionPropagation.REQUIRED,
                   read_only: bool = False):
        """Context manager for repository operations within a transaction"""
        with self._transaction_manager.transaction(
            isolation_level=isolation_level,
            propagation=propagation,
            read_only=read_only
        ) as transaction:
            yield transaction
    
    def save_transactional(self, entity: T, commit: bool = True) -> Optional[T]:
        """
        Save entity within transaction with optional auto-commit
        
        Args:
            entity: Entity to save
            commit: Whether to auto-commit if no existing transaction
            
        Returns:
            Saved entity or None if failed
        """
        current_transaction = self.get_current_transaction()
        
        if current_transaction:
            # Use existing transaction
            return self.save(entity)
        else:
            # Create new transaction if commit is True
            if commit:
                try:
                    with self.transaction() as trans:
                        result = self.save(entity)
                        return result
                except Exception as e:
                    self._logger.error(f"Transactional save failed: {e}")
                    raise RepositoryError(f"Transactional save failed: {e}")
            else:
                # No transaction, normal save
                return self.save(entity)
    
    def delete_transactional(self, entity_id: EntityId, soft_delete: bool = True, commit: bool = True) -> bool:
        """
        Delete entity within transaction with optional auto-commit
        
        Args:
            entity_id: ID of entity to delete
            soft_delete: Whether to perform soft delete
            commit: Whether to auto-commit if no existing transaction
            
        Returns:
            True if deleted successfully
        """
        current_transaction = self.get_current_transaction()
        
        if current_transaction:
            # Use existing transaction
            return self.delete(entity_id, soft_delete)
        else:
            # Create new transaction if commit is True
            if commit:
                try:
                    with self.transaction() as trans:
                        result = self.delete(entity_id, soft_delete)
                        return result
                except Exception as e:
                    self._logger.error(f"Transactional delete failed: {e}")
                    raise RepositoryError(f"Transactional delete failed: {e}")
            else:
                # No transaction, normal delete
                return self.delete(entity_id, soft_delete)
    
    def bulk_save_transactional(self, entities: List[T], batch_size: int = 100) -> List[T]:
        """
        Save multiple entities in batches within a transaction
        
        Args:
            entities: List of entities to save
            batch_size: Number of entities per batch
            
        Returns:
            List of saved entities
        """
        if not entities:
            return []
        
        saved_entities = []
        
        try:
            with self.transaction() as trans:
                for i in range(0, len(entities), batch_size):
                    batch = entities[i:i + batch_size]
                    
                    for entity in batch:
                        saved_entity = self.save(entity)
                        if saved_entity:
                            saved_entities.append(saved_entity)
                    
                    self._logger.debug(f"Processed batch {i//batch_size + 1}: {len(batch)} entities")
                
                self._logger.info(f"Bulk save completed: {len(saved_entities)}/{len(entities)} entities saved")
                return saved_entities
                
        except Exception as e:
            self._logger.error(f"Bulk save transaction failed: {e}")
            raise RepositoryError(f"Bulk save failed: {e}")
    
    def bulk_delete_transactional(self, entity_ids: List[EntityId], 
                                 soft_delete: bool = True, batch_size: int = 100) -> int:
        """
        Delete multiple entities in batches within a transaction
        
        Args:
            entity_ids: List of entity IDs to delete
            soft_delete: Whether to perform soft delete
            batch_size: Number of entities per batch
            
        Returns:
            Number of entities deleted
        """
        if not entity_ids:
            return 0
        
        deleted_count = 0
        
        try:
            with self.transaction() as trans:
                for i in range(0, len(entity_ids), batch_size):
                    batch = entity_ids[i:i + batch_size]
                    
                    for entity_id in batch:
                        if self.delete(entity_id, soft_delete):
                            deleted_count += 1
                    
                    self._logger.debug(f"Processed batch {i//batch_size + 1}: {len(batch)} entities")
                
                self._logger.info(f"Bulk delete completed: {deleted_count}/{len(entity_ids)} entities deleted")
                return deleted_count
                
        except Exception as e:
            self._logger.error(f"Bulk delete transaction failed: {e}")
            raise RepositoryError(f"Bulk delete failed: {e}")


class TransactionalRepository(BaseRepository[T], TransactionAwareRepositoryMixin):
    """
    Repository base class with full transaction support
    
    Combines BaseRepository functionality with transaction awareness
    for complete data consistency management.
    """
    
    def __init__(self, model_manager, *args, **kwargs):
        super().__init__(model_manager, *args, **kwargs)
    
    def save(self, entity: T) -> Optional[T]:
        """Override save to use transaction-aware connection"""
        try:
            connection = self._get_connection_for_transaction()
            try:
                # Validate entity
                validation_errors = self._model.validate_entity(entity)
                if validation_errors:
                    error_messages = [str(error) for error in validation_errors]
                    raise RepositoryError(f"Validation failed: {', '.join(error_messages)}")
                
                # Save using transaction-aware connection
                if entity.id is None:
                    result = self._insert_with_connection(entity, connection)
                else:
                    result = self._update_with_connection(entity, connection)
                
                return result
                
            finally:
                if self._should_return_connection(connection):
                    self._return_connection(connection)
                    
        except Exception as e:
            self._logger.error(f"Failed to save entity: {e}")
            raise RepositoryError(f"Save operation failed: {e}")
    
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        """Override delete to use transaction-aware connection"""
        try:
            connection = self._get_connection_for_transaction()
            try:
                return self._delete_with_connection(entity_id, soft_delete, connection)
                
            finally:
                if self._should_return_connection(connection):
                    self._return_connection(connection)
                    
        except Exception as e:
            self._logger.error(f"Failed to delete entity {entity_id}: {e}")
            raise RepositoryError(f"Delete operation failed: {e}")
    
    def execute_query(self, query: str, params: List[Any] = None) -> List[T]:
        """Override execute_query to use transaction-aware connection"""
        if params is None:
            params = []
        
        try:
            connection = self._get_connection_for_transaction()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                cursor.close()
                
                # Convert rows to entities
                entities = []
                for row in rows:
                    try:
                        entity = self._model.get_entity_class().from_row(row)
                        entities.append(entity)
                    except Exception as e:
                        self._logger.warning(f"Failed to convert row to entity: {e}")
                        continue
                
                return entities
                
            finally:
                if self._should_return_connection(connection):
                    self._return_connection(connection)
                    
        except Exception as e:
            self._logger.error(f"Query execution failed: {e}")
            raise RepositoryError(f"Query execution failed: {e}")
    
    def _insert_with_connection(self, entity: T, connection) -> Optional[T]:
        """Insert entity using provided connection"""
        try:
            # Mark as updated for consistency
            entity.mark_updated()
            
            # Convert to database format
            data = entity.to_dict()
            data.pop('id', None)  # Remove ID for insertion
            
            # Build INSERT query
            fields = list(data.keys())
            placeholders = ['?' for _ in fields]
            values = [data[field] for field in fields]
            
            query = f"""
                INSERT INTO {self._model.get_table_name()} 
                ({', '.join(fields)}) 
                VALUES ({', '.join(placeholders)})
            """
            
            cursor = connection.cursor()
            cursor.execute(query, values)
            
            # Get the inserted ID
            entity_id = cursor.lastrowid
            entity.id = entity_id
            
            cursor.close()
            
            self._logger.debug(f"Inserted entity with ID {entity_id}")
            return entity
            
        except Exception as e:
            self._logger.error(f"Insert failed: {e}")
            raise RepositoryError(f"Insert failed: {e}")
    
    def _update_with_connection(self, entity: T, connection) -> Optional[T]:
        """Update entity using provided connection"""
        try:
            # Mark as updated
            entity.mark_updated()
            
            # Convert to database format
            data = entity.to_dict()
            entity_id = data.pop('id')
            
            # Build UPDATE query
            fields = list(data.keys())
            set_clause = [f"{field} = ?" for field in fields]
            values = [data[field] for field in fields]
            values.append(entity_id)
            
            query = f"""
                UPDATE {self._model.get_table_name()} 
                SET {', '.join(set_clause)} 
                WHERE id = ? AND is_deleted = 0
            """
            
            cursor = connection.cursor()
            cursor.execute(query, values)
            rows_affected = cursor.rowcount
            cursor.close()
            
            if rows_affected == 0:
                self._logger.warning(f"No rows updated for entity ID {entity_id}")
                return None
            
            self._logger.debug(f"Updated entity with ID {entity_id}")
            return entity
            
        except Exception as e:
            self._logger.error(f"Update failed: {e}")
            raise RepositoryError(f"Update failed: {e}")
    
    def _delete_with_connection(self, entity_id: EntityId, soft_delete: bool, connection) -> bool:
        """Delete entity using provided connection"""
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                query = f"""
                    UPDATE {self._model.get_table_name()} 
                    SET is_deleted = 1, updated_at = ? 
                    WHERE id = ? AND is_deleted = 0
                """
                values = [datetime.now().isoformat(), entity_id]
            else:
                # Hard delete - remove from database
                query = f"""
                    DELETE FROM {self._model.get_table_name()} 
                    WHERE id = ?
                """
                values = [entity_id]
            
            cursor = connection.cursor()
            cursor.execute(query, values)
            rows_affected = cursor.rowcount
            cursor.close()
            
            success = rows_affected > 0
            delete_type = "soft" if soft_delete else "hard"
            
            if success:
                self._logger.debug(f"Performed {delete_type} delete for entity ID {entity_id}")
            else:
                self._logger.warning(f"No rows affected during {delete_type} delete for entity ID {entity_id}")
            
            return success
            
        except Exception as e:
            self._logger.error(f"Delete failed: {e}")
            raise RepositoryError(f"Delete failed: {e}")


class UnitOfWork:
    """
    Unit of Work pattern implementation for managing multiple repository operations
    
    Provides coordinated transaction management across multiple repositories
    and ensures all operations succeed or fail together.
    """
    
    def __init__(self, 
                 isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                 read_only: bool = False):
        self._transaction_manager = get_transaction_manager()
        self._isolation_level = isolation_level
        self._read_only = read_only
        self._repositories: Dict[str, IRepository] = {}
        self._operations: List[Callable] = []
        self._transaction: Optional[Transaction] = None
        self._logger = logging.getLogger("UnitOfWork")
    
    def register_repository(self, name: str, repository: IRepository) -> None:
        """Register a repository for use within this unit of work"""
        self._repositories[name] = repository
    
    def get_repository(self, name: str) -> Optional[IRepository]:
        """Get a registered repository by name"""
        return self._repositories.get(name)
    
    def add_operation(self, operation: Callable) -> None:
        """Add an operation to be executed within the transaction"""
        self._operations.append(operation)
    
    def __enter__(self) -> 'UnitOfWork':
        """Start the unit of work transaction"""
        try:
            self._transaction = self._transaction_manager.begin_transaction(
                isolation_level=self._isolation_level,
                read_only=self._read_only
            )
            self._logger.debug(f"Started unit of work with transaction {self._transaction.transaction_id}")
            return self
            
        except Exception as e:
            self._logger.error(f"Failed to start unit of work: {e}")
            raise TransactionException(f"Failed to start unit of work: {e}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete the unit of work transaction"""
        if self._transaction and self._transaction.is_active:
            try:
                if exc_type is None:
                    # No exception, commit the transaction
                    self._transaction.commit()
                    self._logger.debug(f"Committed unit of work transaction {self._transaction.transaction_id}")
                else:
                    # Exception occurred, rollback the transaction
                    self._transaction.rollback()
                    self._logger.debug(f"Rolled back unit of work transaction {self._transaction.transaction_id}")
                    
            except Exception as e:
                self._logger.error(f"Error completing unit of work: {e}")
                if self._transaction.is_active:
                    try:
                        self._transaction.rollback()
                    except:
                        pass
                raise TransactionException(f"Failed to complete unit of work: {e}")
    
    def commit(self) -> None:
        """Manually commit the unit of work"""
        if self._transaction and self._transaction.is_active:
            self._transaction.commit()
        else:
            raise TransactionException("No active transaction to commit")
    
    def rollback(self) -> None:
        """Manually rollback the unit of work"""
        if self._transaction and self._transaction.is_active:
            self._transaction.rollback()
        else:
            raise TransactionException("No active transaction to rollback")
    
    def execute_operations(self) -> List[Any]:
        """Execute all registered operations within the transaction"""
        results = []
        
        for i, operation in enumerate(self._operations):
            try:
                result = operation()
                results.append(result)
                self._logger.debug(f"Executed operation {i+1}/{len(self._operations)}")
                
            except Exception as e:
                self._logger.error(f"Operation {i+1} failed: {e}")
                raise TransactionException(f"Operation {i+1} failed: {e}")
        
        return results


# Transaction decorators for repository methods
def transactional(isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                 propagation: TransactionPropagation = TransactionPropagation.REQUIRED,
                 read_only: bool = False):
    """
    Decorator to make repository methods transactional
    
    Args:
        isolation_level: Transaction isolation level
        propagation: Transaction propagation behavior
        read_only: Whether the transaction is read-only
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            transaction_manager = get_transaction_manager()
            
            with transaction_manager.transaction(
                isolation_level=isolation_level,
                propagation=propagation,
                read_only=read_only
            ):
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def requires_transaction(func):
    """
    Decorator to ensure a method is called within an active transaction
    
    Raises TransactionException if no active transaction exists.
    """
    def wrapper(self, *args, **kwargs):
        current_transaction = get_current_transaction()
        if not current_transaction or not current_transaction.is_active:
            raise TransactionException(f"Method {func.__name__} requires an active transaction")
        
        return func(self, *args, **kwargs)
    
    return wrapper 