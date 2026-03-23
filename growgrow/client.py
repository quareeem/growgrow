"""Thin wrapper around tradernet-sdk.

This is the ONLY module that imports from the tradernet package.
All API calls go through here.
"""

from typing import Any

from tradernet import Tradernet

from growgrow.config import get_client


def create_client() -> Tradernet:
    """Create an authenticated Tradernet client."""
    return get_client()


def fetch_portfolio(client: Tradernet) -> dict[str, Any]:
    """Fetch portfolio positions from Tradernet.

    Uses account_summary() which calls the getPositionJson API endpoint.
    Returns the raw API response dict.
    """
    return client.account_summary()


def fetch_user_info(client: Tradernet) -> dict[str, Any]:
    """Fetch user account information.

    Uses user_info() which calls the GetAllUserTexInfo API endpoint.
    Returns the raw API response dict.
    """
    return client.user_info()


def fetch_orders(client: Tradernet, active_only: bool = True) -> dict[str, Any]:
    """Fetch orders from Tradernet.

    Args:
        client: Authenticated Tradernet client.
        active_only: If True, return only active orders.
    """
    return client.get_placed(active=active_only)


def fetch_quotes(client: Tradernet, symbols: list[str]) -> dict[str, Any]:
    """Fetch current quotes for a list of symbols.

    Args:
        client: Authenticated Tradernet client.
        symbols: List of ticker symbols.
    """
    return client.get_quotes(symbols)
