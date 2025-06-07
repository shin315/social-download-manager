"""
Real-Time Progress Manager for Cross-Tab Communication

This module provides real-time progress tracking capabilities across tabs,
enabling synchronized progress updates, download status coordination, and
efficient cross-tab communication for ongoing operations.

Designed for subtask 16.2 implementation.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass, asdict
from enum import Enum

from .events import get_event_bus, EventType, ComponentEvent


class ProgressStatus(Enum):
    """Progress status enumeration"""
    PENDING = "pending"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressData:
    """Data structure for progress information"""
    operation_id: str
    operation_type: str  # "download", "api_fetch", "upload", etc.
    status: ProgressStatus
    progress_percent: float  # 0.0 to 100.0
    current_value: int
    total_value: int
    speed: str  # Human readable speed like "2.5 MB/s"
    eta: str  # Estimated time remaining like "2:30"
    file_name: str
    file_size: str  # Human readable size like "15.2 MB"
    url: str
    tab_id: str  # Source tab that initiated the operation
    timestamp: datetime
    error_message: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ProgressUpdate:
    """Progress update structure for cross-tab communication"""
    progress_data: ProgressData
    update_type: str  # "progress", "status_change", "completion", "error"
    source_tab: str
    broadcast_timestamp: datetime
    sequence_number: int


class ProgressEventDebouncer:
    """Debouncer for progress events to prevent flooding"""
    
    def __init__(self, debounce_interval: float = 0.1):
        self.debounce_interval = debounce_interval  # 100ms default
        self.last_update_times: Dict[str, float] = {}
        self.pending_updates: Dict[str, ProgressUpdate] = {}
        self.timer = QTimer()
        self.timer.timeout.connect(self._flush_pending_updates)
        self.timer.start(50)  # Check every 50ms
    
    def should_update(self, operation_id: str) -> bool:
        """Check if enough time has passed since last update"""
        current_time = time.time()
        last_time = self.last_update_times.get(operation_id, 0)
        
        if current_time - last_time >= self.debounce_interval:
            self.last_update_times[operation_id] = current_time
            return True
        return False
    
    def queue_update(self, operation_id: str, update: ProgressUpdate):
        """Queue an update for debounced processing"""
        self.pending_updates[operation_id] = update
    
    def _flush_pending_updates(self):
        """Flush pending updates that are ready"""
        current_time = time.time()
        ready_updates = []
        
        for operation_id, update in list(self.pending_updates.items()):
            last_time = self.last_update_times.get(operation_id, 0)
            if current_time - last_time >= self.debounce_interval:
                ready_updates.append((operation_id, update))
                del self.pending_updates[operation_id]
        
        return ready_updates


class RealtimeProgressManager(QObject):
    """
    Real-time progress manager for cross-tab communication.
    
    Coordinates progress updates between tabs using the component bus system,
    provides debounced updates to prevent UI flooding, and maintains progress
    state consistency across the application.
    """
    
    # Signals for progress events
    progress_updated = pyqtSignal(str, ProgressData)  # operation_id, progress_data
    progress_started = pyqtSignal(str, ProgressData)  # operation_id, progress_data
    progress_completed = pyqtSignal(str, ProgressData)  # operation_id, progress_data
    progress_failed = pyqtSignal(str, ProgressData)  # operation_id, progress_data
    progress_cancelled = pyqtSignal(str, ProgressData)  # operation_id, progress_data
    
    def __init__(self, debounce_interval: float = 0.1):
        super().__init__()
        
        # Progress tracking storage
        self.active_operations: Dict[str, ProgressData] = {}
        self.completed_operations: Dict[str, ProgressData] = {}
        self.operation_history: List[ProgressUpdate] = []
        
        # Debouncer for progress updates
        self.debouncer = ProgressEventDebouncer(debounce_interval)
        
        # Sequence counter for ordering updates
        self.sequence_counter = 0
        
        # Event bus integration
        self.event_bus = get_event_bus()
        self._setup_event_subscriptions()
        
        # Cleanup timer for old operations
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_operations)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds
        
        # Cross-tab storage key
        self.storage_key = "realtime_progress_data"
        
        # Tab registration for progress coordination
        self.registered_tabs: Dict[str, QObject] = {}
    
    def _setup_event_subscriptions(self):
        """Setup event bus subscriptions for progress coordination"""
        try:
            # Subscribe to download progress events
            self.event_bus.subscribe(EventType.DOWNLOAD_PROGRESS, self._handle_download_progress_event)
            self.event_bus.subscribe(EventType.DOWNLOAD_STARTED, self._handle_download_started_event)
            self.event_bus.subscribe(EventType.DOWNLOAD_COMPLETED, self._handle_download_completed_event)
            self.event_bus.subscribe(EventType.API_ERROR, self._handle_api_error_event)
            
            # Subscribe to tab events for coordination
            self.event_bus.subscribe(EventType.TAB_ACTIVATED, self._handle_tab_activated_event)
            self.event_bus.subscribe(EventType.TAB_DEACTIVATED, self._handle_tab_deactivated_event)
            
        except Exception as e:
            print(f"Error setting up progress manager event subscriptions: {e}")
    
    def register_tab(self, tab_id: str, tab_instance: QObject):
        """Register a tab for progress updates"""
        self.registered_tabs[tab_id] = tab_instance
        
        # Connect tab-specific signals if available
        if hasattr(tab_instance, 'progress_updated'):
            tab_instance.progress_updated.connect(self._handle_tab_progress_update)
        if hasattr(tab_instance, 'operation_started'):
            tab_instance.operation_started.connect(self._handle_tab_operation_started)
    
    def unregister_tab(self, tab_id: str):
        """Unregister a tab from progress updates"""
        if tab_id in self.registered_tabs:
            tab_instance = self.registered_tabs[tab_id]
            
            # Disconnect signals if connected
            if hasattr(tab_instance, 'progress_updated'):
                try:
                    tab_instance.progress_updated.disconnect(self._handle_tab_progress_update)
                except:
                    pass
            if hasattr(tab_instance, 'operation_started'):
                try:
                    tab_instance.operation_started.disconnect(self._handle_tab_operation_started)
                except:
                    pass
            
            del self.registered_tabs[tab_id]
    
    def start_operation(self, operation_id: str, operation_type: str, tab_id: str, 
                       total_value: int = 100, file_name: str = "", url: str = "",
                       additional_data: Optional[Dict[str, Any]] = None) -> ProgressData:
        """Start tracking a new operation"""
        
        progress_data = ProgressData(
            operation_id=operation_id,
            operation_type=operation_type,
            status=ProgressStatus.STARTING,
            progress_percent=0.0,
            current_value=0,
            total_value=total_value,
            speed="",
            eta="",
            file_name=file_name,
            file_size="",
            url=url,
            tab_id=tab_id,
            timestamp=datetime.now(),
            additional_data=additional_data or {}
        )
        
        self.active_operations[operation_id] = progress_data
        
        # Broadcast start event
        self._broadcast_progress_update(progress_data, "start")
        self.progress_started.emit(operation_id, progress_data)
        
        return progress_data
    
    def update_progress(self, operation_id: str, current_value: int, speed: str = "",
                       eta: str = "", file_size: str = "", status: Optional[ProgressStatus] = None,
                       additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update progress for an active operation"""
        
        if operation_id not in self.active_operations:
            return False
        
        progress_data = self.active_operations[operation_id]
        
        # Update values
        progress_data.current_value = current_value
        progress_data.progress_percent = (current_value / progress_data.total_value) * 100.0 if progress_data.total_value > 0 else 0.0
        progress_data.speed = speed
        progress_data.eta = eta
        progress_data.file_size = file_size
        progress_data.timestamp = datetime.now()
        
        if status:
            progress_data.status = status
        else:
            progress_data.status = ProgressStatus.IN_PROGRESS
        
        if additional_data:
            progress_data.additional_data.update(additional_data)
        
        # Use debouncer for progress updates
        if self.debouncer.should_update(operation_id):
            self._broadcast_progress_update(progress_data, "progress")
            self.progress_updated.emit(operation_id, progress_data)
        else:
            # Queue for later update
            update = ProgressUpdate(
                progress_data=progress_data,
                update_type="progress",
                source_tab=progress_data.tab_id,
                broadcast_timestamp=datetime.now(),
                sequence_number=self._get_next_sequence()
            )
            self.debouncer.queue_update(operation_id, update)
        
        return True
    
    def complete_operation(self, operation_id: str, success: bool = True, 
                          error_message: Optional[str] = None,
                          final_data: Optional[Dict[str, Any]] = None) -> bool:
        """Mark an operation as completed"""
        
        if operation_id not in self.active_operations:
            return False
        
        progress_data = self.active_operations[operation_id]
        
        # Update final status
        if success:
            progress_data.status = ProgressStatus.COMPLETED
            progress_data.progress_percent = 100.0
            progress_data.current_value = progress_data.total_value
        else:
            progress_data.status = ProgressStatus.FAILED
            progress_data.error_message = error_message
        
        progress_data.timestamp = datetime.now()
        
        if final_data:
            progress_data.additional_data.update(final_data)
        
        # Move to completed operations
        self.completed_operations[operation_id] = progress_data
        del self.active_operations[operation_id]
        
        # Broadcast completion
        self._broadcast_progress_update(progress_data, "completion")
        
        if success:
            self.progress_completed.emit(operation_id, progress_data)
        else:
            self.progress_failed.emit(operation_id, progress_data)
        
        return True
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an active operation"""
        
        if operation_id not in self.active_operations:
            return False
        
        progress_data = self.active_operations[operation_id]
        progress_data.status = ProgressStatus.CANCELLED
        progress_data.timestamp = datetime.now()
        
        # Move to completed operations
        self.completed_operations[operation_id] = progress_data
        del self.active_operations[operation_id]
        
        # Broadcast cancellation
        self._broadcast_progress_update(progress_data, "cancellation")
        self.progress_cancelled.emit(operation_id, progress_data)
        
        return True
    
    def get_active_operations(self) -> Dict[str, ProgressData]:
        """Get all currently active operations"""
        return self.active_operations.copy()
    
    def get_operations_for_tab(self, tab_id: str) -> Dict[str, ProgressData]:
        """Get all operations (active and completed) for a specific tab"""
        operations = {}
        
        # Add active operations
        for op_id, progress_data in self.active_operations.items():
            if progress_data.tab_id == tab_id:
                operations[op_id] = progress_data
        
        # Add recent completed operations (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        for op_id, progress_data in self.completed_operations.items():
            if progress_data.tab_id == tab_id and progress_data.timestamp > cutoff_time:
                operations[op_id] = progress_data
        
        return operations
    
    def _broadcast_progress_update(self, progress_data: ProgressData, update_type: str):
        """Broadcast progress update to all registered tabs"""
        
        update = ProgressUpdate(
            progress_data=progress_data,
            update_type=update_type,
            source_tab=progress_data.tab_id,
            broadcast_timestamp=datetime.now(),
            sequence_number=self._get_next_sequence()
        )
        
        # Add to history
        self.operation_history.append(update)
        
        # Broadcast via event bus
        try:
            event_data = {
                'operation_id': progress_data.operation_id,
                'operation_type': progress_data.operation_type,
                'status': progress_data.status.value,
                'progress_percent': progress_data.progress_percent,
                'current_value': progress_data.current_value,
                'total_value': progress_data.total_value,
                'speed': progress_data.speed,
                'eta': progress_data.eta,
                'file_name': progress_data.file_name,
                'file_size': progress_data.file_size,
                'url': progress_data.url,
                'source_tab': progress_data.tab_id,
                'update_type': update_type,
                'timestamp': progress_data.timestamp.isoformat(),
                'error_message': progress_data.error_message,
                'additional_data': progress_data.additional_data
            }
            
            # Create component event
            event = ComponentEvent(
                event_type=EventType.PROGRESS_UPDATE,
                source_component="realtime_progress_manager",
                data=event_data
            )
            
            self.event_bus.emit_event(
                event_type=EventType.PROGRESS_UPDATE,
                source_component="realtime_progress_manager",
                data=event_data
            )
            
        except Exception as e:
            print(f"Error broadcasting progress update: {e}")
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number for ordering updates"""
        self.sequence_counter += 1
        return self.sequence_counter
    
    def _cleanup_old_operations(self):
        """Clean up old completed operations"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Remove old completed operations
        old_operations = [
            op_id for op_id, progress_data in self.completed_operations.items()
            if progress_data.timestamp < cutoff_time
        ]
        
        for op_id in old_operations:
            del self.completed_operations[op_id]
        
        # Limit operation history size
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-500:]  # Keep latest 500
    
    # Event handlers
    def _handle_download_progress_event(self, event: ComponentEvent):
        """Handle download progress events from tabs"""
        try:
            data = event.data
            operation_id = data.get('url', '') or data.get('operation_id', '')
            
            if operation_id and operation_id in self.active_operations:
                self.update_progress(
                    operation_id=operation_id,
                    current_value=data.get('progress', 0),
                    speed=data.get('speed', ''),
                    eta=data.get('eta', ''),
                    additional_data={'download_data': data}
                )
        except Exception as e:
            print(f"Error handling download progress event: {e}")
    
    def _handle_download_started_event(self, event: ComponentEvent):
        """Handle download started events"""
        try:
            data = event.data
            operation_id = data.get('url', '')
            file_name = data.get('title', '') or data.get('file_name', '')
            
            if operation_id:
                self.start_operation(
                    operation_id=operation_id,
                    operation_type="download",
                    tab_id=data.get('source_tab', 'unknown'),
                    file_name=file_name,
                    url=operation_id,
                    additional_data={'download_data': data}
                )
        except Exception as e:
            print(f"Error handling download started event: {e}")
    
    def _handle_download_completed_event(self, event: ComponentEvent):
        """Handle download completed events"""
        try:
            data = event.data
            operation_id = data.get('url', '')
            success = data.get('success', False)
            error_message = data.get('error_message')
            
            if operation_id:
                self.complete_operation(
                    operation_id=operation_id,
                    success=success,
                    error_message=error_message,
                    final_data={'completion_data': data}
                )
        except Exception as e:
            print(f"Error handling download completed event: {e}")
    
    def _handle_api_error_event(self, event: ComponentEvent):
        """Handle API error events"""
        try:
            data = event.data
            operation_id = data.get('url', '')
            error_message = data.get('error_message', 'API Error')
            
            if operation_id and operation_id in self.active_operations:
                self.complete_operation(
                    operation_id=operation_id,
                    success=False,
                    error_message=error_message,
                    final_data={'error_data': data}
                )
        except Exception as e:
            print(f"Error handling API error event: {e}")
    
    def _handle_tab_activated_event(self, event: ComponentEvent):
        """Handle tab activation events"""
        # Could be used for tab-specific progress coordination
        pass
    
    def _handle_tab_deactivated_event(self, event: ComponentEvent):
        """Handle tab deactivation events"""
        # Could be used for saving progress state
        pass
    
    def _handle_tab_progress_update(self, operation_id: str, progress_data: Dict[str, Any]):
        """Handle progress updates from registered tabs"""
        try:
            self.update_progress(
                operation_id=operation_id,
                current_value=progress_data.get('current_value', 0),
                speed=progress_data.get('speed', ''),
                eta=progress_data.get('eta', ''),
                file_size=progress_data.get('file_size', ''),
                additional_data=progress_data
            )
        except Exception as e:
            print(f"Error handling tab progress update: {e}")
    
    def _handle_tab_operation_started(self, operation_id: str, operation_data: Dict[str, Any]):
        """Handle operation started events from registered tabs"""
        try:
            self.start_operation(
                operation_id=operation_id,
                operation_type=operation_data.get('operation_type', 'unknown'),
                tab_id=operation_data.get('tab_id', 'unknown'),
                total_value=operation_data.get('total_value', 100),
                file_name=operation_data.get('file_name', ''),
                url=operation_data.get('url', ''),
                additional_data=operation_data
            )
        except Exception as e:
            print(f"Error handling tab operation started: {e}")


# Global instance for easy access
realtime_progress_manager = RealtimeProgressManager() 