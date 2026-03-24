# Security Rules

## Secrets & Credentials
- NEVER hardcode API keys, tokens, passwords, or secrets in source code
- All credentials loaded via `growgrow/config.py` (tradernet.ini or env vars)
- NEVER commit `tradernet.ini`, `.env`, or any file containing real credentials
- Check `.gitignore` includes credential files before committing

## Dangerous Functions
- NEVER use `eval()` or `exec()` on any input
- NEVER use `pickle.loads()` or `yaml.load()` without safe loader on untrusted data
- Use `subprocess.run(["cmd", "arg"], ...)` with list args — NEVER `shell=True` with user input
- No `os.system()` — use `subprocess` instead

## Path Safety
- Validate file paths — reject paths containing `..`
- Use `pathlib.Path.resolve()` to canonicalize paths before operations
- Restrict file operations to known directories (DATA_DIR, PROJECT_ROOT)

## Dependencies
- Pin major versions in pyproject.toml
- Review new dependencies before adding — prefer well-maintained packages
- Don't install packages from untrusted sources

## Error Messages
- Don't expose stack traces, internal paths, or credentials in user-facing error messages
- Log detailed errors internally, show sanitized messages to users
