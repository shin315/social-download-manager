# UI Migration Tutorial
### Step-by-Step Guide for v1.2.1 to v2.0 Transition

## 🚀 Prerequisites

1. Ensure all v1.2.1 components are working properly
2. Backup current application state
3. Verify system requirements for v2.0

## 📋 Migration Steps

### Step 1: Initialize Bridge System

```python
from ui.adapters.feature_flag_manager import FeatureFlagManager
from ui.adapters.adapter_manager import AdapterManager

# Initialize feature flag manager
flag_manager = FeatureFlagManager()

# Load development preset for testing
flag_manager.load_preset("development")

# Initialize adapter manager
adapter_manager = AdapterManager(app_controller)
```

### Step 2: Start Health Monitoring

```python
# Start monitoring adapter health
adapter_manager.start_health_monitoring(interval=30)

# Verify monitoring is active
health_status = adapter_manager.get_system_health()
print(f"System health: {health_status}")
```

### Step 3: Enable Non-Critical Adapters First

```python
# Start with video info tab (non-critical)
flag_manager.set_flag("enable_video_info_adapter", True)

# Wait and check health
import time
time.sleep(5)
health = adapter_manager.get_adapter_health("video_info")
print(f"Video Info Adapter Health: {health}")
```

### Step 4: Enable Downloaded Videos Adapter

```python
# Enable downloaded videos adapter
flag_manager.set_flag("enable_downloaded_videos_adapter", True)

# Monitor system stability
health = adapter_manager.get_system_health()
if health["status"] == "healthy":
    print("✅ System stable - proceeding")
else:
    print("⚠️ System unstable - check logs")
```

### Step 5: Enable Main Window Adapter (Critical)

```python
# This is the most critical step
flag_manager.set_flag("enable_main_window_adapter", True)

# Set migration phase to complete
flag_manager.set_flag("migration_phase", "complete")

# Verify all adapters are healthy
all_healthy = adapter_manager.verify_all_adapters_healthy()
if all_healthy:
    print("🎉 Migration completed successfully!")
else:
    print("❌ Migration failed - initiating rollback")
    adapter_manager.initiate_rollback()
```

## 🚨 Emergency Rollback

If anything goes wrong during migration:

```python
# Emergency rollback procedure
flag_manager.load_preset("safe_mode")
adapter_manager.initiate_rollback()

# Verify rollback success
status = adapter_manager.get_system_health()
if status["status"] == "healthy":
    print("✅ Rollback successful - back to v1.2.1")
else:
    print("❌ Rollback failed - manual intervention required")
```

## 🔍 Monitoring Commands

### Check Feature Flags
```python
active_flags = flag_manager.get_all_flags(filter_status=FlagStatus.ACTIVE)
print("Active flags:", active_flags)
```

### Check Adapter Status
```python
adapter_status = adapter_manager.get_all_adapter_status()
for adapter_id, status in adapter_status.items():
    print(f"{adapter_id}: {status['status']}")
```

### View System Metrics
```python
metrics = adapter_manager.get_performance_metrics()
print(f"Memory usage: {metrics['memory_usage_mb']}MB")
print(f"Event processing: {metrics['event_processing_time_ms']}ms")
```

## 🛠️ Troubleshooting

### Common Issues

**Issue**: Adapter fails to initialize
```python
# Solution: Reset and reinitialize
adapter_manager.reset_adapter("video_info")
adapter_manager.force_reinitialize("video_info")
```

**Issue**: Events not being processed
```python
# Solution: Check event coordination
from ui.adapters.cross_component_coordinator import CrossComponentCoordinator
coordinator = CrossComponentCoordinator()
coordinator.enable_debug_tracing(True)
```

**Issue**: Memory usage too high
```python
# Solution: Cleanup old events
adapter_manager.cleanup_old_events()
coordinator.clear_event_history()
```

## ✅ Verification Checklist

- [ ] All feature flags configured correctly
- [ ] Health monitoring active
- [ ] All adapters healthy
- [ ] No memory leaks detected
- [ ] Event processing working
- [ ] User interface responsive
- [ ] Data integrity maintained
- [ ] Rollback procedure tested

## 📞 Support

If you encounter issues:

1. Check logs in `logs/` directory
2. Run diagnostic report: `adapter_manager.generate_diagnostic_report()`
3. Consult troubleshooting guide in full documentation
4. Contact development team if needed

---

**Created**: 2025-06-02  
**Version**: 1.0  
**Estimated Time**: 15-30 minutes 