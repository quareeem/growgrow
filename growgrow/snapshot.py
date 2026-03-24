"""CSV snapshot persistence and historical comparison.

Saves portfolio snapshots to timestamped CSV files and provides
comparison between snapshots to track changes over time.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from growgrow.config import ensure_data_dir
from growgrow.portfolio import PortfolioSummary, Position


def save_snapshot(summary: PortfolioSummary) -> Path:
    """Save a portfolio snapshot to a timestamped CSV file.

    Args:
        summary: The portfolio summary to save.

    Returns:
        Path to the created CSV file.
    """
    data_dir = ensure_data_dir()
    timestamp = summary.timestamp.strftime("%Y-%m-%d_%H%M")
    filename = f"portfolio_{timestamp}.csv"
    filepath = data_dir / filename

    rows = [p.to_dict() for p in summary.positions]
    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)
    return filepath


def list_snapshots() -> list[Path]:
    """List all saved snapshot files, sorted by date (newest first)."""
    data_dir = ensure_data_dir()
    snapshots = sorted(data_dir.glob("portfolio_*.csv"), reverse=True)
    return snapshots


def load_snapshot(filepath: Path) -> PortfolioSummary:
    """Load a portfolio snapshot from a CSV file.

    Args:
        filepath: Path to the CSV file.

    Returns:
        PortfolioSummary reconstructed from the CSV data.
    """
    df = pd.read_csv(filepath)
    positions = []
    for _, row in df.iterrows():
        positions.append(
            Position(
                ticker=row["ticker"],
                name=row.get("name", row["ticker"]),
                quantity=float(row["quantity"]),
                avg_price=float(row["avg_price"]),
                current_price=float(row["current_price"]),
                currency=row.get("currency", "USD"),
                asset_type=row.get("asset_type", "equity"),
            )
        )

    # Parse timestamp from filename: portfolio_YYYY-MM-DD_HHMM.csv
    stem = filepath.stem  # portfolio_2026-03-17_1430
    ts_str = stem.replace("portfolio_", "")
    try:
        timestamp = datetime.strptime(ts_str, "%Y-%m-%d_%H%M")
    except ValueError:
        timestamp = datetime.fromtimestamp(filepath.stat().st_mtime)

    return PortfolioSummary(positions=positions, timestamp=timestamp)


@dataclass
class PositionChange:
    """Describes how a single position changed between two snapshots."""

    ticker: str
    name: str
    status: str  # "added", "removed", "changed", "unchanged"
    old_quantity: float = 0.0
    new_quantity: float = 0.0
    old_price: float = 0.0
    new_price: float = 0.0
    old_value: float = 0.0
    new_value: float = 0.0
    value_change: float = 0.0
    price_change_pct: float = 0.0


def compare_snapshots(
    current: PortfolioSummary, previous: PortfolioSummary
) -> list[PositionChange]:
    """Compare two portfolio snapshots and return a list of changes.

    Args:
        current: The newer portfolio snapshot.
        previous: The older portfolio snapshot.

    Returns:
        List of PositionChange objects describing what changed.
    """
    prev_map = {p.ticker: p for p in previous.positions}
    curr_map = {p.ticker: p for p in current.positions}
    all_tickers = sorted(set(prev_map.keys()) | set(curr_map.keys()))
    changes = []

    for ticker in all_tickers:
        old = prev_map.get(ticker)
        new = curr_map.get(ticker)

        if new and not old:
            changes.append(
                PositionChange(
                    ticker=ticker,
                    name=new.name,
                    status="added",
                    new_quantity=new.quantity,
                    new_price=new.current_price,
                    new_value=new.market_value,
                    value_change=new.market_value,
                )
            )
        elif old and not new:
            changes.append(
                PositionChange(
                    ticker=ticker,
                    name=old.name,
                    status="removed",
                    old_quantity=old.quantity,
                    old_price=old.current_price,
                    old_value=old.market_value,
                    value_change=-old.market_value,
                )
            )
        elif old and new:
            price_change_pct = 0.0
            if old.current_price != 0:
                price_change_pct = (
                    (new.current_price - old.current_price) / old.current_price
                ) * 100

            status = "unchanged"
            if old.quantity != new.quantity or abs(old.current_price - new.current_price) > 0.001:
                status = "changed"

            changes.append(
                PositionChange(
                    ticker=ticker,
                    name=new.name,
                    status=status,
                    old_quantity=old.quantity,
                    new_quantity=new.quantity,
                    old_price=old.current_price,
                    new_price=new.current_price,
                    old_value=old.market_value,
                    new_value=new.market_value,
                    value_change=new.market_value - old.market_value,
                    price_change_pct=price_change_pct,
                )
            )

    return changes
