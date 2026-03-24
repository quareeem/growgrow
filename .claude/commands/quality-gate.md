Run a full quality gate validation on the project. This is a thorough check before committing or pushing.

Execute ALL of these checks using the project's venv (`source venv/bin/activate`):

1. **Lint**: `ruff check .`
2. **Format**: `ruff format --check .`
3. **Tests**: `pytest -v --tb=short`
4. **Coverage**: `pytest --cov=growgrow --cov-report=term-missing` (if pytest-cov is installed, otherwise skip)
5. **Security scan**: Check for any hardcoded secrets or credentials in tracked files: `git grep -n -i "password\|secret\|api_key\|private_key" -- '*.py'`

Present a final summary table:

| Check | Status | Details |
|-------|--------|---------|
| Lint | PASS/FAIL | ... |
| Format | PASS/FAIL | ... |
| Tests | PASS/FAIL | X/Y passed |
| Coverage | X% | ... |
| Secrets | PASS/FAIL | ... |

If ALL checks pass, print: "Quality gate PASSED — safe to commit."
If ANY check fails, print: "Quality gate FAILED — fix issues before committing." and list what needs fixing.
