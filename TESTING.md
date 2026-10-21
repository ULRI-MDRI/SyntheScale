# Testing

## Overview

This document outlines the testing strategy and conventions for this repository.

## Test Structure

```
tests/
├── unit/         # Unit tests for individual components
├── integration/  # Integration tests across multiple components
└── e2e/          # End-to-end tests
```

## Running Tests

```bash
# Run all tests
[test command]

# Run unit tests only
[unit test command]

# Run integration tests only
[integration test command]
```

## Writing Tests

- Place tests in the `tests/` directory, mirroring the structure of `src/`
- Name test files with the suffix `.test.[ext]` or `.spec.[ext]`
- Each test should be independent and not rely on external state
- Use descriptive test names that explain the expected behaviour

## CI Integration

All tests are run automatically on every pull request. A pull request may not be merged unless:
- All tests pass
- No regressions are introduced

See [CONVENTIONS.md](CONVENTIONS.md) for branching and code review requirements.
