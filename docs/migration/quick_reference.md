# Migration Quick Reference Cards - V2.0

## 🚀 Quick Reference for IT Teams

Essential migration information for rapid V1.2.1 to V2.0 deployment and troubleshooting.

---

## 📋 Card 1: Pre-Migration Checklist

### System Requirements Verification
```
✅ SYSTEM COMPATIBILITY CHECK:
☐ OS: Windows 10+, macOS 10.15+, Ubuntu 18.04+
☐ Python: 3.8 or higher
☐ RAM: 4GB minimum (8GB recommended)  
☐ Storage: 2GB free space
☐ Network: Stable broadband connection
☐ Graphics: PyQt6 compatible drivers
```

### V1.2.1 Assessment
```
✅ CURRENT INSTALLATION CHECK:
☐ Version: python -c "import version; print(version.get_version())"
☐ Data size: Check %APPDATA%\social-download-manager\ size
☐ Active downloads: Complete or document for resumption
☐ Custom settings: Screenshot interface for reference
☐ Authentication: Verify saved credentials working
```

### Backup Verification
```
✅ MANDATORY BACKUP STEPS:
☐ Config files: Copy entire %APPDATA%\social-download-manager\
☐ Download history: Backup downloads.db with integrity check
☐ User data: Document download locations and preferences
☐ Settings export: Run settings export utility
☐ Verification: Test backup restoration procedure
```

---

## ⚡ Card 2: Installation Commands

### Windows Installation
```powershell
# Standard Installation
SocialDownloadManager_v2.0_setup.exe /S /MIGRATEV1=1 /PRESERVEDATA=1

# Silent Enterprise Installation  
msiexec /i "SocialDownloadManager_v2.0_enterprise.msi" /quiet /l*v "install.log" CONFIGFILE="enterprise_config.json"

# Installation Verification
Get-ItemProperty "HKLM:\SOFTWARE\SocialDownloadManager" -Name "Version"
# Expected: 2.0.0
```

### Linux/macOS Installation
```bash
# Extract and Install
tar -xzf social-download-manager-v2.0.tar.gz
cd social-download-manager-v2.0/
sudo ./install.sh --migrate-v1 --preserve-data

# Verification
python3 -c "import social_download_manager; print(social_download_manager.__version__)"
# Expected: 2.0.0
```

### Docker Deployment
```bash
# Pull V2.0 image
docker pull socialdownloadmanager:v2.0

# Run with migration
docker run -d --name sdm-v2 \
  -v /host/data:/app/data \
  -v /host/config:/app/config \
  socialdownloadmanager:v2.0 --migrate-from-v1
```

---

## 🔧 Card 3: Common Issues & Quick Fixes

### Installation Failures
```
❌ INSTALLER FAILS TO DETECT V1.2.1:
Fix: Run with explicit path
Windows: setup.exe /V1PATH="%APPDATA%\social-download-manager"
Linux: ./install.sh --v1-path="~/.config/social-download-manager"

❌ INSUFFICIENT DISK SPACE:
Fix: Free up 2GB minimum
- Clear temp files: %TEMP%, /tmp/
- Empty recycle bin/trash
- Move large files to external storage

❌ PERMISSION DENIED:
Fix: Run with elevated privileges
Windows: Right-click > Run as Administrator  
Linux: sudo ./install.sh
```

### Data Migration Issues
```
❌ DOWNLOAD HISTORY MISSING:
Fix: Manual database import
1. Copy old downloads.db to new installation
2. Settings > Import > Download History
3. Select backed up database file

❌ SETTINGS NOT MIGRATED:
Fix: Manual configuration import
1. Locate v1_settings_export.json backup
2. Settings > Import > V1.2.1 Configuration
3. Select backup file and restart

❌ DOWNLOAD LOCATIONS INACCESSIBLE:
Fix: Update paths in settings
1. Settings > Downloads > Locations
2. Update each path to current locations
3. Test accessibility with "Browse" button
```

### Performance Problems
```
❌ SLOW STARTUP (>5 seconds):
Fix: Performance optimization
1. Close other applications during startup
2. Clear application cache: Settings > Storage > Clear Cache
3. Check system resources: Task Manager > Performance
4. Restart in safe mode if needed

❌ HIGH MEMORY USAGE (>500MB):
Fix: Enable hibernation and cleanup
1. Settings > Performance > Enable Tab Hibernation
2. Close unnecessary tabs (keep <10 active)
3. Clear cache and restart application
4. Check for memory leaks: F12 dashboard

❌ TAB HIBERNATION NOT WORKING:
Fix: Reset hibernation system
1. Settings > Performance > Reset Tab Manager
2. Verify hibernation timeout: 10 minutes default
3. Manual test: Right-click tab > Hibernate
4. Check minimum tab count requirement (>5)
```

---

## 📊 Card 4: Performance Validation

### Startup Performance Test
```bash
# Measure startup time
time social-download-manager --benchmark-startup
# Target: <3 seconds (vs 8.5s V1.2.1)

# Memory usage check
ps aux | grep social-download-manager | awk '{print $6}'
# Target: <150MB (vs 650MB V1.2.1)
```

### Feature Validation Checklist
```
✅ CORE FUNCTIONALITY TEST:
☐ Download test: YouTube/TikTok video
☐ Quality selection: 1080p, 720p, 4K options
☐ Tab management: Create 5+ tabs, verify hibernation
☐ Theme switching: Light/Dark/Auto themes (<2ms)
☐ Performance dashboard: F12 key access
☐ State recovery: Force-close and restart test
```

### Performance Targets
```
📈 V2.0 PERFORMANCE EXPECTATIONS:
✅ Startup time: <3s (70% improvement)
✅ Memory usage: <150MB (84% reduction)  
✅ Tab switching: <50ms (99% improvement)
✅ Theme switching: <2ms (99.7% improvement)
✅ Download init: <200ms (43% improvement)
✅ ComponentBus: >100k msg/s throughput
```

---

## 🚨 Card 5: Emergency Procedures

### Immediate Rollback (15 minutes)
```bash
# STEP 1: Stop V2.0 immediately
# Windows
taskkill /f /im "social-download-manager.exe"
# Linux/macOS
killall social-download-manager

# STEP 2: Restore V1.2.1 from backup
# Windows
robocopy "C:\SDM_Backup_*" "%APPDATA%\social-download-manager\" /E
# Linux/macOS
cp -r ~/SDM_Backup_*/* ~/.config/social-download-manager/

# STEP 3: Verify V1.2.1 functionality
python -c "import version; print(f'Restored version: {version.get_version()}')"
# Expected: 1.2.1
```

### Data Recovery Procedures
```bash
# Restore corrupted database
cp backup/downloads_*.db downloads.db
sqlite3 downloads.db "PRAGMA integrity_check;"

# Reset to minimal configuration
python reset_to_defaults.py

# Clear all caches and restart
rm -rf ~/.config/social-download-manager/cache/
rm -rf ~/.config/social-download-manager/temp/
```

### Emergency Contacts
```
🆘 EMERGENCY SUPPORT:
- Critical Issues: emergency@socialdownloadmanager.com
- Phone Support: 1-800-SDM-HELP (1-800-736-4357)
- Escalation: Level 4 support for data loss/security issues
- Response Time: <2 hours for critical issues
```

---

## 🔍 Card 6: Verification & Testing

### Migration Success Validation
```bash
# Complete verification script
python migration_verify.py --full-check

# Expected output:
# ✅ Version: 2.0.0
# ✅ Data integrity: 100% preserved
# ✅ Performance: All targets met
# ✅ Features: All functional
# ✅ Migration: SUCCESS
```

### Performance Monitoring Setup
```bash
# Enable F12 dashboard monitoring
# Key metrics to watch:
# - Memory usage trend (should stay <200MB)
# - Tab hibernation effectiveness
# - Download success rate (>95%)
# - Startup time consistency
# - Error rate (should be 0%)
```

### User Acceptance Criteria
```
✅ MIGRATION SUCCESS INDICATORS:
☐ Zero data loss reported
☐ User can complete normal workflows  
☐ Performance visibly improved
☐ No increase in support tickets
☐ User satisfaction >85%
☐ All V1.2.1 features available
☐ New V2.0 features accessible
```

---

## 📞 Card 7: Support & Escalation

### Self-Service Troubleshooting
```
🔧 FIRST-LINE SUPPORT STEPS:
1. Check F12 performance dashboard for issues
2. Review error logs: %APPDATA%\social-download-manager\logs\
3. Test basic functionality: download, tab switch, theme change
4. Clear cache if performance issues: Settings > Storage
5. Restart application if persistent problems
```

### Escalation Decision Matrix
```
🚨 ESCALATE TO TIER 2 IF:
- User unable to complete basic downloads
- Memory usage >500MB consistently  
- Startup time >5 seconds regularly
- Data loss or corruption suspected
- Multiple user reports of same issue

🚨 ESCALATE TO TIER 3 IF:  
- Complete application failure
- Security-related concerns
- Enterprise deployment issues
- Integration problems with other systems
- Performance <50% of expected targets

🚨 ESCALATE TO TIER 4 IF:
- Data loss confirmed
- Security breach suspected  
- Critical business impact
- Vendor bug suspected
- Mass deployment failures
```

### Documentation Requirements
```
📝 INCIDENT DOCUMENTATION:
Required Information:
- User details: Name, department, OS version
- Issue description: What happened, when, frequency
- Environment: V1.2.1 migration date, current config
- Steps taken: Troubleshooting attempted
- Impact: Business impact assessment
- Screenshots: Error messages, performance metrics
```

---

## 🎯 Card 8: Success Metrics

### Technical KPIs
```
📊 TRACK THESE METRICS:
Deployment Success:
- Migration completion rate: Target >95%
- Rollback rate: Target <5%
- Data integrity: Target 100%

Performance Achievement:  
- Startup improvement: Target >50%
- Memory reduction: Target >70%
- User response time: Target <100ms

User Adoption:
- Daily active users: Target >80% within 2 weeks
- Feature utilization: Track hibernation, themes, F12
- Support ticket volume: Target <110% of baseline
```

### Business Impact Tracking
```
💰 ROI MEASUREMENT:
Productivity Gains:
- Time saved per user: ~8.5 minutes/day
- Monetary value: User hourly rate × time saved
- System efficiency: Memory/CPU savings

Cost Reductions:
- IT support tickets: Track volume and resolution time
- Training costs: Reduced due to familiar interface
- Infrastructure: Memory savings × cost per GB

User Satisfaction:
- Survey scores: Target >85% satisfaction
- Feature feedback: Collect improvement suggestions
- Adoption rate: Track new feature usage
```

---

## 🎓 Card 9: Training Quick Guide

### Essential User Training (15 minutes)
```
👨‍🏫 MANDATORY TRAINING TOPICS:
1. New Performance Features (5 min):
   - F12 dashboard overview
   - Tab hibernation concept
   - Theme switching demonstration

2. Familiar Features (5 min):
   - Download process unchanged
   - Settings location and options
   - Keyboard shortcuts (same + new)

3. Troubleshooting Basics (5 min):
   - When to use F12 dashboard
   - How to clear cache
   - When to contact IT support
```

### Power User Training (30 minutes)
```
🎯 ADVANCED FEATURES:
1. Performance Optimization:
   - Manual hibernation control
   - Memory monitoring techniques
   - Custom performance thresholds

2. Advanced Configuration:
   - Custom theme creation
   - Keyboard shortcut customization
   - Export/import settings

3. Troubleshooting:
   - Log file analysis
   - Performance debugging
   - Configuration reset procedures
```

### Training Validation
```
✅ USER COMPETENCY CHECK:
☐ Can download video successfully
☐ Knows how to access F12 dashboard
☐ Understands tab hibernation concept
☐ Can switch themes quickly
☐ Knows when to contact support
☐ Comfortable with interface changes
```

---

## 🎉 Card 10: Migration Completion

### Final Validation Checklist
```
✅ MIGRATION COMPLETION CRITERIA:
Technical Validation:
☐ V2.0 version confirmed installed
☐ All user data successfully migrated
☐ Performance targets achieved
☐ New features operational
☐ Security compliance verified

User Validation:
☐ User training completed
☐ Basic functionality tested by user
☐ User comfortable with changes
☐ Support contact information provided
☐ User satisfaction survey completed

Administrative Validation:
☐ Migration documented in system
☐ Performance baseline established
☐ Monitoring enabled and configured
☐ Support procedures tested
☐ Success metrics tracking active
```

### Handover Documentation
```
📋 HANDOVER TO OPERATIONS:
Required Documentation:
- Migration completion report
- Performance baseline measurements  
- User training completion records
- Configuration backup verification
- Support escalation procedures tested
- Monitoring dashboard configured
- Success metrics tracking enabled
```

### Celebration & Recognition
```
🎉 MIGRATION SUCCESS ACHIEVED!
User Benefits Delivered:
✅ 70% faster startup time
✅ 84% memory usage reduction
✅ 99% faster interface operations
✅ Enhanced reliability and recovery
✅ Modern, accessible interface
✅ Future-ready platform capabilities

Next Steps:
- Monitor performance trends
- Collect user feedback for improvements
- Plan advanced feature training
- Track ROI realization
- Prepare for future updates
```

---

*Quick Reference Cards Version 1.0 • December 2025 • For V2.0 Migration Support*

**IT Support Hotline**: it-support@company.com | **Emergency**: 1-800-SDM-HELP 