"""
Database layer for Social Download Manager v2.0

Provides database connection management, connection pooling, and database utilities.
"""

from .connection import (
    ConnectionState, ConnectionConfig, ConnectionStats,
    DatabaseError, ConnectionPoolError, ConnectionTimeoutError,
    IConnectionManager, SQLiteConnectionManager,
    get_connection_manager, initialize_database, shutdown_database,
    get_connection, return_connection,
    database_connection, database_transaction
)

from .transactions import (
    # Enums and types
    TransactionIsolationLevel, TransactionPropagation, TransactionStatus,
    
    # Exceptions
    TransactionException, DeadlockException, TransactionTimeoutException,
    InvalidTransactionStateException,
    
    # Core classes
    TransactionInfo, TransactionStatistics,
    ITransactionManager, Transaction, TransactionManager,
    
    # Global functions
    get_transaction_manager, initialize_transaction_manager,
    transaction, get_current_transaction
) 