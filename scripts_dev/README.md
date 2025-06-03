# Development Scripts Directory

## 🛠️ Development & Utility Scripts for SDM v2.0

This directory contains development, testing, and utility scripts organized by functionality.

### 📁 Directory Structure

#### `/database/`
**Database management and testing scripts**
- Database creation and setup scripts
- Migration testing utilities
- Database optimization tools
- Schema validation scripts
- Data conversion utilities

**Key Scripts:**
- `create_test_db.py` - Create test database
- `check_db.py` - Database health checks
- `debug_db*.py` - Database debugging tools

#### `/performance/`
**Performance testing and optimization scripts**
- Performance benchmarking tools
- Memory management testing
- Optimization validation scripts
- Resource monitoring utilities
- Load testing tools

**Key Scripts:**
- `run_*_optimization.py` - Various optimization tests
- `run_performance_profiling.py` - Performance profiling
- `run_memory_management.py` - Memory usage analysis

#### `/validation/`
**Validation and integration testing scripts**
- System validation tools
- Integration test runners
- Final verification scripts
- Workflow validation utilities

**Key Scripts:**
- `run_final_validation*.py` - System validation
- `run_integration_tests.py` - Integration testing

#### `/utilities/`
**General utility and debugging scripts**
- Debugging utilities
- Simple test scripts
- Demo applications
- Development helpers
- Translation checkers

**Key Scripts:**
- `check_*.py` - Various system checks
- `debug_*.py` - Debugging utilities
- `simple_*.py` - Simplified test scripts
- `demo_*.py` - Demo applications

### 🚀 Usage Guidelines

#### Database Scripts:
```bash
# Set up test database
python scripts_dev/database/create_test_db.py

# Check database health
python scripts_dev/database/check_db.py

# Debug database issues
python scripts_dev/database/debug_db.py
```

#### Performance Scripts:
```bash
# Run performance tests
python scripts_dev/performance/run_performance_profiling.py

# Test memory management
python scripts_dev/performance/run_memory_management.py

# Run optimization tests
python scripts_dev/performance/run_*_optimization.py
```

#### Validation Scripts:
```bash
# Run full system validation
python scripts_dev/validation/run_final_validation.py

# Run integration tests
python scripts_dev/validation/run_integration_tests.py
```

#### Utility Scripts:
```bash
# Check system components
python scripts_dev/utilities/check_*.py

# Run debugging tools
python scripts_dev/utilities/debug_*.py

# Test simple scenarios
python scripts_dev/utilities/simple_*.py
```

### 📋 Script Categories

#### **Setup & Configuration:**
- Database initialization
- Environment setup
- Configuration validation

#### **Testing & Validation:**
- Component testing
- Integration validation
- Performance benchmarking

#### **Debugging & Diagnostics:**
- System debugging
- Error investigation
- Health checks

#### **Development Utilities:**
- Code generation helpers
- Migration tools
- Data conversion scripts

### 🔧 Development Workflow

1. **Initial Setup:**
   ```bash
   python scripts_dev/database/create_test_db.py
   python scripts_dev/utilities/check_translations.py
   ```

2. **Development Testing:**
   ```bash
   python scripts_dev/validation/run_integration_tests.py
   python scripts_dev/performance/run_performance_profiling.py
   ```

3. **Pre-commit Validation:**
   ```bash
   python scripts_dev/validation/run_final_validation.py
   ```

### ⚠️ Important Notes

#### **Environment Requirements:**
- These scripts are for development use only
- Some scripts require test databases
- Performance scripts may impact system resources

#### **Safety Considerations:**
- Database scripts may modify test data
- Performance scripts may consume significant resources
- Always backup important data before running scripts

#### **Dependencies:**
- Scripts may have specific requirements
- Check individual script documentation
- Ensure proper Python environment setup

### 🆘 Troubleshooting

#### **Common Issues:**

**Import Errors:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts_dev/path/to/script.py
```

**Database Connection Issues:**
```bash
python scripts_dev/database/check_db.py
```

**Performance Test Failures:**
```bash
python scripts_dev/utilities/simple_test.py
```

### 📝 Best Practices

1. **Always test scripts in development environment first**
2. **Check script documentation before running**
3. **Monitor system resources during performance tests**
4. **Keep development data separate from production**
5. **Regular cleanup of test artifacts**

---

**Note:** These scripts support the development workflow and should not be used in production environments. 