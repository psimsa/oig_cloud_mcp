# Developer Quick Reference

## Quick Commands

### Testing
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_transformer.py

# Run specific test class
pytest tests/test_security.py::TestRateLimiter

# Run specific test
pytest tests/test_security.py::TestRateLimiter::test_lockout_after_max_failures
```

### Code Quality
```bash
# Check linting
flake8 .

# Check formatting (dry run)
black --check .

# Apply formatting
black .

# Run all checks
flake8 . && black --check . && pytest
```

### CI/CD
The GitHub Actions workflow runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

Tests against: Python 3.11 and 3.12

## Project Structure
```
tests/
├── test_transformer.py       # Unit tests for data transformation
├── test_security.py           # Unit tests for security components
└── test_tools_integration.py  # Integration tests with mocked APIs
```

## Test Count: 40 Total
- transformer.py: 25 tests
- security.py: 12 tests
- tools.py: 11 integration tests

## Configuration Files
- `.flake8` - Linting configuration
- `pytest.ini` - Test runner configuration
- `setup.cfg` - Additional tool configs
- `.github/workflows/ci.yml` - CI/CD pipeline

## Documentation
- `TESTING.md` - Comprehensive testing guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `README.md` - Main documentation with testing section

## Pre-Commit Checklist
- [ ] Run `pytest` - All tests pass
- [ ] Run `flake8 .` - No linting errors
- [ ] Run `black --check .` - Code is formatted
- [ ] Update tests if adding new features
- [ ] Update documentation if changing APIs
