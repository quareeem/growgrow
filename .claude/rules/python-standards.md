# Python Coding Standards

## Type Hints
- Type hints on ALL public function signatures
- Use specific types, avoid `Any` where possible
- Use `Optional[X]` or `X | None` for nullable parameters
- Use `Sequence`, `Mapping` for read-only collection params

## Code Structure
- Functions: max 50 lines, max 5 parameters, max 4 nesting levels
- One class/concern per module
- Extract magic numbers to named constants
- Use Enum instead of magic strings/numbers

## Pythonic Patterns
- List/dict/set comprehensions over imperative loops where clearer
- `isinstance()` not `type() ==`
- `"".join()` for string building
- `is None` not `== None`
- Avoid mutable default arguments (use `None` then assign inside)
- Don't shadow built-in names (list, dict, id, type, etc.)

## Error Handling
- Never use bare `except:` — always catch specific exception types
- Use context managers (`with`) for resource management (files, connections)
- Log exceptions, don't silently swallow them
- Raise meaningful errors with clear messages

## Imports
- Group: stdlib → third-party → local, separated by blank lines
- No wildcard imports (`from x import *`)
- Ruff handles import sorting (isort rules enabled)

## Formatting & Linting
- Ruff for linting AND formatting (do NOT use black or isort separately)
- Line length: 100 (configured in pyproject.toml)
- Run `ruff check .` and `ruff format .` before committing

## Docstrings
- Google style docstrings on all public functions and classes
- Include Args, Returns, Raises sections where applicable
- Keep docstrings concise — don't restate what's obvious from the signature

## Output
- Use `print()` only for CLI user-facing output (in display.py, cli.py)
- Use `logging` module for debug/info/warning messages in library code
