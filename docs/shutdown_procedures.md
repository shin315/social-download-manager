# Graceful Shutdown Procedures

## Overview

The v2.0 architecture implements a sophisticated 8-phase shutdown sequence that ensures all resources are properly released, data is saved, and the application exits cleanly. The shutdown process runs in reverse dependency order to maintain system integrity.

## Shutdown Initiation Methods

### 1. User-Initiated Shutdown
The most common shutdown method initiated by user action:

- **File → Exit Menu**: Standard menu option
- **Window Close Button**: Click the X button
- **Keyboard Shortcut**: Ctrl+Q (Cmd+Q on macOS)
- **System Tray**: Right-click → Exit

### 2. System Signal Shutdown
Operating system initiated shutdown:

- **SIGTERM**: Graceful termination request
- **SIGINT**: Interrupt signal (Ctrl+C)
- **System Shutdown**: OS shutdown/restart
- **Logout**: User session ending

### 3. Error-Triggered Shutdown
Automatic shutdown due to critical errors:

- **Fatal Error**: Unrecoverable application error
- **Resource Exhaustion**: Out of memory/disk space
- **Dependency Failure**: Critical component failure
- **Security Violation**: Unauthorized access attempt

## Shutdown Phases (Reverse Dependency Order)

### Phase 1: Verification Cleanup (5ms)
**Purpose**: Capture final application state and metrics

**Operations**:
- Save final performance metrics
- Log shutdown reason and timestamp
- Prepare shutdown summary report
- Capture any pending error information

**Components Affected**:
- Metrics collectors
- Health monitors
- Statistics trackers

### Phase 2: UI Component Cleanup (25ms)
**Purpose**: Gracefully close all user interface elements

**Operations**:
- Close all open dialogs and popups
- Save window position and size
- Store UI preferences and state
- Stop UI animations and timers
- Quit QApplication event loop

**Components Affected**:
- MainWindow
- Dialog windows
- System tray
- Notification system

### Phase 3: Bridge Layer Cleanup (30ms)
**Purpose**: Disconnect adapters and bridge components

**Operations**:
- Detach all Task 29 adapters
- Stop event bridge coordinator
- Clear adapter registrations
- Release bridge resources
- Save adapter state information

**Components Affected**:
- AdapterIntegrationFramework
- EventBridgeCoordinator
- All UI adapters

### Phase 4: Service Layer Cleanup (20ms)
**Purpose**: Stop all running services

**Operations**:
- Cancel active downloads
- Stop platform services
- Clear service registry
- Release service resources
- Save service state

**Components Affected**:
- DownloadService
- PlatformFactory
- ServiceRegistry

### Phase 5: Data Layer Cleanup (25ms)
**Purpose**: Ensure data integrity and close connections

**Operations**:
- Commit pending transactions
- Close database connections
- Release connection pool
- Flush write buffers
- Create data backup if configured

**Components Affected**:
- DatabaseConnection
- TransactionManager
- Repository instances

### Phase 6: Core Foundation Cleanup (15ms)
**Purpose**: Shutdown core architectural components

**Operations**:
- Stop event bus
- Clear event queues
- Release configuration
- Stop background threads
- Clear singleton instances

**Components Affected**:
- EventBus
- ConfigManager
- AppController

### Phase 7: System Cleanup (10ms)
**Purpose**: Clean system-level resources

**Operations**:
- Delete temporary files
- Release file locks
- Clear system caches
- Unregister from OS
- Clean IPC resources

**Components Affected**:
- File system handlers
- System integrations
- Temporary storage

### Phase 8: Finalization (5ms)
**Purpose**: Final cleanup and exit

**Operations**:
- Write final log entries
- Create shutdown report
- Set exit code
- Terminate process

**Total Shutdown Time**: ~135ms (target: <200ms)

## Shutdown Flow Diagram

```
┌─────────────────┐
│ Shutdown        │
│ Requested       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Check Shutdown  │──Already──> Return
│ State           │  Shutting
└────────┬────────┘    Down
         │Not Active
         v
┌─────────────────┐
│ Set Shutdown    │
│ State & Reason  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Create Backup?  │──Yes──> Emergency
│ (If configured) │         Backup
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Phase 1-8       │──Error──> Log &
│ Execution       │           Continue
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Rollback        │──Yes──> Execute
│ Needed?         │         Rollback
└────────┬────────┘
         │No
         v
┌─────────────────┐
│ Write Shutdown  │
│ Report          │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Exit            │
│ Application     │
└─────────────────┘
```

## Emergency Shutdown

For situations requiring immediate termination:

### Triggering Emergency Shutdown

1. **Double Ctrl+C**: Press Ctrl+C twice within 2 seconds
2. **Task Manager**: Force quit via OS task manager
3. **Kill Command**: 
   ```bash
   # Linux/macOS
   kill -9 <PID>
   
   # Windows
   taskkill /F /PID <PID>
   ```

### Emergency Shutdown Behavior

- Minimal cleanup performed
- Only critical resources released
- No data backup created
- Exit code indicates abnormal termination
- Recovery mode available on next start

### When to Use Emergency Shutdown

- Application completely frozen
- Normal shutdown not responding
- Critical security incident
- System resource emergency

## Shutdown Configuration

### config.json Settings
```json
{
  "shutdown": {
    "timeout_s": 30,
    "force_after_timeout": true,
    "create_backup": true,
    "cleanup_temp_files": true,
    "save_metrics": true
  }
}
```

### Environment Variables
```bash
# Shutdown timeout override
SHUTDOWN_TIMEOUT=60

# Disable backup on shutdown
SHUTDOWN_NO_BACKUP=true

# Force immediate shutdown
SHUTDOWN_FORCE=true
```

## Rollback Scenarios

### When Rollback Occurs

1. **Critical Handler Failure**: Essential cleanup fails
2. **Data Corruption Risk**: Transaction commit fails
3. **Resource Lock**: Cannot release critical resource
4. **Timeout Exceeded**: Shutdown takes too long

### Rollback Actions

1. **Restore Files**: Revert file changes
2. **Reset Database**: Rollback transactions
3. **Clear Cache**: Remove corrupted cache
4. **Reset Config**: Restore last good config
5. **Cleanup Temp**: Remove partial files
6. **Restart Services**: Attempt service recovery

## Best Practices

### For Users

1. **Always use normal shutdown** when possible
2. **Wait for shutdown completion** before turning off computer
3. **Check for active downloads** before shutting down
4. **Save work** before initiating shutdown
5. **Report hanging shutdowns** to help improve the system

### For Developers

1. **Implement proper cleanup** in all components
2. **Use shutdown handlers** for resource cleanup
3. **Set appropriate priorities** for handlers
4. **Test shutdown scenarios** thoroughly
5. **Log shutdown events** for debugging

### Shutdown Handler Example
```python
from core.shutdown_manager import ShutdownHandler, ShutdownReason

class MyComponentShutdownHandler(ShutdownHandler):
    def __init__(self, component):
        super().__init__(priority=75)  # 0-100, higher = earlier
        self.component = component
    
    def shutdown(self, reason: ShutdownReason) -> bool:
        try:
            # Save state
            self.component.save_state()
            
            # Stop operations
            self.component.stop()
            
            # Release resources
            self.component.cleanup()
            
            return True  # Success
        except Exception as e:
            self.logger.error(f"Shutdown failed: {e}")
            return False  # Trigger rollback
    
    def rollback(self, state) -> bool:
        # Attempt to restore component
        return self.component.restore(state)
```

## Monitoring Shutdown

### Log Files
- `logs/shutdown.log`: Dedicated shutdown events
- `logs/app.log`: General application logs
- `logs/error.log`: Shutdown errors

### Metrics
- Total shutdown time
- Per-phase timing
- Handler success rate
- Rollback frequency
- Resource cleanup stats

### Health Checks
```bash
# Check last shutdown
python scripts/check_last_shutdown.py

# Analyze shutdown performance
python scripts/analyze_shutdown_metrics.py

# Test shutdown sequence
python scripts/test_shutdown.py --dry-run
```

## Troubleshooting Shutdown Issues

### Application Won't Shutdown

1. Check for hanging operations:
   ```bash
   python scripts/check_hanging_ops.py
   ```

2. View shutdown progress:
   ```bash
   tail -f logs/shutdown.log
   ```

3. Force shutdown if needed:
   ```bash
   python main.py --force-shutdown
   ```

### Slow Shutdown

1. Identify slow phases:
   ```bash
   grep "phase.*duration" logs/shutdown.log
   ```

2. Optimize handler timeouts:
   ```json
   {
     "shutdown": {
       "handler_timeout_s": 5
     }
   }
   ```

### Data Loss on Shutdown

1. Enable shutdown backup:
   ```json
   {
     "shutdown": {
       "create_backup": true
     }
   }
   ```

2. Increase transaction timeout:
   ```json
   {
     "database": {
       "shutdown_timeout_s": 10
     }
   }
   ```

## Recovery After Abnormal Shutdown

### Automatic Recovery
On next startup, the application will:
1. Detect abnormal shutdown
2. Run integrity checks
3. Restore from backup if available
4. Clear corrupted data
5. Log recovery actions

### Manual Recovery
```bash
# Check shutdown state
python scripts/check_shutdown_state.py

# Clear shutdown lock
python scripts/clear_shutdown_lock.py

# Restore from backup
python scripts/restore_from_backup.py

# Reset to clean state
python scripts/reset_application.py
``` 