"""CLI display formatting using tabulate.

Renders portfolio data, comparisons, and account info as terminal tables.
No business logic — display only.
"""

import sys

from tabulate import tabulate

from growgrow.portfolio import PortfolioSummary
from growgrow.snapshot import PositionChange

# ANSI color codes (disabled if not a TTY)
_USE_COLOR = sys.stdout.isatty()
GREEN = "\033[32m" if _USE_COLOR else ""
RED = "\033[31m" if _USE_COLOR else ""
RESET = "\033[0m" if _USE_COLOR else ""
BOLD = "\033[1m" if _USE_COLOR else ""


def _colorize_pnl(value: float, formatted: str) -> str:
    """Color a P&L value green (positive) or red (negative)."""
    if value > 0:
        return f"{GREEN}{formatted}{RESET}"
    elif value < 0:
        return f"{RED}{formatted}{RESET}"
    return formatted


def display_portfolio(summary: PortfolioSummary) -> None:
    """Print portfolio positions as a formatted table with P&L."""
    if not summary.positions:
        print("No positions found.")
        return

    headers = ["Ticker", "Name", "Qty", "Avg Price", "Price", "Value", "P&L", "P&L %", "Weight %"]
    rows = []

    for p in summary.positions:
        pnl_str = _colorize_pnl(p.unrealized_pnl, f"{p.unrealized_pnl:+,.2f}")
        pnl_pct_str = _colorize_pnl(p.pnl_pct, f"{p.pnl_pct:+.2f}%")
        weight = summary.weight(p)

        rows.append(
            [
                p.ticker,
                p.name[:20],
                f"{p.quantity:g}",
                f"{p.avg_price:,.2f}",
                f"{p.current_price:,.2f}",
                f"{p.market_value:,.2f}",
                pnl_str,
                pnl_pct_str,
                f"{weight:.1f}%",
            ]
        )

    print(tabulate(rows, headers=headers, tablefmt="simple"))
    print()
    _display_totals(summary)


def _display_totals(summary: PortfolioSummary) -> None:
    """Print portfolio totals."""
    pnl_str = _colorize_pnl(summary.total_unrealized_pnl, f"{summary.total_unrealized_pnl:+,.2f}")
    pnl_pct_str = _colorize_pnl(summary.total_pnl_pct, f"{summary.total_pnl_pct:+.2f}%")
    print(f"{BOLD}Portfolio Summary{RESET}")
    print(f"  Positions:    {summary.position_count}")
    print(f"  Cost Basis:   {summary.total_cost_basis:,.2f}")
    print(f"  Market Value: {summary.total_market_value:,.2f}")
    print(f"  Total P&L:    {pnl_str} ({pnl_pct_str})")
    print(f"  As of:        {summary.timestamp:%Y-%m-%d %H:%M}")


def display_comparison(changes: list[PositionChange], old_label: str, new_label: str) -> None:
    """Print a comparison of two portfolio snapshots."""
    if not changes:
        print("No changes found.")
        return

    print(f"{BOLD}Comparison: {old_label} -> {new_label}{RESET}")
    print()

    headers = [
        "Status",
        "Ticker",
        "Name",
        "Old Qty",
        "New Qty",
        "Old Price",
        "New Price",
        "Price %",
        "Value Change",
    ]
    rows = []

    for c in changes:
        if c.status == "unchanged":
            continue

        status_display = {
            "added": f"{GREEN}+ added{RESET}",
            "removed": f"{RED}- removed{RESET}",
            "changed": "~ changed",
        }.get(c.status, c.status)

        price_pct = _colorize_pnl(c.price_change_pct, f"{c.price_change_pct:+.2f}%")
        val_change = _colorize_pnl(c.value_change, f"{c.value_change:+,.2f}")

        rows.append(
            [
                status_display,
                c.ticker,
                c.name[:20],
                f"{c.old_quantity:g}" if c.old_quantity else "-",
                f"{c.new_quantity:g}" if c.new_quantity else "-",
                f"{c.old_price:,.2f}" if c.old_price else "-",
                f"{c.new_price:,.2f}" if c.new_price else "-",
                price_pct if c.price_change_pct else "-",
                val_change,
            ]
        )

    if rows:
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        print("No changes between snapshots.")

    # Summary
    total_change = sum(c.value_change for c in changes)
    added = sum(1 for c in changes if c.status == "added")
    removed = sum(1 for c in changes if c.status == "removed")
    changed = sum(1 for c in changes if c.status == "changed")
    print()
    print(f"  Added: {added}  Removed: {removed}  Changed: {changed}")
    print(f"  Total value change: {_colorize_pnl(total_change, f'{total_change:+,.2f}')}")


def display_snapshot_list(snapshots: list) -> None:
    """Print a list of saved snapshot files."""
    if not snapshots:
        print("No snapshots found. Run 'growgrow snapshot' to create one.")
        return

    print(f"{BOLD}Saved Snapshots{RESET}")
    for i, path in enumerate(snapshots, 1):
        ts_str = path.stem.replace("portfolio_", "")
        print(f"  {i}. {ts_str}  ({path.name})")


def display_user_info(info: dict) -> None:
    """Print user account info as key-value pairs."""
    if not info:
        print("No user info available.")
        return

    print(f"{BOLD}Account Info{RESET}")
    for key, value in info.items():
        if isinstance(value, (dict, list)):
            continue  # Skip nested structures for now
        print(f"  {key}: {value}")
