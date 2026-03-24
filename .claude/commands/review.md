Run a quick code review check on the project. Execute these steps in order:

1. Run `ruff check .` to check for lint issues
2. Run `ruff format --check .` to verify formatting
3. Run `pytest -v` to run all tests

Summarize results as:
- PASS/FAIL for each step
- List any specific issues found
- Suggest fixes for any failures

All commands should use the project's venv: `source venv/bin/activate && ...`
