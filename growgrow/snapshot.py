"""CSV snapshot persistence and historical comparison.

Saves portfolio snapshots to timestamped CSV files and provides
comparison between snapshots to track changes over time.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from growgrow.config import ensure_data_dir
from growgrow.portfolio import PortfolioSummary, Position

# Numeric columns that get currency-aware rounding
_PRICE_COLS = ("avg_price", "current_price", "cost_basis", "market_value", "unrealized_pnl")


def _round_position_row(row: dict[str, Any]) -> dict[str, Any]:
    """Round numeric fields based on currency to reduce float noise.

    KZT: round to integer (KZT ≈ 1/470 USD, sub-unit noise is irrelevant).
    USD/EUR: round to 1 decimal place.
    pnl_pct and weight_pct: always 1 decimal.
    """
    result = dict(row)
    is_kzt = row.get("currency") == "KZT"
    decimals = 0 if is_kzt else 1

    for col in _PRICE_COLS:
        if col in result and result[col] is not None:
            result[col] = round(float(result[col]), decimals)

    for col in ("pnl_pct", "weight_pct"):
        if col in result and result[col] is not None:
            result[col] = round(float(result[col]), 1)

    return result


def _build_subtotal_rows(summary: PortfolioSummary) -> list[dict[str, Any]]:
    """Build subtotal rows grouped by asset_type + currency."""
    groups: dict[tuple[str, str], list[Position]] = {}
    for p in summary.positions:
        key = (p.asset_type.upper(), p.currency)
        groups.setdefault(key, []).append(p)

    rows = []
    for (asset_type, currency) in sorted(groups.keys()):
        positions = groups[(asset_type, currency)]
        total_cost = sum(p.cost_basis for p in positions)
        total_value = sum(p.market_value for p in positions)
        total_pnl = total_value - total_cost
        pnl_pct = round((total_pnl / total_cost * 100) if total_cost else 0.0, 1)
        is_kzt = currency == "KZT"
        decimals = 0 if is_kzt else 1

        rows.append({
            "ticker": f"SUBTOTAL_{asset_type}_{currency}",
            "name": "",
            "quantity": "",
            "avg_price": "",
            "current_price": "",
            "currency": currency,
            "asset_type": asset_type.lower(),
            "cost_basis": round(total_cost, decimals),
            "market_value": round(total_value, decimals),
            "unrealized_pnl": round(total_pnl, decimals),
            "pnl_pct": pnl_pct,
            "weight_pct": "",
        })
    return rows


def save_snapshot(summary: PortfolioSummary) -> Path:
    """Save a portfolio snapshot to a timestamped CSV file.

    The CSV includes:
    - Comment header lines (# key: value) with snapshot metadata
    - Position rows with currency-aware rounded numbers
    - Subtotal rows grouped by asset_type + currency

    Args:
        summary: The portfolio summary to save.

    Returns:
        Path to the created CSV file.
    """
    data_dir = ensure_data_dir()
    timestamp = summary.timestamp.strftime("%Y-%m-%d_%H%M")
    filename = f"portfolio_{timestamp}.csv"
    filepath = data_dir / filename

    currencies = sorted({p.currency for p in summary.positions})
    rows = [
        _round_position_row(p.to_dict(weight_pct=round(summary.weight(p), 1)))
        for p in summary.positions
    ]

    with filepath.open("w", encoding="utf-8") as f:
        f.write(f"# snapshot_date: {summary.timestamp:%Y-%m-%d %H:%M}\n")
        f.write(f"# positions: {summary.position_count}\n")
        f.write(f"# currencies: {', '.join(currencies)}\n")

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, mode="a")

    subtotals = _build_subtotal_rows(summary)
    if subtotals:
        sub_df = pd.DataFrame(subtotals)
        sub_df.to_csv(filepath, index=False, header=False, mode="a")

    return filepath


def list_snapshots() -> list[Path]:
    """List all saved snapshot files, sorted by date (newest first)."""
    data_dir = ensure_data_dir()
    snapshots = sorted(data_dir.glob("portfolio_*.csv"), reverse=True)
    return snapshots


def load_snapshot(filepath: Path) -> PortfolioSummary:
    """Load a portfolio snapshot from a CSV file.

    Skips comment lines (starting with #) and subtotal rows.

    Args:
        filepath: Path to the CSV file.

    Returns:
        PortfolioSummary reconstructed from the CSV data.
    """
    df = pd.read_csv(filepath, comment="#")
    # Drop subtotal rows added during save
    df = df[~df["ticker"].str.startswith("SUBTOTAL", na=False)]

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
