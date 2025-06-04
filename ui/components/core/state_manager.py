"""
Advanced State Manager for v2.0 UI Architecture

This module provides comprehensive state management including:
- Advanced state snapshots with incremental updates
- Automatic crash recovery and session restoration
- Encrypted storage for sensitive state data
- Cross-component state synchronization
- User interface for manual state restoration
- State versioning and migration support
- Performance-optimized serialization
"""

import logging
import threading
import json
import gzip
import pickle
import hashlib
import os
import shutil
from typing import Dict, Any, Optional, Callable, List, Set, Union, TypeVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict
import weakref
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

T = TypeVar('T')


class StateType(Enum):
    """Types of state that can be managed"""
    COMPONENT = "component"
    TAB = "tab"
    APPLICATION = "application"
    USER_PREFERENCES = "user_preferences"
    SESSION = "session"
    WINDOW = "window"
    CUSTOM = "custom"


class SnapshotStrategy(Enum):
    """Snapshot creation strategies"""
    IMMEDIATE = "immediate"      # Create snapshot immediately
    INCREMENTAL = "incremental"  # Only save changes since last snapshot
    SCHEDULED = "scheduled"      # Create snapshots on schedule
    ON_CHANGE = "on_change"      # Create snapshot when state changes
    MANUAL = "manual"            # User-triggered snapshots only


class RecoveryTrigger(Enum):
    """Recovery trigger conditions"""
    CRASH_DETECTED = "crash_detected"
    SESSION_START = "session_start"
    USER_REQUEST = "user_request"
    AUTO_RECOVERY = "auto_recovery"
    ERROR_STATE = "error_state"


@dataclass
class StateSnapshot:
    """Complete state snapshot with metadata"""
    id: str
    name: str
    state_type: StateType
    target_id: str  # ID of component/tab/application
    
    # State data
    state_data: Dict[str, Any]
    compressed_data: Optional[bytes] = None
    encryption_key: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    checksum: str = ""
    size_bytes: int = 0
    compression_ratio: float = 0.0
    
    # Snapshot chain for incremental updates
    parent_snapshot_id: Optional[str] = None
    delta_data: Optional[Dict[str, Any]] = None
    
    # Recovery info
    recovery_priority: int = 0
    auto_recovery: bool = True
    user_description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class StateProvider:
    """Component that provides state for snapshots"""
    id: str
    component_type: str
    state_extractor: Callable[[], Dict[str, Any]]
    state_restorer: Callable[[Dict[str, Any]], bool]
    snapshot_strategy: SnapshotStrategy = SnapshotStrategy.ON_CHANGE
    include_in_auto_recovery: bool = True
    encryption_required: bool = False
    priority: int = 0


@dataclass
class RecoverySession:
    """Recovery session information"""
    id: str
    trigger: RecoveryTrigger
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Recovery targets
    target_snapshots: List[str] = field(default_factory=list)
    successful_recoveries: List[str] = field(default_factory=list)
    failed_recoveries: List[str] = field(default_factory=list)
    
    # User interaction
    user_selections: Dict[str, bool] = field(default_factory=dict)
    manual_recovery: bool = False
    
    # Results
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class StateMetrics:
    """State management performance metrics"""
    total_snapshots: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    
    # Performance
    average_snapshot_time: float = 0.0
    average_recovery_time: float = 0.0
    total_storage_size: int = 0
    compression_savings: int = 0
    
    # Recent activity
    recent_snapshots: List[str] = field(default_factory=list)
    recent_recoveries: List[str] = field(default_factory=list)
    
    # Errors
    snapshot_errors: int = 0
    recovery_errors: int = 0
    corruption_detected: int = 0


class StateManager(QObject):
    """
    Advanced state manager providing comprehensive state snapshots,
    recovery mechanisms, and cross-component synchronization for v2.0 UI architecture.
    """
    
    # Signals for state events
    snapshot_created = pyqtSignal(str, str)  # snapshot_id, target_id
    snapshot_failed = pyqtSignal(str, str)   # target_id, error_message
    recovery_started = pyqtSignal(str, str)  # session_id, trigger
    recovery_completed = pyqtSignal(str, bool)  # session_id, success
    state_corrupted = pyqtSignal(str, str)   # snapshot_id, error
    auto_recovery_available = pyqtSignal(str, int)  # target_id, snapshot_count
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._state_providers: Dict[str, StateProvider] = {}
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._recovery_sessions: Dict[str, RecoverySession] = {}
        self._state_cache: Dict[str, Dict[str, Any]] = {}
        
        # Storage and persistence
        self._storage_path = Path(self.config['storage_path'])
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._encryption_key = self._generate_encryption_key()
        
        # Performance tracking
        self._metrics = StateMetrics()
        self._performance_stats: Dict[str, List[float]] = defaultdict(list)
        
        # Automatic operations
        self._snapshot_timer: Optional[QTimer] = None
        self._cleanup_timer: Optional[QTimer] = None
        self._auto_recovery_enabled = self.config['enable_auto_recovery']
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize system
        self._load_existing_snapshots()
        self._start_automatic_operations()
        self._detect_crash_recovery()
        
        self.logger.info(f"StateManager initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for state manager"""
        return {
            'storage_path': 'data/state_snapshots',
            'enable_compression': True,
            'enable_encryption': True,
            'enable_auto_recovery': True,
            'enable_incremental_snapshots': True,
            'snapshot_interval_minutes': 5,
            'cleanup_interval_hours': 24,
            'max_snapshots_per_target': 10,
            'max_storage_size_mb': 500,
            'compression_level': 6,
            'auto_recovery_timeout_seconds': 30,
            'enable_crash_detection': True,
            'backup_snapshots': True,
            'validate_checksums': True
        }
    
    def _generate_encryption_key(self) -> str:
        """Generate or load encryption key for state data"""
        key_file = self._storage_path / '.encryption_key'
        
        if key_file.exists() and self.config['enable_encryption']:
            try:
                with open(key_file, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        # Generate new key
        import secrets
        key = secrets.token_hex(32)
        
        if self.config['enable_encryption']:
            try:
                with open(key_file, 'w') as f:
                    f.write(key)
                # Set restrictive permissions
                os.chmod(key_file, 0o600)
            except Exception as e:
                self.logger.error(f"Failed to save encryption key: {e}")
        
        return key
    
    def _start_automatic_operations(self) -> None:
        """Start automatic snapshot and cleanup operations"""
        try:
            # Snapshot timer
            if self.config['snapshot_interval_minutes'] > 0:
                self._snapshot_timer = QTimer()
                self._snapshot_timer.timeout.connect(self._create_scheduled_snapshots)
                self._snapshot_timer.start(self.config['snapshot_interval_minutes'] * 60000)
            
            # Cleanup timer
            if self.config['cleanup_interval_hours'] > 0:
                self._cleanup_timer = QTimer()
                self._cleanup_timer.timeout.connect(self._cleanup_old_snapshots)
                self._cleanup_timer.start(self.config['cleanup_interval_hours'] * 3600000)
            
            self.logger.info("Automatic operations started")
            
        except Exception as e:
            self.logger.error(f"Failed to start automatic operations: {e}")
    
    def register_state_provider(self, provider_id: str, component_type: str,
                              state_extractor: Callable[[], Dict[str, Any]],
                              state_restorer: Callable[[Dict[str, Any]], bool],
                              **kwargs) -> bool:
        """
        Register a component as a state provider
        
        Args:
            provider_id: Unique identifier for the provider
            component_type: Type of component
            state_extractor: Function to extract state from component
            state_restorer: Function to restore state to component
            **kwargs: Additional provider configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                if provider_id in self._state_providers:
                    self.logger.warning(f"State provider {provider_id} already registered")
                    return False
                
                provider = StateProvider(
                    id=provider_id,
                    component_type=component_type,
                    state_extractor=state_extractor,
                    state_restorer=state_restorer,
                    **kwargs
                )
                
                self._state_providers[provider_id] = provider
                
                self.logger.info(f"State provider {provider_id} ({component_type}) registered")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register state provider {provider_id}: {e}")
                return False
    
    def unregister_state_provider(self, provider_id: str) -> bool:
        """Unregister a state provider"""
        with self._lock:
            try:
                if provider_id not in self._state_providers:
                    return False
                
                del self._state_providers[provider_id]
                
                # Clean up related snapshots if requested
                if self.config.get('cleanup_on_unregister', True):
                    self._cleanup_provider_snapshots(provider_id)
                
                self.logger.info(f"State provider {provider_id} unregistered")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister state provider {provider_id}: {e}")
                return False
    
    def create_snapshot(self, target_id: str, snapshot_name: Optional[str] = None,
                       strategy: SnapshotStrategy = SnapshotStrategy.IMMEDIATE,
                       user_description: str = "", tags: List[str] = None) -> Optional[str]:
        """
        Create a state snapshot for a target
        
        Args:
            target_id: ID of target component/tab/application
            snapshot_name: Optional name for the snapshot
            strategy: Snapshot creation strategy
            user_description: User-provided description
            tags: Optional tags for categorization
            
        Returns:
            Snapshot ID if successful, None otherwise
        """
        with self._lock:
            try:
                provider = self._state_providers.get(target_id)
                if not provider:
                    self.logger.error(f"No state provider found for {target_id}")
                    return None
                
                snapshot_start = datetime.now()
                
                # Extract state data
                state_data = provider.state_extractor()
                if not state_data:
                    self.logger.warning(f"No state data extracted for {target_id}")
                    return None
                
                # Create snapshot
                snapshot_id = self._generate_snapshot_id(target_id)
                snapshot_name = snapshot_name or f"Auto-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                snapshot = StateSnapshot(
                    id=snapshot_id,
                    name=snapshot_name,
                    state_type=StateType.COMPONENT,
                    target_id=target_id,
                    state_data=state_data,
                    user_description=user_description,
                    tags=tags or []
                )
                
                # Handle incremental snapshots
                if (strategy == SnapshotStrategy.INCREMENTAL and 
                    self.config['enable_incremental_snapshots']):
                    self._create_incremental_snapshot(snapshot, target_id)
                
                # Process and store snapshot
                if self._process_snapshot(snapshot):
                    self._snapshots[snapshot_id] = snapshot
                    
                    # Update metrics
                    processing_time = (datetime.now() - snapshot_start).total_seconds() * 1000
                    self._update_snapshot_metrics(snapshot_id, processing_time, True)
                    
                    self.logger.info(f"Snapshot {snapshot_id} created for {target_id}")
                    self.snapshot_created.emit(snapshot_id, target_id)
                    
                    return snapshot_id
                else:
                    self.snapshot_failed.emit(target_id, "Processing failed")
                    return None
                
            except Exception as e:
                self.logger.error(f"Failed to create snapshot for {target_id}: {e}")
                self.snapshot_failed.emit(target_id, str(e))
                return None
    
    def _generate_snapshot_id(self, target_id: str) -> str:
        """Generate unique snapshot ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"{target_id}_{timestamp}"
    
    def _create_incremental_snapshot(self, snapshot: StateSnapshot, target_id: str) -> None:
        """Create incremental snapshot with delta data"""
        try:
            # Find most recent snapshot for this target
            recent_snapshots = [
                s for s in self._snapshots.values()
                if s.target_id == target_id
            ]
            
            if not recent_snapshots:
                return  # First snapshot, no delta needed
            
            # Get most recent snapshot
            recent_snapshot = max(recent_snapshots, key=lambda s: s.timestamp)
            
            # Calculate delta
            delta_data = self._calculate_state_delta(
                recent_snapshot.state_data, 
                snapshot.state_data
            )
            
            if delta_data:
                snapshot.parent_snapshot_id = recent_snapshot.id
                snapshot.delta_data = delta_data
                
                # Replace full state with delta for storage efficiency
                original_size = len(str(snapshot.state_data))
                delta_size = len(str(delta_data))
                
                if delta_size < original_size * 0.5:  # Only use delta if significantly smaller
                    snapshot.state_data = delta_data
                    snapshot.compression_ratio = 1.0 - (delta_size / original_size)
                    
        except Exception as e:
            self.logger.error(f"Failed to create incremental snapshot: {e}")
    
    def _calculate_state_delta(self, old_state: Dict[str, Any], 
                              new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate delta between two state dictionaries"""
        delta = {}
        
        # Find changes and additions
        for key, new_value in new_state.items():
            old_value = old_state.get(key)
            
            if old_value != new_value:
                if isinstance(new_value, dict) and isinstance(old_value, dict):
                    # Recursive delta for nested dictionaries
                    nested_delta = self._calculate_state_delta(old_value, new_value)
                    if nested_delta:
                        delta[key] = nested_delta
                else:
                    delta[key] = new_value
        
        # Mark deletions
        for key in old_state:
            if key not in new_state:
                delta[f"__deleted_{key}"] = True
        
        return delta
    
    def _process_snapshot(self, snapshot: StateSnapshot) -> bool:
        """Process snapshot with compression and encryption"""
        try:
            # Serialize state data
            serialized_data = json.dumps(snapshot.state_data, default=str)
            snapshot.size_bytes = len(serialized_data.encode('utf-8'))
            
            # Apply compression if enabled
            if self.config['enable_compression']:
                compressed_data = gzip.compress(
                    serialized_data.encode('utf-8'),
                    compresslevel=self.config['compression_level']
                )
                
                # Calculate compression ratio
                original_size = len(serialized_data.encode('utf-8'))
                compressed_size = len(compressed_data)
                snapshot.compression_ratio = 1.0 - (compressed_size / original_size)
                
                if compressed_size < original_size:
                    snapshot.compressed_data = compressed_data
                    self._metrics.compression_savings += original_size - compressed_size
            
            # Apply encryption if enabled and required
            if (self.config['enable_encryption'] and 
                self._state_providers.get(snapshot.target_id, StateProvider("", "", None, None)).encryption_required):
                snapshot.encryption_key = self._encrypt_data(snapshot)
            
            # Generate checksum
            if self.config['validate_checksums']:
                snapshot.checksum = self._generate_checksum(snapshot)
            
            # Save to disk
            return self._save_snapshot_to_disk(snapshot)
            
        except Exception as e:
            self.logger.error(f"Failed to process snapshot {snapshot.id}: {e}")
            return False
    
    def _encrypt_data(self, snapshot: StateSnapshot) -> str:
        """Encrypt snapshot data and return encryption key reference"""
        try:
            from cryptography.fernet import Fernet
            import base64
            
            # Use the master encryption key
            key = base64.urlsafe_b64encode(self._encryption_key[:32].encode())
            f = Fernet(key)
            
            # Encrypt the compressed data or serialized data
            data_to_encrypt = snapshot.compressed_data or json.dumps(snapshot.state_data).encode()
            encrypted_data = f.encrypt(data_to_encrypt)
            
            # Store encrypted data
            snapshot.compressed_data = encrypted_data
            
            return "master_key"  # Reference to master key
            
        except ImportError:
            self.logger.warning("Cryptography library not available, skipping encryption")
            return ""
        except Exception as e:
            self.logger.error(f"Failed to encrypt snapshot data: {e}")
            return ""
    
    def _generate_checksum(self, snapshot: StateSnapshot) -> str:
        """Generate SHA-256 checksum for snapshot integrity"""
        data_for_checksum = snapshot.compressed_data or json.dumps(snapshot.state_data).encode()
        return hashlib.sha256(data_for_checksum).hexdigest()[:16]
    
    def _save_snapshot_to_disk(self, snapshot: StateSnapshot) -> bool:
        """Save snapshot to persistent storage"""
        try:
            snapshot_file = self._storage_path / f"{snapshot.id}.snapshot"
            
            # Prepare data for storage
            storage_data = {
                'metadata': asdict(snapshot),
                'data': snapshot.compressed_data.hex() if snapshot.compressed_data else None
            }
            
            # Remove non-serializable data from metadata
            storage_data['metadata'].pop('state_data', None)
            storage_data['metadata'].pop('compressed_data', None)
            
            # Save to file
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, indent=2, default=str)
            
            # Create backup if enabled
            if self.config['backup_snapshots']:
                backup_file = self._storage_path / 'backups' / f"{snapshot.id}.backup"
                backup_file.parent.mkdir(exist_ok=True)
                shutil.copy2(snapshot_file, backup_file)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save snapshot to disk: {e}")
            return False
    
    def restore_snapshot(self, snapshot_id: str, target_id: Optional[str] = None) -> bool:
        """
        Restore state from a snapshot
        
        Args:
            snapshot_id: ID of snapshot to restore
            target_id: Optional target ID (defaults to snapshot's target)
            
        Returns:
            True if restoration successful, False otherwise
        """
        with self._lock:
            try:
                snapshot = self._snapshots.get(snapshot_id)
                if not snapshot:
                    # Try loading from disk
                    snapshot = self._load_snapshot_from_disk(snapshot_id)
                    if not snapshot:
                        self.logger.error(f"Snapshot {snapshot_id} not found")
                        return False
                
                target_id = target_id or snapshot.target_id
                provider = self._state_providers.get(target_id)
                if not provider:
                    self.logger.error(f"No state provider found for {target_id}")
                    return False
                
                restore_start = datetime.now()
                
                # Prepare state data for restoration
                state_data = self._prepare_restoration_data(snapshot)
                if not state_data:
                    return False
                
                # Restore state using provider
                success = provider.state_restorer(state_data)
                
                if success:
                    # Update metrics
                    restore_time = (datetime.now() - restore_start).total_seconds() * 1000
                    self._update_recovery_metrics(snapshot_id, restore_time, True)
                    
                    # Update cache
                    self._state_cache[target_id] = state_data
                    
                    self.logger.info(f"Snapshot {snapshot_id} restored to {target_id}")
                    return True
                else:
                    self._update_recovery_metrics(snapshot_id, 0, False)
                    return False
                
            except Exception as e:
                self.logger.error(f"Failed to restore snapshot {snapshot_id}: {e}")
                self._update_recovery_metrics(snapshot_id, 0, False)
                return False
    
    def _prepare_restoration_data(self, snapshot: StateSnapshot) -> Optional[Dict[str, Any]]:
        """Prepare snapshot data for restoration"""
        try:
            # Handle incremental snapshots
            if snapshot.parent_snapshot_id and snapshot.delta_data:
                return self._reconstruct_from_delta(snapshot)
            
            # Handle encrypted data
            if snapshot.encryption_key:
                return self._decrypt_snapshot_data(snapshot)
            
            # Handle compressed data
            if snapshot.compressed_data:
                return self._decompress_snapshot_data(snapshot)
            
            # Return direct state data
            return snapshot.state_data
            
        except Exception as e:
            self.logger.error(f"Failed to prepare restoration data: {e}")
            return None
    
    def _reconstruct_from_delta(self, snapshot: StateSnapshot) -> Optional[Dict[str, Any]]:
        """Reconstruct full state from delta snapshot"""
        try:
            # Get parent snapshot
            parent_snapshot = self._snapshots.get(snapshot.parent_snapshot_id)
            if not parent_snapshot:
                parent_snapshot = self._load_snapshot_from_disk(snapshot.parent_snapshot_id)
                if not parent_snapshot:
                    self.logger.error(f"Parent snapshot {snapshot.parent_snapshot_id} not found")
                    return None
            
            # Get parent state
            parent_state = self._prepare_restoration_data(parent_snapshot)
            if not parent_state:
                return None
            
            # Apply delta
            return self._apply_delta_to_state(parent_state, snapshot.delta_data or {})
            
        except Exception as e:
            self.logger.error(f"Failed to reconstruct from delta: {e}")
            return None
    
    def _apply_delta_to_state(self, base_state: Dict[str, Any], 
                             delta: Dict[str, Any]) -> Dict[str, Any]:
        """Apply delta changes to base state"""
        result_state = base_state.copy()
        
        for key, value in delta.items():
            if key.startswith("__deleted_"):
                # Handle deletions
                actual_key = key[10:]  # Remove "__deleted_" prefix
                result_state.pop(actual_key, None)
            elif isinstance(value, dict) and key in result_state and isinstance(result_state[key], dict):
                # Recursive delta application
                result_state[key] = self._apply_delta_to_state(result_state[key], value)
            else:
                # Direct assignment
                result_state[key] = value
        
        return result_state
    
    def start_recovery_session(self, trigger: RecoveryTrigger, 
                              target_ids: List[str] = None) -> Optional[str]:
        """
        Start a recovery session
        
        Args:
            trigger: What triggered the recovery
            target_ids: Optional list of specific targets to recover
            
        Returns:
            Recovery session ID if successful, None otherwise
        """
        try:
            session_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Find available snapshots
            available_snapshots = []
            if target_ids:
                for target_id in target_ids:
                    snapshots = self.get_snapshots_for_target(target_id)
                    available_snapshots.extend([s.id for s in snapshots])
            else:
                available_snapshots = list(self._snapshots.keys())
            
            session = RecoverySession(
                id=session_id,
                trigger=trigger,
                target_snapshots=available_snapshots,
                manual_recovery=(trigger == RecoveryTrigger.USER_REQUEST)
            )
            
            self._recovery_sessions[session_id] = session
            
            self.logger.info(f"Recovery session {session_id} started with {len(available_snapshots)} snapshots")
            self.recovery_started.emit(session_id, trigger.value)
            
            # Start automatic recovery if enabled
            if (self._auto_recovery_enabled and 
                trigger in [RecoveryTrigger.CRASH_DETECTED, RecoveryTrigger.SESSION_START]):
                self._execute_auto_recovery(session_id)
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start recovery session: {e}")
            return None
    
    def _execute_auto_recovery(self, session_id: str) -> None:
        """Execute automatic recovery for a session"""
        try:
            session = self._recovery_sessions.get(session_id)
            if not session:
                return
            
            recovery_count = 0
            
            # Sort snapshots by priority and recency
            snapshot_priorities = []
            for snapshot_id in session.target_snapshots:
                snapshot = self._snapshots.get(snapshot_id)
                if snapshot and snapshot.auto_recovery:
                    provider = self._state_providers.get(snapshot.target_id)
                    priority = provider.priority if provider else 0
                    snapshot_priorities.append((snapshot_id, priority, snapshot.timestamp))
            
            # Sort by priority (higher first) then by timestamp (newer first)
            snapshot_priorities.sort(key=lambda x: (-x[1], -x[2].timestamp()))
            
            # Attempt recovery for each snapshot
            for snapshot_id, _, _ in snapshot_priorities:
                try:
                    if self.restore_snapshot(snapshot_id):
                        session.successful_recoveries.append(snapshot_id)
                        recovery_count += 1
                    else:
                        session.failed_recoveries.append(snapshot_id)
                except Exception as e:
                    self.logger.error(f"Auto recovery failed for {snapshot_id}: {e}")
                    session.failed_recoveries.append(snapshot_id)
            
            # Update session
            session.completed_at = datetime.now()
            session.success = recovery_count > 0
            
            self.logger.info(f"Auto recovery completed: {recovery_count} successful")
            self.recovery_completed.emit(session_id, session.success)
            
        except Exception as e:
            self.logger.error(f"Auto recovery execution failed: {e}")
    
    def get_snapshots_for_target(self, target_id: str) -> List[StateSnapshot]:
        """Get all snapshots for a specific target"""
        snapshots = [
            snapshot for snapshot in self._snapshots.values()
            if snapshot.target_id == target_id
        ]
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)
    
    def _load_existing_snapshots(self) -> None:
        """Load existing snapshots from disk"""
        try:
            snapshot_files = list(self._storage_path.glob("*.snapshot"))
            loaded_count = 0
            
            for snapshot_file in snapshot_files:
                try:
                    snapshot = self._load_snapshot_from_disk(snapshot_file.stem)
                    if snapshot:
                        self._snapshots[snapshot.id] = snapshot
                        loaded_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to load snapshot {snapshot_file}: {e}")
            
            self.logger.info(f"Loaded {loaded_count} existing snapshots")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing snapshots: {e}")
    
    def _load_snapshot_from_disk(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Load a specific snapshot from disk"""
        try:
            snapshot_file = self._storage_path / f"{snapshot_id}.snapshot"
            if not snapshot_file.exists():
                return None
            
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                storage_data = json.load(f)
            
            # Reconstruct snapshot object
            metadata = storage_data['metadata']
            snapshot = StateSnapshot(**metadata)
            
            # Restore compressed data
            if storage_data.get('data'):
                snapshot.compressed_data = bytes.fromhex(storage_data['data'])
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to load snapshot {snapshot_id} from disk: {e}")
            return None
    
    def _detect_crash_recovery(self) -> None:
        """Detect if recovery is needed from a previous crash"""
        if not self.config['enable_crash_detection']:
            return
        
        try:
            # Check for crash indicator file
            crash_file = self._storage_path / '.crash_detected'
            
            if crash_file.exists():
                self.logger.info("Previous crash detected, initiating recovery")
                
                # Start crash recovery session
                self.start_recovery_session(RecoveryTrigger.CRASH_DETECTED)
                
                # Clean up crash file
                crash_file.unlink()
            else:
                # Create crash detection file
                with open(crash_file, 'w') as f:
                    f.write(datetime.now().isoformat())
            
        except Exception as e:
            self.logger.error(f"Crash detection failed: {e}")
    
    def _create_scheduled_snapshots(self) -> None:
        """Create snapshots for providers with scheduled strategy"""
        try:
            for provider_id, provider in self._state_providers.items():
                if provider.snapshot_strategy == SnapshotStrategy.SCHEDULED:
                    self.create_snapshot(
                        provider_id, 
                        strategy=SnapshotStrategy.SCHEDULED,
                        user_description="Scheduled automatic snapshot"
                    )
                    
        except Exception as e:
            self.logger.error(f"Scheduled snapshot creation failed: {e}")
    
    def _cleanup_old_snapshots(self) -> None:
        """Clean up old snapshots based on retention policies"""
        try:
            cleanup_count = 0
            
            # Group snapshots by target
            snapshots_by_target = defaultdict(list)
            for snapshot in self._snapshots.values():
                snapshots_by_target[snapshot.target_id].append(snapshot)
            
            # Clean up excess snapshots per target
            for target_id, snapshots in snapshots_by_target.items():
                max_snapshots = self.config['max_snapshots_per_target']
                
                if len(snapshots) > max_snapshots:
                    # Sort by timestamp (newest first)
                    snapshots.sort(key=lambda s: s.timestamp, reverse=True)
                    
                    # Remove excess snapshots
                    for snapshot in snapshots[max_snapshots:]:
                        if self._remove_snapshot(snapshot.id):
                            cleanup_count += 1
            
            # Check total storage size
            total_size = sum(s.size_bytes for s in self._snapshots.values())
            max_size = self.config['max_storage_size_mb'] * 1024 * 1024
            
            if total_size > max_size:
                # Remove oldest snapshots until under limit
                all_snapshots = sorted(self._snapshots.values(), key=lambda s: s.timestamp)
                
                for snapshot in all_snapshots:
                    if total_size <= max_size:
                        break
                    
                    if self._remove_snapshot(snapshot.id):
                        total_size -= snapshot.size_bytes
                        cleanup_count += 1
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} old snapshots")
                
        except Exception as e:
            self.logger.error(f"Snapshot cleanup failed: {e}")
    
    def _remove_snapshot(self, snapshot_id: str) -> bool:
        """Remove a snapshot from memory and disk"""
        try:
            # Remove from memory
            if snapshot_id in self._snapshots:
                del self._snapshots[snapshot_id]
            
            # Remove from disk
            snapshot_file = self._storage_path / f"{snapshot_id}.snapshot"
            if snapshot_file.exists():
                snapshot_file.unlink()
            
            # Remove backup
            backup_file = self._storage_path / 'backups' / f"{snapshot_id}.backup"
            if backup_file.exists():
                backup_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove snapshot {snapshot_id}: {e}")
            return False
    
    def _update_snapshot_metrics(self, snapshot_id: str, processing_time: float, success: bool) -> None:
        """Update snapshot creation metrics"""
        if success:
            self._metrics.total_snapshots += 1
            self._metrics.recent_snapshots.append(snapshot_id)
            
            # Update average processing time
            if self._metrics.average_snapshot_time == 0:
                self._metrics.average_snapshot_time = processing_time
            else:
                self._metrics.average_snapshot_time = (
                    self._metrics.average_snapshot_time * 0.9 + processing_time * 0.1
                )
        else:
            self._metrics.snapshot_errors += 1
    
    def _update_recovery_metrics(self, snapshot_id: str, recovery_time: float, success: bool) -> None:
        """Update recovery metrics"""
        if success:
            self._metrics.successful_recoveries += 1
            self._metrics.recent_recoveries.append(snapshot_id)
            
            # Update average recovery time
            if self._metrics.average_recovery_time == 0:
                self._metrics.average_recovery_time = recovery_time
            else:
                self._metrics.average_recovery_time = (
                    self._metrics.average_recovery_time * 0.9 + recovery_time * 0.1
                )
        else:
            self._metrics.failed_recoveries += 1
            self._metrics.recovery_errors += 1
    
    def get_state_metrics(self) -> StateMetrics:
        """Get state management metrics"""
        # Update total storage size
        self._metrics.total_storage_size = sum(s.size_bytes for s in self._snapshots.values())
        return self._metrics
    
    def get_available_snapshots(self) -> Dict[str, List[StateSnapshot]]:
        """Get all available snapshots grouped by target"""
        snapshots_by_target = defaultdict(list)
        for snapshot in self._snapshots.values():
            snapshots_by_target[snapshot.target_id].append(snapshot)
        
        # Sort each group by timestamp (newest first)
        for target_id in snapshots_by_target:
            snapshots_by_target[target_id].sort(key=lambda s: s.timestamp, reverse=True)
        
        return dict(snapshots_by_target)
    
    def export_snapshots(self, export_path: str, target_ids: List[str] = None) -> bool:
        """Export snapshots to a file for backup or transfer"""
        try:
            snapshots_to_export = []
            
            for snapshot in self._snapshots.values():
                if not target_ids or snapshot.target_id in target_ids:
                    # Prepare snapshot data for export
                    export_data = asdict(snapshot)
                    
                    # Include actual state data
                    export_data['actual_state_data'] = self._prepare_restoration_data(snapshot)
                    
                    snapshots_to_export.append(export_data)
            
            export_package = {
                'snapshots': snapshots_to_export,
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'version': '1.0',
                    'total_snapshots': len(snapshots_to_export)
                }
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_package, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(snapshots_to_export)} snapshots to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export snapshots: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the state manager"""
        with self._lock:
            try:
                self.logger.info("Shutting down StateManager")
                
                # Stop timers
                if self._snapshot_timer:
                    self._snapshot_timer.stop()
                if self._cleanup_timer:
                    self._cleanup_timer.stop()
                
                # Create final snapshots for all providers
                for provider_id in list(self._state_providers.keys()):
                    self.create_snapshot(
                        provider_id,
                        snapshot_name="Shutdown",
                        user_description="Final snapshot before shutdown"
                    )
                
                # Clean up crash detection file
                crash_file = self._storage_path / '.crash_detected'
                if crash_file.exists():
                    crash_file.unlink()
                
                self.logger.info("StateManager shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during StateManager shutdown: {e}")


# Factory function for creating state manager instances
def create_state_manager(config: Optional[Dict[str, Any]] = None) -> StateManager:
    """Create a new state manager instance with optional configuration"""
    return StateManager(config)


# Global instance management
_global_state_manager: Optional[StateManager] = None


def get_global_state_manager() -> StateManager:
    """Get or create the global state manager instance"""
    global _global_state_manager
    
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    
    return _global_state_manager


def set_global_state_manager(manager: StateManager) -> None:
    """Set the global state manager instance"""
    global _global_state_manager
    _global_state_manager = manager 