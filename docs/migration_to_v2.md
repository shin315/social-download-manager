# Migration Guide: v1.2.1 to v2.0

## Overview

This guide provides step-by-step instructions for migrating Social Download Manager from version 1.2.1 to the new v2.0 architecture. The migration process is designed to be safe, reversible, and maintains full compatibility with existing data and configurations.

## What's New in v2.0

### Architecture Improvements
- **Modern v2.0 Core**: Event-driven architecture with better performance
- **Adapter Bridge System**: Seamless integration between v2.0 backend and v1.2.1 UI
- **Enhanced Error Handling**: User-friendly error dialogs with recovery suggestions
- **Graceful Degradation**: Automatic fallback modes ensure application always works
- **Performance Monitoring**: Built-in health checks and performance tracking

### User Benefits
- **Faster Startup**: <250ms startup time (vs ~400ms in v1.2.1)
- **Better Stability**: Automatic recovery from component failures
- **Same Familiar UI**: v1.2.1 interface preserved through adapters
- **Improved Performance**: More efficient resource usage
- **Enhanced Reliability**: Comprehensive error handling and logging

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] **Backed up your data** (see Backup section below)
- [ ] **Closed all instances** of Social Download Manager
- [ ] **Checked system requirements**:
  - Python 3.8 or higher
  - 100MB free disk space
  - Administrator/sudo access (for some operations)
- [ ] **Noted custom configurations** or modifications
- [ ] **Exported download history** if needed
- [ ] **Documented any third-party integrations**

## Backup Procedures

### Automatic Backup
```bash
# Run the backup script
python scripts/backup_v1.py

# This creates:
# - backup/v1.2.1_backup_YYYYMMDD_HHMMSS/
#   ├── config.json
#   ├── data/
#   │   └── app.db
#   ├── downloads/
#   └── logs/
```

### Manual Backup
```bash
# Create backup directory
mkdir -p backup/manual_$(date +%Y%m%d_%H%M%S)

# Copy important files
cp config.json backup/manual_*/
cp -r data/ backup/manual_*/
cp -r downloads/ backup/manual_*/
cp -r logs/ backup/manual_*/

# Create archive (optional)
tar -czf backup_v1.2.1_$(date +%Y%m%d).tar.gz backup/manual_*/
```

### What to Backup
1. **Configuration**: `config.json`
2. **Database**: `data/app.db`
3. **Download History**: `data/` directory
4. **Downloaded Files**: `downloads/` directory (optional, can be large)
5. **Logs**: `logs/` directory (for troubleshooting)
6. **Custom Scripts**: Any modifications you've made

## Migration Steps

### Step 1: Update Dependencies

```bash
# Update pip first
python -m pip install --upgrade pip

# Install new requirements
pip install -r requirements.txt --upgrade

# Verify critical packages
python -c "import PyQt6; print(f'PyQt6 {PyQt6.__version__} ✓')"
python -c "import aiohttp; print(f'aiohttp {aiohttp.__version__} ✓')"
```

### Step 2: Configuration Migration

The v2.0 configuration is backward compatible, but includes new sections:

```bash
# Backup existing config
cp config.json config.v1.json

# Merge v2.0 settings
python scripts/migrate_config.py

# Review the changes
diff config.v1.json config.json
```

New configuration sections added:
- `architecture`: v2.0 initialization settings
- `adapters`: Bridge layer configuration
- `error_handling`: Error dialog settings
- `shutdown`: Graceful shutdown options

### Step 3: Database Migration

```bash
# Check current database version
python scripts/check_db_version.py

# Run migration (automatic backup created)
python scripts/migrate_database.py

# Verify migration
python scripts/verify_db_migration.py
```

### Step 4: First Launch

```bash
# Start with verbose logging for first run
python main.py --verbose --show-startup-metrics

# Watch the startup sequence
# You should see:
# - 8 initialization phases completing
# - "Application ready" message
# - Familiar v1.2.1 UI appearing
```

### Step 5: Verify Core Functions

Test these essential functions:
1. **UI Loads**: Main window appears correctly
2. **Settings Work**: Open Settings dialog, make a change
3. **Download Test**: Try downloading a small file
4. **History Shows**: Check download history is intact
5. **Platforms Work**: Test YouTube and TikTok

## Post-Migration Verification

### Automated Tests
```bash
# Run migration verification suite
python scripts/test_migration.py

# This checks:
# ✓ Configuration validity
# ✓ Database integrity
# ✓ UI component functionality
# ✓ Download capabilities
# ✓ Platform integrations
```

### Manual Verification Checklist

#### Data Integrity
- [ ] All download history entries present
- [ ] User preferences preserved
- [ ] Platform credentials still work
- [ ] Custom settings maintained

#### Functionality Tests
- [ ] Can add new downloads
- [ ] Downloads complete successfully
- [ ] UI responds normally
- [ ] No error dialogs on startup
- [ ] Performance feels normal or better

#### Performance Metrics
```bash
# Check startup performance
grep "Startup completed" logs/app.log | tail -1

# Should show:
# "Startup completed in XXXms (target: 250ms)"
```

## Rollback Procedures

If you encounter issues, you can safely rollback to v1.2.1:

### Quick Rollback (Recommended)
```bash
# Use the rollback script
python scripts/rollback_to_v1.py

# This will:
# 1. Stop any running instances
# 2. Restore v1.2.1 files
# 3. Revert database changes
# 4. Reset configuration
```

### Manual Rollback
```bash
# Stop the application
pkill -f "python main.py" || taskkill /F /IM python.exe

# Restore backup
cp backup/v1.2.1_backup_*/config.json .
cp backup/v1.2.1_backup_*/data/app.db data/
cp -r backup/v1.2.1_backup_*/downloads/* downloads/

# Start v1.2.1 version
python main_v2.py  # Note: main_v2.py is actually v1.2.1
```

### Partial Rollback
If only specific components have issues:

```bash
# Disable v2.0 architecture (use v1.2.1 mode)
echo "ENABLE_V2_ARCHITECTURE=false" > .env

# Or disable specific features
echo "ENABLE_ADAPTER_BRIDGE=false" >> .env
echo "ENABLE_ERROR_DIALOGS=false" >> .env
```

## Troubleshooting Migration Issues

### Common Issues and Solutions

#### 1. "Module not found" Errors
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall

# Check for conflicts
pip check
```

#### 2. Configuration Errors
```bash
# Validate configuration
python scripts/validate_config.py

# Reset to default if needed
cp config.template.json config.json
```

#### 3. Database Lock Issues
```bash
# Check for running instances
ps aux | grep python

# Clear lock file
rm data/app.db-journal  # SQLite journal
rm data/.lock          # App lock file
```

#### 4. UI Not Appearing
```bash
# Test PyQt6 directly
python -c "from PyQt6.QtWidgets import QApplication, QLabel; app = QApplication([]); label = QLabel('Test'); label.show(); app.exec()"

# Check display settings
echo $DISPLAY  # Linux only
```

### Getting Help

If migration issues persist:

1. **Collect Diagnostics**:
   ```bash
   python scripts/collect_migration_diagnostics.py
   ```

2. **Check Logs**:
   - `logs/migration.log`: Migration-specific events
   - `logs/error.log`: Any errors during migration
   - `logs/app.log`: General application logs

3. **Report Issues**:
   Include:
   - Diagnostic report
   - Error messages
   - Steps that led to the issue
   - System information

## Feature Flags

Control v2.0 features individually:

```bash
# Create .env file
cat > .env << EOF
# Core Features
ENABLE_V2_ARCHITECTURE=true
ENABLE_ADAPTER_BRIDGE=true

# UI Features  
ENABLE_ERROR_DIALOGS=true
ENABLE_PERFORMANCE_MONITORING=true

# Advanced Features
ENABLE_AUTO_RECOVERY=true
ENABLE_HEALTH_CHECKS=true
EOF
```

## Performance Tuning

### Optimize for Your System

```json
// In config.json
{
  "architecture": {
    "initialization": {
      "timeout_ms": 5000,      // Increase for slower systems
      "retry_attempts": 3      // Reduce for faster startup
    }
  },
  "adapters": {
    "health_check_interval_ms": 60000  // Reduce frequency
  }
}
```

### Monitor Performance
```bash
# Enable performance logging
echo "LOG_PERFORMANCE=true" >> .env

# View performance metrics
tail -f logs/performance.log
```

## Best Practices

### During Migration
1. **Migrate during low activity** periods
2. **Test on a copy** first if possible
3. **Keep the backup** until confident
4. **Document any issues** encountered
5. **Monitor first 24 hours** closely

### After Migration
1. **Regular backups** continue to be important
2. **Monitor logs** for any warnings
3. **Report issues** to help improve v2.0
4. **Keep v1.2.1 backup** for 30 days
5. **Update documentation** for your setup

## FAQ

### Q: Will I lose any data during migration?
A: No, the migration process preserves all data. Automatic backups ensure recovery is possible.

### Q: Can I still use my custom scripts?
A: Yes, the v2.0 API is backward compatible. Minor adjustments may be needed for some scripts.

### Q: How do I know if migration succeeded?
A: Run `python scripts/test_migration.py` for comprehensive verification.

### Q: Can I migrate back and forth?
A: Yes, but it's not recommended. Each migration creates overhead and potential for issues.

### Q: What if migration fails halfway?
A: The process is transactional. It will rollback automatically on failure.

## Summary

The migration to v2.0 is designed to be:
- **Safe**: Multiple backup and rollback options
- **Transparent**: Same UI, better backend
- **Reversible**: Can return to v1.2.1 anytime
- **Beneficial**: Better performance and stability

Take your time, follow the steps, and enjoy the improved Social Download Manager v2.0! 