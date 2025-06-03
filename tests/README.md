# Tests Directory Structure

## 📁 Organized Test Architecture for SDM v2.0

This directory contains all test files organized by functionality and purpose for better maintainability and clarity.

### 🎯 Directory Categories

#### `/database/`
**Database-related tests and migrations**
- Database schema tests
- Migration scripts and validation
- Data integrity checks
- Database optimization tests
- Connection and transaction tests

#### `/integration/`
**Cross-component integration tests**
- End-to-end workflow tests
- Component interaction tests
- Service integration validation
- System-level functionality tests

#### `/performance/`
**Performance and optimization tests**
- Benchmark tests
- Memory usage analysis
- Speed optimization validation
- Resource usage monitoring
- Load testing scenarios

#### `/platform/`
**Platform-specific tests**
- TikTok download functionality
- YouTube integration tests
- Platform detection and handling
- API interaction tests
- Content extraction validation

#### `/task_specific/`
**Task implementation validation**
- Individual task verification
- Subtask completion tests
- Task workflow validation
- Feature-specific testing
- Implementation milestone checks

#### `/ui/`
**User Interface tests**
- UI component testing
- Design system validation
- Accessibility compliance
- Responsiveness tests
- Visual consistency checks
- User interaction flows

#### `/unit/`
**Individual component unit tests**
- Isolated function testing
- Class method validation
- Utility function tests
- Core logic verification
- Edge case handling

#### `/validation/`
**Validation and error handling**
- Error scenarios testing
- Input validation checks
- Recovery procedure tests
- Data validation tests
- Security validation

### 🚀 Running Tests

#### Run all tests:
```bash
python -m pytest tests/
```

#### Run specific category:
```bash
python -m pytest tests/database/
python -m pytest tests/integration/
python -m pytest tests/performance/
```

#### Run with verbose output:
```bash
python -m pytest tests/ -v
```

#### Run with coverage:
```bash
python -m pytest tests/ --cov=.
```

### 📋 Test Naming Conventions

- **`test_*_integration.py`** - Integration tests
- **`test_*_performance.py`** - Performance tests  
- **`test_*_validation.py`** - Validation tests
- **`test_*_simple.py`** - Simplified/basic tests
- **`test_*_comprehensive.py`** - Full feature tests
- **`test_*_standalone.py`** - Isolated environment tests

### 🔧 Test Utilities

#### Shared test utilities in `/unit/`:
- Mock data generators
- Test fixtures
- Common test utilities
- Assertion helpers

#### Platform-specific utilities in `/platform/`:
- Mock API responses
- Test content samples
- Platform simulators

### 📊 Test Data

#### `/test_datasets/` and `/test_accessibility_standalone/`
- Sample test data
- Mock content files
- Test configuration files
- Reference data for validation

**Note:** Test data is excluded from git for size and privacy reasons.

### 🎯 Best Practices

1. **Isolation:** Each test should be independent
2. **Naming:** Use descriptive test names
3. **Coverage:** Aim for comprehensive test coverage
4. **Performance:** Keep tests fast and efficient
5. **Documentation:** Document complex test scenarios
6. **Cleanup:** Ensure proper test cleanup

### 🆘 Troubleshooting

#### Import Issues:
If you encounter import errors after reorganization:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Database Tests:
Make sure test database is properly set up:
```bash
python scripts_dev/database/create_test_db.py
```

#### Performance Tests:
Performance tests may require specific environment setup:
```bash
python scripts_dev/performance/setup_performance_env.py
```

---

**Note:** This organized structure improves test maintainability, discovery, and execution efficiency. 