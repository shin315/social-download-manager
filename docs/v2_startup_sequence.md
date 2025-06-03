# Social Download Manager v2.0 Startup Sequence

## Overview
The v2.0 architecture implements an 8-phase initialization sequence with automatic fallback mechanisms to ensure reliable application startup while maintaining backward compatibility with v1.2.1.

## Architecture Modes

### FULL_V2_PRODUCTION
- Complete v2.0 architecture with all components
- Task 29 adapters bridging to v1.2.1 UI
- Full performance monitoring and health checks
- Target startup time: <250ms

### FULL_V2_DEV
- Development mode with enhanced debugging
- Verbose logging and startup metrics
- Extended timeouts for debugging
- Hot-reload support for adapters

### DEGRADED_V2
- Core v2.0 functionality with minimal adapters
- Activated when non-critical components fail
- Reduced feature set but stable operation
- Fallback from FULL_V2 modes

### FALLBACK_V1
- Legacy v1.2.1 mode only
- No v2.0 components or adapters
- Ensures application always starts
- Last resort fallback option

## Initialization Phases

### Phase 1: Constants Validation (5ms)
**Components**: AppConstants, Version Info
**Purpose**: Validate core application constants and display version
**Critical**: Yes - Application cannot start without valid constants

**Operations**:
- Load and validate AppConstants configuration
- Display application version and build information
- Set up basic application metadata
- Initialize emergency logging for critical errors

**Failure Handling**: Fatal error - show emergency dialog and exit

### Phase 2: Core Foundation (20ms)
**Components**: ConfigManager, EventBus, AppController
**Purpose**: Initialize core v2.0 architecture foundation
**Critical**: Yes - Required for all other components

**Operations**:
- Initialize ConfigManager with config.json
- Create EventBus for v2.0 event system
- Initialize AppController as central coordinator
- Set up core error handling infrastructure

**Failure Handling**: Fallback to FALLBACK_V1 mode

### Phase 3: Data Layer (30ms)
**Components**: DatabaseConnection, TransactionManager, Repositories
**Purpose**: Establish data persistence layer
**Critical**: Yes - Required for application state

**Operations**:
- Open database connection with connection pooling
- Initialize TransactionManager for ACID compliance
- Create repository instances for data access
- Run database migrations if needed

**Failure Handling**: Attempt read-only mode, then fallback

### Phase 4: Service Layer (25ms)
**Components**: ServiceRegistry, PlatformFactory, Services
**Purpose**: Initialize business logic and platform services
**Critical**: No - Can operate with reduced services

**Operations**:
- Initialize ServiceRegistry for service management
- Create PlatformFactory for YouTube/TikTok
- Register available platform services
- Initialize download management services

**Failure Handling**: Continue with available services

### Phase 5: Bridge Layer (40ms)
**Components**: AdapterFramework, EventBridgeCoordinator
**Purpose**: Set up Task 29 adapter integration
**Critical**: Yes for v2.0 modes - Required for UI compatibility

**Operations**:
- Initialize adapter integration framework
- Create EventBridgeCoordinator for v1.2.1 compatibility
- Prepare adapter registration system
- Set up performance monitoring

**Failure Handling**: Fallback to FALLBACK_V1 mode

### Phase 6: UI Adapters (50ms)
**Components**: Individual Task 29 Adapters
**Purpose**: Register and initialize UI component adapters
**Critical**: No - Can operate with partial adapters

**Operations**:
- Register MainWindowAdapter
- Register DownloadListAdapter
- Register SettingsAdapter
- Register other UI adapters
- Start adapter health monitoring

**Failure Handling**: Continue with successful adapters (DEGRADED_V2)

### Phase 7: Legacy UI (25ms)
**Components**: QApplication, MainWindow v1.2.1
**Purpose**: Create and display the user interface
**Critical**: Yes - No UI means no user interaction

**Operations**:
- Create PyQt6 QApplication instance
- Initialize v1.2.1 MainWindow
- Attach adapters to UI components
- Apply saved window state and preferences

**Failure Handling**: Show emergency error dialog

### Phase 8: Verification (5ms)
**Components**: Health Checks, Metrics
**Purpose**: Verify successful initialization
**Critical**: No - Informational only

**Operations**:
- Perform component health checks
- Calculate initialization success rate
- Log startup metrics and timing
- Display ready message to user

**Failure Handling**: Log warnings but continue

## Total Startup Time: ~200ms (target: <250ms)

## Startup Flow Diagram

```
┌─────────────────┐
│ Application     │
│ Start           │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Python Version  │──No──> Fatal Error
│ Check (3.8+)    │
└────────┬────────┘
         │Yes
         v
┌─────────────────┐
│ Phase 1:        │──Fail──> Emergency
│ Constants       │          Dialog
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 2:        │──Fail──> FALLBACK_V1
│ Core Foundation │          Mode
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 3:        │──Fail──> Read-Only
│ Data Layer      │          or Fallback
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 4:        │──Fail──> Continue with
│ Service Layer   │          Available
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 5:        │──Fail──> FALLBACK_V1
│ Bridge Layer    │          Mode
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 6:        │──Partial──> DEGRADED_V2
│ UI Adapters     │             Mode
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 7:        │──Fail──> Emergency
│ Legacy UI       │          Dialog
└────────┬────────┘
         │Success
         v
┌─────────────────┐
│ Phase 8:        │
│ Verification    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Application     │
│ Ready           │
└─────────────────┘
```

## Performance Characteristics

### Memory Usage
- Initial footprint: ~48MB
- After full initialization: ~75MB
- With active downloads: ~100-150MB

### CPU Usage
- Startup spike: 15-25%
- Idle: <1%
- Active downloading: 5-10%

### Concurrent Initialization
Phases that can run in parallel:
- Service registry components (Phase 4)
- UI adapter registration (Phase 6)
- Health checks (Phase 8)

## Monitoring and Diagnostics

### Startup Metrics
- Total initialization time
- Per-phase timing breakdown
- Component success/failure count
- Memory usage at each phase
- Mode transitions (if any)

### Health Indicators
- ✅ Green: All components initialized successfully
- 🟡 Yellow: Some non-critical components failed (DEGRADED_V2)
- 🔴 Red: Critical failure, running in FALLBACK_V1

### Log Categories
- `STARTUP`: General startup events
- `PHASE`: Phase-specific events
- `ADAPTER`: Adapter initialization
- `PERFORMANCE`: Timing and metrics
- `ERROR`: Initialization failures

## Troubleshooting Quick Reference

| Phase | Common Issues | Quick Fix |
|-------|--------------|-----------|
| 1 | Missing constants | Check installation integrity |
| 2 | Config not found | Copy config.template.json |
| 3 | Database locked | Close other instances |
| 4 | Service failure | Check platform dependencies |
| 5 | Bridge timeout | Increase timeout in config |
| 6 | Adapter errors | Update to latest version |
| 7 | UI won't show | Check PyQt6 installation |
| 8 | Health check fail | Review error logs |

## Best Practices

1. **Always check logs** in `logs/app.log` for detailed startup information
2. **Monitor first startup** after updates for any degradation
3. **Use verbose mode** (`--verbose`) when troubleshooting
4. **Keep config.json** backed up before modifications
5. **Test in development mode** before production deployment 