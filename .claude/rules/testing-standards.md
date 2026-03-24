# Testing Standards

## Framework
- pytest (configured in pyproject.toml)
- Run with: `pytest` or `pytest -v` for verbose

## Test Organization
- Mirror source structure: `growgrow/foo.py` → `tests/test_foo.py`
- Group related tests in classes: `class TestPosition:`, `class TestParsePositions:`
- Use `pytest.mark` decorators for categorization when needed (`@pytest.mark.unit`, `@pytest.mark.integration`)

## Test Structure (AAA Pattern)
```python
def test_something():
    # Arrange — set up test data and dependencies
    position = Position("AAPL", "Apple", 10, 150.0, 175.0)

    # Act — call the code under test
    result = position.unrealized_pnl

    # Assert — verify the result
    assert result == 250.0
```

## Fixtures
- Use `@pytest.fixture` for reusable test data
- Use `tmp_path` for file system tests
- Use `monkeypatch` to override config/env vars

## Mocking Strategy
- Mock external dependencies (tradernet-sdk API calls) — never make real API calls in tests
- Test business logic (portfolio.py, snapshot.py) with fixture data
- Use `unittest.mock.patch` or `monkeypatch` for dependency injection

## Coverage Target
- 80%+ coverage on business logic (portfolio.py, snapshot.py)
- CLI (cli.py) and display (display.py) tested via integration or manually
- Run coverage: `pytest --cov=growgrow --cov-report=term-missing`

## What to Test
- Happy path + edge cases (empty data, zero values, missing fields)
- Data transformations (parse_positions, compare_snapshots)
- CSV roundtrips (save → load → verify)
- Error conditions (missing config, invalid data)
