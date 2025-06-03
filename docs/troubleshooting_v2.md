# Troubleshooting Guide for v2.0 Architecture

## Quick Diagnostics

Before diving into specific issues, run these quick checks:

```bash
# Check Python version
python --version  # Should be 3.8 or higher

# Verify PyQt6 installation
python -c "import PyQt6; print(f'PyQt6 {PyQt6.__version__} installed')"

# Test configuration
python -c "import json; json.load(open('config.json'))"

# Check database
python scripts/check_db_integrity.py

# View recent errors
tail -n 50 logs/error.log
```

## Common Startup Issues

### 1. Python Version Error (Code: 1001)
**Error Message**: "Python 3.8 or higher is required. You are using Python X.X"

**Symptoms**:
- Application fails to start immediately
- Error dialog shows Python version mismatch

**Solutions**:
1. Update Python to version 3.8 or higher:
   ```bash
   # Windows
   Download from python.org
   
   # Linux
   sudo apt update && sudo apt install python3.8
   
   # macOS
   brew install python@3.8
   ```

2. Use virtual environment:
   ```bash
   python3.8 -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Update PATH environment variable to point to correct Python

### 2. PyQt6 Import Error (Code: 1103)
**Error Message**: "PyQt6 is not installed or cannot be imported"

**Symptoms**:
- ImportError when starting application
- Missing PyQt6 modules

**Solutions**:
```bash
# Install PyQt6
pip install PyQt6==6.5.0

# If that fails, try:
pip install --upgrade pip
pip install PyQt6==6.5.0 --no-cache-dir

# For system-wide installation (Linux):
sudo apt install python3-pyqt6

# Verify installation:
python -c "from PyQt6.QtWidgets import QApplication"
```

### 3. Configuration File Error (Code: 1201)
**Error Message**: "Configuration file not found or corrupt"

**Symptoms**:
- config.json missing or invalid
- JSON parsing errors

**Solutions**:
1. Create config from template:
   ```bash
   cp config.template.json config.json
   ```

2. Validate JSON syntax:
   ```bash
   python -m json.tool config.json
   ```

3. Fix common JSON errors:
   - Remove trailing commas
   - Ensure all strings are quoted
   - Check bracket matching

4. Reset to defaults:
   ```bash
   # Backup current config
   mv config.json config.json.backup
   # Copy fresh template
   cp config.template.json config.json
   ```

### 4. Database Connection Error (Code: 1401)
**Error Message**: "Failed to connect to database"

**Symptoms**:
- Database file locked or corrupted
- Permission denied errors
- Migration failures

**Solutions**:
1. Check database file permissions:
   ```bash
   # Linux/macOS
   chmod 644 data/app.db
   chmod 755 data/
   
   # Windows - Check file properties
   ```

2. Close other instances:
   ```bash
   # Linux/macOS
   ps aux | grep "Social Download Manager"
   kill <PID>
   
   # Windows
   taskkill /F /IM python.exe
   ```

3. Repair database:
   ```bash
   # Backup first
   cp data/app.db data/app.db.backup
   
   # Run integrity check
   python scripts/check_db_integrity.py --repair
   
   # If corrupted, restore from backup
   cp data/backup/app.db data/app.db
   ```

4. Reset database (loses data):
   ```bash
   rm data/app.db
   python scripts/init_database.py
   ```

### 5. Adapter Initialization Error (Code: 1304)
**Error Message**: "Failed to initialize adapters"

**Symptoms**:
- Task 29 adapters not loading
- UI components not responding
- Bridge layer timeout

**Solutions**:
1. Verify adapter files exist:
   ```bash
   ls -la ui/adapters/
   # Should show all adapter files
   ```

2. Check adapter dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. Increase initialization timeout:
   ```json
   // In config.json
   "architecture": {
     "initialization": {
       "timeout_ms": 10000  // Increase from 5000
     }
   }
   ```

4. Enable adapter debug logging:
   ```bash
   LOG_LEVEL=DEBUG python main.py
   ```

### 6. UI Creation Error (Code: 1501)
**Error Message**: "Failed to create application window"

**Symptoms**:
- Window doesn't appear
- QApplication errors
- Display/graphics issues

**Solutions**:
1. Check display environment:
   ```bash
   # Linux - Check X11/Wayland
   echo $DISPLAY
   xhost +
   
   # Windows - Update graphics drivers
   ```

2. Test PyQt6 separately:
   ```python
   from PyQt6.QtWidgets import QApplication, QWidget
   app = QApplication([])
   window = QWidget()
   window.show()
   app.exec()
   ```

3. Try software rendering:
   ```bash
   export QT_QUICK_BACKEND=software
   python main.py
   ```

## Fallback Mode Scenarios

### FULL_V2 → DEGRADED_V2 Transition

**Triggers**:
- Non-critical adapter failures (1-2 adapters)
- Performance threshold exceeded (>100ms response time)
- Optional component unavailable
- Memory pressure (>100MB adapter memory)

**User Impact**: 
- Minimal - some features may be slower
- Specific UI components may not update in real-time
- Performance monitoring may be limited

**Recovery**:
```bash
# Check which adapters failed
grep "adapter.*failed" logs/app.log

# Restart specific adapters
python scripts/restart_adapters.py --failed-only

# Monitor adapter health
python scripts/monitor_adapters.py
```

### DEGRADED_V2 → FALLBACK_V1 Transition

**Triggers**:
- Bridge layer complete failure
- Critical adapter malfunction (>50% adapters failed)
- Core v2.0 component error
- Event system breakdown

**User Impact**: 
- Falls back to v1.2.1 functionality
- No v2.0 features available
- Performance returns to v1.2.1 levels
- All data preserved

**Recovery**:
```bash
# Force v1.2.1 mode on next start
echo "ENABLE_V2_ARCHITECTURE=false" >> .env

# Or use command line
python main.py --fallback-v1

# To re-enable v2.0
python main.py --reset-mode
```

### Emergency Mode

**Triggers**:
- Fatal initialization error
- Critical resource unavailable (no disk space, etc.)
- Unrecoverable exception
- Corrupted core files

**User Impact**: 
- Error dialog with recovery options
- Limited functionality
- Data recovery mode available

**Recovery Steps**:
1. Note the error code and message
2. Check available disk space
3. Verify file integrity
4. Run recovery tool:
   ```bash
   python scripts/emergency_recovery.py
   ```

## Error Code Reference

### System Errors (1000-1099)
| Code | Error | Solution |
|------|-------|----------|
| 1001 | Python version too old | Update Python to 3.8+ |
| 1002 | Missing system dependency | Install required system packages |
| 1003 | Insufficient permissions | Run as administrator or fix permissions |
| 1004 | System resource exhausted | Free up memory/disk space |

### Import/Dependency Errors (1100-1199)
| Code | Error | Solution |
|------|-------|----------|
| 1101 | Missing required module | Run `pip install -r requirements.txt` |
| 1102 | Version conflict | Update conflicting packages |
| 1103 | PyQt6 not available | Install PyQt6==6.5.0 |
| 1104 | Core module corrupted | Reinstall application |

### Configuration Errors (1200-1299)
| Code | Error | Solution |
|------|-------|----------|
| 1201 | Config file not found | Copy config.template.json to config.json |
| 1202 | Config file corrupt | Validate JSON syntax |
| 1203 | Invalid config value | Check config documentation |
| 1204 | Missing required setting | Add missing configuration key |

### Initialization Errors (1300-1399)
| Code | Error | Solution |
|------|-------|----------|
| 1301 | Component init failed | Check component logs |
| 1302 | Timeout during init | Increase timeout in config |
| 1303 | Dependency not met | Check initialization order |
| 1304 | Adapter init failed | Verify adapter files |

### Database Errors (1400-1499)
| Code | Error | Solution |
|------|-------|----------|
| 1401 | Connection failed | Check database file permissions |
| 1402 | Migration failed | Run manual migration |
| 1403 | Corruption detected | Restore from backup |
| 1404 | Lock timeout | Close other instances |

### UI Errors (1500-1599)
| Code | Error | Solution |
|------|-------|----------|
| 1501 | QApplication failed | Check display environment |
| 1502 | Main window failed | Verify PyQt6 installation |
| 1503 | Theme load failed | Reset to default theme |
| 1504 | Icon load failed | Verify resource files |

## Advanced Troubleshooting

### Enable Verbose Logging
```bash
# Maximum verbosity
LOG_LEVEL=TRACE python main.py --verbose

# Specific component debugging
LOG_LEVEL=DEBUG LOG_CATEGORY=ADAPTER python main.py

# Performance profiling
python main.py --profile --show-startup-metrics
```

### Component Health Check
```python
# Run health check script
python scripts/health_check.py

# Check specific component
python scripts/health_check.py --component adapter_framework

# Generate health report
python scripts/health_check.py --report > health_report.txt
```

### Manual Mode Override
```bash
# Force specific mode
python main.py --mode DEGRADED_V2

# Skip specific phases
python main.py --skip-phase adapters

# Dry run (no actual startup)
python main.py --dry-run
```

### Log Analysis
```bash
# Find all errors in last hour
grep -E "ERROR|CRITICAL" logs/app.log | tail -n 100

# Track mode transitions
grep "mode transition" logs/app.log

# Performance issues
grep "threshold exceeded" logs/performance.log

# Adapter specific issues
grep "adapter:" logs/app.log | grep -i error
```

## Getting Help

### Before Reporting Issues
1. Check this troubleshooting guide
2. Search existing issues on GitHub
3. Collect diagnostic information:
   ```bash
   python scripts/collect_diagnostics.py
   ```

### Information to Include
- Error code and full error message
- Steps to reproduce
- System information (OS, Python version)
- Relevant log excerpts
- Diagnostic report

### Support Channels
- GitHub Issues: [Report bugs and issues]
- Documentation: [Full documentation]
- Community Forum: [Get help from community]

## Prevention Tips

1. **Regular Backups**
   ```bash
   python scripts/backup_data.py --auto
   ```

2. **Monitor System Health**
   ```bash
   python scripts/monitor_health.py --daemon
   ```

3. **Keep Updated**
   ```bash
   python scripts/check_updates.py
   ```

4. **Test Configuration Changes**
   ```bash
   python scripts/validate_config.py config.json
   ```

5. **Clean Temporary Files**
   ```bash
   python scripts/cleanup_temp.py
   ``` 