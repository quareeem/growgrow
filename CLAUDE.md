# CLAUDE.md - AI Agent Instructions for GrowGrow

## Project Overview
GrowGrow is a Python portfolio tracker/analyzer that connects to the Tradernet
broker API (tradernet.com). It fetches portfolio positions with P&L tracking,
saves snapshots to CSV, compares snapshots over time, and displays summaries
in the CLI.

## Quick Start
```bash
cd /Users/karimakhmediyev/VScodeProjects/growgrow
source venv/bin/activate
pip install -e ".[dev]"
cp tradernet.ini.example tradernet.ini  # then fill in real API keys
growgrow portfolio
```

## Architecture
```
cli.py  →  client.py  →  tradernet-sdk (external)
  │            │
  ▼            ▼
display.py   portfolio.py  →  snapshot.py  →  data/*.csv
                 │
              config.py  →  tradernet.ini / env vars
```

## Module Responsibilities
- `config.py` - Loads API keys from tradernet.ini or env vars. Single source
  of truth for configuration.
- `client.py` - Thin wrapper around tradernet-sdk. ONLY file that imports from
  the `tradernet` package. All API calls go through here.
- `portfolio.py` - Dataclasses (Position, PortfolioSummary) and transformation
  logic. Includes P&L calculation. Pure Python, no API calls.
- `snapshot.py` - CSV read/write to data/ directory. Uses pandas. Includes
  compare_snapshots() for historical comparison.
- `display.py` - CLI table formatting with tabulate. No business logic.
- `cli.py` - argparse entry point. Wires everything together.

## Conventions
- Python 3.11, type hints on all functions
- Docstrings on all public functions (Google style)
- One class/concern per file, files under 150 lines
- Use dataclasses, not dicts, for structured data
- Ruff for linting and formatting
- Tests in tests/ using pytest

## Config / Secrets
- API keys in `tradernet.ini` (NEVER commit this file)
- Format: `[auth]` section with `public` and `private` keys (matches tradernet-sdk's from_config)
- Template in `tradernet.ini.example`
- Fallback to env vars: TRADERNET_PUBLIC_KEY, TRADERNET_PRIVATE_KEY
- Data snapshots in data/ (gitignored, only .gitkeep is committed)

## Tradernet SDK Key Methods
- `account_summary()` → portfolio positions (getPositionJson)
- `user_info()` → account info (GetAllUserTexInfo)
- `get_placed(active=True)` → orders
- `get_quotes(symbols)` → current quotes
- `get_candles(symbol, start, end, timeframe)` → historical OHLCV
- `Tradernet.from_config("tradernet.ini")` → auth from config file

## Common Commands
```bash
growgrow portfolio          # show current positions with P&L
growgrow snapshot           # save snapshot to CSV
growgrow history            # list saved snapshots
growgrow compare            # compare latest vs previous snapshot
growgrow info               # show account info
ruff check .                # lint
ruff format .               # format
pytest                      # run tests
```

## Adding New Features
When extending this project, follow these patterns:
1. New data sources → add a new module (e.g., `market.py`, `watchlist.py`)
2. New CLI commands → add subcommand in `cli.py`, logic in dedicated module
3. New display formats → extend `display.py` or add `viz.py` for graphical output
4. Keep `client.py` as the only gateway to external APIs
5. All new data models should be dataclasses in their own module

## Planned Future Extensions
- Visualization (Plotly/Dash)
- Watchlist tracking (stocks not yet owned)
- LLM analysis (Claude/GPT suggestions)
- Market data parsing (daily OHLCV, technical indicators)
- Batch processing (PySpark)
- News/sentiment analysis
