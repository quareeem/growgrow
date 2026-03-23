# GrowGrow

Portfolio tracker and analyzer for the Tradernet broker platform.

## Features (v0.1.0)

- Fetch and display portfolio positions with P&L tracking
- Save portfolio snapshots to timestamped CSV files
- Compare snapshots to track changes over time
- View account information
- CLI interface with subcommands

## Setup

```bash
# Clone and enter the project
cd growgrow

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package with dev dependencies
pip install -e ".[dev]"

# Set up API credentials
cp tradernet.ini.example tradernet.ini
# Edit tradernet.ini with your Tradernet API keys
```

Get your API keys from [tradernet.com](https://tradernet.com/tradernet-api/).

## Usage

```bash
growgrow portfolio          # Show current positions with P&L
growgrow snapshot           # Save portfolio snapshot to CSV
growgrow history            # List saved snapshots
growgrow compare            # Compare two most recent snapshots
growgrow compare --new 0 --old 2  # Compare specific snapshots
growgrow info               # Show account information
```

## Development

```bash
ruff check .    # Lint
ruff format .   # Format
pytest          # Run tests
```

## Architecture

```
growgrow/
├── config.py      # API key loading (ini file or env vars)
├── client.py      # Tradernet SDK wrapper (only file importing tradernet)
├── portfolio.py   # Position/PortfolioSummary dataclasses + P&L
├── snapshot.py    # CSV persistence + snapshot comparison
├── display.py     # CLI table formatting
└── cli.py         # Entry point with argparse subcommands
```

## Links

- [Tradernet API docs](https://tradernet.com/tradernet-api/)
- [Tradernet Python SDK](https://tradernet.com/tradernet-api/python-sdk)
- [tradernet-sdk on PyPI](https://pypi.org/project/tradernet-sdk/)
