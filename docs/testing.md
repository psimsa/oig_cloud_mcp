# Testing Documentation

## Overview

The OIG Cloud MCP Server includes a comprehensive testing suite with unit tests, integration tests, and automated CI/CD pipeline to ensure code quality and prevent regressions.

## Test Structure

```
tests/
├── __init__.py
├── test_transformer.py      # Unit tests for data transformation logic
├── test_security.py          # Unit tests for security components
└── test_tools_integration.py # Integration tests for tool endpoints
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Specific Test Files

```bash
pytest tests/test_transformer.py
pytest tests/test_security.py
pytest tests/test_tools_integration.py
```

### Run Specific Test Classes or Methods

```bash
pytest tests/test_transformer.py::TestTransformGetStats
pytest tests/test_security.py::TestRateLimiter::test_lockout_after_max_failures
```

## Test Coverage

### Unit Tests

#### `test_transformer.py`
- Tests for `_create_data_point` helper function
- Tests for `_transform_solar`, `_transform_battery`, `_transform_household` functions
- Tests for main `transform_get_stats` function with various input scenarios:
  - Complete sample response
  - Empty/None inputs
  - Malformed data
  - Missing keys

#### `test_security.py`
- **Whitelist Tests:**
  - Email validation (allowed/rejected)
  - Case insensitivity
  - Comment handling in whitelist file
  - Missing file handling
  
- **RateLimiter Tests:**
  - Initial access without failures
  - Lockout after maximum failures
  - Success resets failure count
  - User isolation
  - Lockout expiration
  - Exponential backoff behavior

### Integration Tests

#### `test_tools_integration.py`
Tests all tool endpoints with mocked API calls:

- **get_basic_data:**
  - Success with valid authentication
  - Missing authentication headers
  - Whitelist enforcement

- **get_extended_data:**
  - Success with valid date parameters
  
- **get_notifications:**
  - Success scenario
  
- **set_box_mode (write action):**
  - Success with write access enabled
  - Denied in readonly mode
  - Denied without explicit readonly header override

- **set_grid_delivery (write action):**
  - Success with write access enabled
  - Denied in readonly mode

## Code Quality Checks

### Linting with flake8

```bash
# Critical checks (syntax errors)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Full check
flake8 . --count --statistics
```

### Code Formatting with black

```bash
# Check formatting
black --check .

# Apply formatting
black .
```

### Static type checking (mypy)

We use mypy for project-wide static type checking. Configuration is in [`setup.cfg:1`](setup.cfg:1) and local stubs are located in [`stubs/`](stubs:1).

- Install developer dependencies (includes mypy and type-stub packages listed in [`requirements-dev.txt:1`](requirements-dev.txt:1)):

```bash
pip install -r requirements-dev.txt
```

- Run mypy locally:

```bash
python -m mypy --config-file=setup.cfg
```

- Add missing third-party type stubs:
  - Prefer published `types-*` packages (add them to [`requirements-dev.txt:1`](requirements-dev.txt:1)).
  - If no published stub exists, add a minimal `.pyi` file to the [`stubs/`](stubs:1) directory and update `setup.cfg` (we already set `mypy_path = stubs`).

- Integrate mypy into pre-commit (we added [`.pre-commit-config.yaml:1`](.pre-commit-config.yaml:1)):
  1. Install pre-commit:
  
```bash
pip install pre-commit
pre-commit install
```

  2. Run hooks on all files (first-time check):

```bash
pre-commit run --all-files
```

CI notes:
- The GitHub Actions workflow already runs mypy in CI at [`.github/workflows/ci.yml:42`](.github/workflows/ci.yml:42). Ensure CI installs dev dependencies (`requirements-dev.txt`) so mypy and any `types-*` packages are available during the check.

Recommended everyday workflow:
- Run tests and type-check before pushing:

```bash
pip install -r requirements-dev.txt
pre-commit run --all-files
pytest -q
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that automatically:

1. Runs on every push/PR to `main` and `develop` branches
2. Tests against Python 3.13
3. Installs all dependencies
4. Runs flake8 linting checks
5. Validates code formatting with black
6. Executes the full pytest suite

### Workflow Configuration

```yaml
name: Python CI

on:
  push:
    branches: [ "main", "develop" ]
  pull_request:
    branches: [ "main", "develop" ]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
  python-version: ["3.13"]
```

## Test Fixtures and Mocking

The integration tests use `pytest-mock` to mock external dependencies:

- **mock_whitelist**: Mocks the whitelist to allow test users
- **mock_rate_limiter**: Mocks rate limiting to allow all requests
- **mock_session_cache**: Provides a fake API client with mocked responses
- **mock_context**: Creates mock FastMCP context objects with various header configurations

## Best Practices

1. **Run tests before committing**: Ensure all tests pass locally
2. **Write tests for new features**: Maintain high test coverage
3. **Use mocks for external APIs**: Keep tests fast and isolated
4. **Follow naming conventions**: Test files start with `test_`, test classes with `Test`, test functions with `test_`
5. **Test edge cases**: Include tests for error conditions, empty inputs, and boundary conditions

## Continuous Improvement

- Tests are designed to be maintainable and readable
- Mocking strategy prevents external API calls during testing
- CI/CD ensures consistent quality across all contributions
- Black formatting ensures consistent code style
