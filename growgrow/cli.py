"""CLI entry point for GrowGrow.

Provides subcommands for portfolio tracking, snapshots, and comparison.
"""

import argparse
import sys

from growgrow import __version__


def cmd_portfolio(args: argparse.Namespace) -> None:
    """Fetch and display current portfolio with P&L."""
    from growgrow.client import create_client, fetch_portfolio
    from growgrow.display import display_portfolio
    from growgrow.portfolio import parse_positions

    client = create_client()
    raw = fetch_portfolio(client)
    summary = parse_positions(raw)
    display_portfolio(summary)


def cmd_snapshot(args: argparse.Namespace) -> None:
    """Fetch portfolio and save to CSV snapshot."""
    from growgrow.client import create_client, fetch_portfolio
    from growgrow.display import display_portfolio
    from growgrow.portfolio import parse_positions
    from growgrow.snapshot import save_snapshot

    client = create_client()
    raw = fetch_portfolio(client)
    summary = parse_positions(raw)
    filepath = save_snapshot(summary)
    display_portfolio(summary)
    print(f"\nSnapshot saved to: {filepath}")


def cmd_history(args: argparse.Namespace) -> None:
    """List saved snapshots."""
    from growgrow.display import display_snapshot_list
    from growgrow.snapshot import list_snapshots

    snapshots = list_snapshots()
    display_snapshot_list(snapshots)


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare two portfolio snapshots."""
    from growgrow.display import display_comparison
    from growgrow.snapshot import compare_snapshots, list_snapshots, load_snapshot

    snapshots = list_snapshots()
    if len(snapshots) < 2:
        print("Need at least 2 snapshots to compare.")
        print("Run 'growgrow snapshot' to create snapshots.")
        sys.exit(1)

    # Default: compare two most recent snapshots
    idx_new = args.new if args.new is not None else 0
    idx_old = args.old if args.old is not None else 1

    if idx_new >= len(snapshots) or idx_old >= len(snapshots):
        print(f"Invalid snapshot index. Available: 0-{len(snapshots) - 1}")
        sys.exit(1)

    new_snapshot = load_snapshot(snapshots[idx_new])
    old_snapshot = load_snapshot(snapshots[idx_old])

    changes = compare_snapshots(new_snapshot, old_snapshot)
    display_comparison(
        changes,
        old_label=snapshots[idx_old].stem.replace("portfolio_", ""),
        new_label=snapshots[idx_new].stem.replace("portfolio_", ""),
    )


def cmd_info(args: argparse.Namespace) -> None:
    """Show account information."""
    from growgrow.client import create_client, fetch_user_info
    from growgrow.display import display_user_info

    client = create_client()
    info = fetch_user_info(client)
    display_user_info(info)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="growgrow",
        description="Portfolio tracker and analyzer for Tradernet",
    )
    parser.add_argument("--version", action="version", version=f"growgrow {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # portfolio
    subparsers.add_parser("portfolio", help="Show current portfolio with P&L")

    # snapshot
    subparsers.add_parser("snapshot", help="Save portfolio snapshot to CSV")

    # history
    subparsers.add_parser("history", help="List saved snapshots")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare two snapshots")
    compare_parser.add_argument(
        "--new",
        type=int,
        default=None,
        help="Index of newer snapshot (0=most recent, default: 0)",
    )
    compare_parser.add_argument(
        "--old",
        type=int,
        default=None,
        help="Index of older snapshot (0=most recent, default: 1)",
    )

    # info
    subparsers.add_parser("info", help="Show account information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "portfolio": cmd_portfolio,
        "snapshot": cmd_snapshot,
        "history": cmd_history,
        "compare": cmd_compare,
        "info": cmd_info,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
