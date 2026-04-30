"""CLI display formatting using tabulate.

Renders portfolio data, comparisons, and account info as terminal tables.
No business logic — display only.
"""

import sys

from tabulate import tabulate

from growgrow.bonds import current_yield, days_to_maturity, load_bond_metadata
from growgrow.portfolio import PortfolioSummary, Position
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
    """Print portfolio positions grouped by asset type and currency."""
    if not summary.positions:
        print("No positions found.")
        return

    bond_meta = load_bond_metadata()

    # Group: equity first, bond second; within each type sort currencies alphabetically
    type_order = ["equity", "bond"]
    groups: dict[str, dict[str, list]] = {"equity": {}, "bond": {}}
    for p in summary.positions:
        groups.setdefault(p.asset_type, {}).setdefault(p.currency, []).append(p)

    for asset_type in type_order:
        currencies = groups.get(asset_type, {})
        if not currencies:
            continue
        type_label = asset_type.capitalize()
        for currency in sorted(currencies.keys()):
            positions = sorted(currencies[currency], key=lambda p: p.market_value, reverse=True)
            print(f"{BOLD}── {type_label} / {currency} ──{RESET}")
            if asset_type == "bond":
                _display_bond_group(positions, summary, bond_meta)
            else:
                _display_equity_group(positions, summary)
            print()

    _display_totals(summary)


def _display_equity_group(positions: list[Position], summary: PortfolioSummary) -> None:
    """Print equity positions with P&L-focused columns."""
    headers = ["Ticker", "Name", "Qty", "Avg Price", "Price", "Value", "P&L", "P&L %", "Wt% (ccy)"]
    rows = []
    for p in positions:
        pnl_str = _colorize_pnl(p.unrealized_pnl, f"{p.unrealized_pnl:+,.2f}")
        pnl_pct_str = _colorize_pnl(p.pnl_pct, f"{p.pnl_pct:+.2f}%")
        weight = summary.weight(p)
        rows.append([
            p.ticker,
            p.name[:20],
            f"{p.quantity:g}",
            f"{p.avg_price:,.2f}",
            f"{p.current_price:,.2f}",
            f"{p.market_value:,.2f}",
            pnl_str,
            pnl_pct_str,
            f"{weight:.1f}%",
        ])
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def _display_bond_group(
    positions: list[Position],
    summary: PortfolioSummary,
    bond_meta: dict,
) -> None:
    """Print bond positions with income-focused columns.

    Columns: Ticker, Name, Qty, Price%, Value, Coupon%, Curr.Yield, Accrued, Maturity, Days
    """
    _FREQ_SHORT = {"monthly": "M", "quarterly": "Q", "semi-annual": "S", "annual": "A"}

    headers = [
        "Ticker", "Name", "Qty", "Price%", "Value",
        "Coupon%", "Freq", "Curr.Yield", "Accrued", "Maturity", "Days",
    ]
    rows = []
    for p in positions:
        meta = bond_meta.get(p.ticker, {})
        face_val = float(meta.get("face_value") or 100)
        coupon_rate = meta.get("coupon_rate")
        maturity_str = meta.get("maturity_date")

        price_pct = (p.current_price / face_val * 100) if face_val else 0.0
        price_pct_fmt = f"{price_pct:.2f}%"

        cy = current_yield(coupon_rate, p.current_price, face_val) if coupon_rate else None
        cy_fmt = f"{cy:.2f}%" if cy is not None else "—"

        coupon_fmt = f"{coupon_rate:.1f}%" if coupon_rate is not None else "—"
        freq_fmt = _FREQ_SHORT.get(meta.get("coupon_frequency", ""), "—")

        accrued_total = p.accrued_per_unit * p.quantity
        accrued_fmt = f"{accrued_total:,.0f}" if accrued_total else "—"

        if maturity_str:
            days = days_to_maturity(maturity_str)
            maturity_fmt = maturity_str
            days_fmt = _colorize_pnl(-days, str(days)) if days <= 30 else str(days)
        else:
            maturity_fmt = "—"
            days_fmt = "—"

        rows.append([
            p.ticker,
            p.name[:20],
            f"{p.quantity:g}",
            price_pct_fmt,
            f"{p.market_value:,.0f}",
            coupon_fmt,
            freq_fmt,
            cy_fmt,
            accrued_fmt,
            maturity_fmt,
            days_fmt,
        ])
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def _format_native(amount: float, currency: str) -> str:
    """Currency-aware formatting: KZT → integer, others → 2 decimals."""
    if currency == "KZT":
        return f"{amount:,.0f}"
    return f"{amount:,.2f}"


def _display_totals(summary: PortfolioSummary) -> None:
    """Print portfolio totals with currency and asset-type breakdowns."""
    print(f"{BOLD}Portfolio Summary{RESET}")
    print(f"  Positions:    {summary.position_count}")

    total_usd = summary.total_market_value_usd()
    if total_usd is None or total_usd == 0:
        # FX rates missing — fall back to native-only view
        print()
        print(f"  {BOLD}By Currency (no FX rates available):{RESET}")
        by_ccy = summary.market_value_by_currency()
        for ccy in sorted(by_ccy.keys()):
            print(f"    {ccy:<5} {_format_native(by_ccy[ccy], ccy):>14}")
        print()
        print(f"  As of:        {summary.timestamp:%Y-%m-%d %H:%M}")
        return

    print(f"  Total (USD):  ${total_usd:,.2f}")
    print()

    # Currency breakdown — sorted by USD-equivalent share descending
    print(f"  {BOLD}By Currency:{RESET}")
    by_ccy = summary.market_value_by_currency()
    ccy_rows = []
    for ccy, native_total in by_ccy.items():
        usd_equiv = summary.to_usd(native_total, ccy)
        if usd_equiv is None:
            continue
        ccy_rows.append((ccy, native_total, usd_equiv, usd_equiv / total_usd * 100))
    ccy_rows.sort(key=lambda r: r[2], reverse=True)
    for ccy, native_total, usd_equiv, pct in ccy_rows:
        native_fmt = _format_native(native_total, ccy)
        print(f"    {ccy:<5} {native_fmt:>14}   {pct:5.1f}%   (${usd_equiv:,.2f})")
    print()

    # Asset type breakdown
    print(f"  {BOLD}By Asset Type:{RESET}")
    by_type = summary.market_value_by_asset_type_usd()
    type_rows = sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)
    for asset_type, usd_total in type_rows:
        pct = usd_total / total_usd * 100
        label = asset_type.capitalize()
        print(f"    {label:<7} ${usd_total:>10,.2f}   {pct:5.1f}%")
    print()

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
