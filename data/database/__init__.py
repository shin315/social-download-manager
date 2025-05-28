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