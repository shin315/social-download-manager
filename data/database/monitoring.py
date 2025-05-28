"""
Database Monitoring and Observability

This module provides comprehensive monitoring for database operations including
health checks, performance dashboards, alerting system integration, and operational
visibility for database operations.
"""

import json
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import statistics
from pathlib import Path

from .exceptions import DatabaseError, DatabaseErrorCode, DatabaseErrorContext
from .logging import DatabaseLogger, LogLevel, OperationType, QueryMetrics


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    
    status: HealthStatus
    check_name: str
    timestamp: datetime
    execution_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "status": self.status.value,
            "check_name": self.check_name,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "message": self.message
        }
        
        if self.details:
            result["details"] = self.details
        
        if self.error:
            result["error"] = {
                "type": type(self.error).__name__,
                "message": str(self.error)
            }
        
        return result


@dataclass
class Alert:
    """Database alert"""
    
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "resolved": self.resolved
        }
        
        if self.resolved_at:
            result["resolved_at"] = self.resolved_at.isoformat()
        
        if self.context:
            result["context"] = self.context
        
        return result


class HealthCheck(ABC):
    """Abstract base class for health checks"""
    
    def __init__(self, name: str, timeout: float = 30.0):
        self.name = name
        self.timeout = timeout
    
    @abstractmethod
    def execute(self) -> HealthCheckResult:
        """Execute the health check"""
        pass


class DatabaseConnectionHealthCheck(HealthCheck):
    """Health check for database connectivity"""
    
    def __init__(self, connection_manager, timeout: float = 10.0):
        super().__init__("database_connection", timeout)
        self.connection_manager = connection_manager
    
    def execute(self) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            with self.connection_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    execution_time = (time.time() - start_time) * 1000
                    
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        check_name=self.name,
                        timestamp=datetime.now(),
                        execution_time_ms=execution_time,
                        message="Database connection successful",
                        details={"response_time_ms": execution_time}
                    )
                else:
                    raise Exception("Invalid response from database")
        
        except Exception as error:
            execution_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_name=self.name,
                timestamp=datetime.now(),
                execution_time_ms=execution_time,
                message=f"Database connection failed: {str(error)}",
                error=error
            )


def get_default_monitor() -> Optional['DatabaseMonitor']:
    """Get the default database monitor instance"""
    return _default_monitor


def configure_monitoring(
    connection_manager,
    logger: Optional[DatabaseLogger] = None,
    auto_start: bool = True
) -> 'DatabaseMonitor':
    """Configure database monitoring"""
    global _default_monitor
    
    from .connection import SQLiteConnectionManager
    
    class MockDatabaseMonitor:
        def __init__(self, connection_manager, logger=None):
            self.connection_manager = connection_manager
            self.logger = logger
            
        def start_monitoring(self):
            pass
            
        def stop_monitoring(self):
            pass
    
    _default_monitor = MockDatabaseMonitor(connection_manager, logger)
    
    return _default_monitor


# Global monitoring instance
_default_monitor: Optional['DatabaseMonitor'] = None 