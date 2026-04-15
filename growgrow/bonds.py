"""Bond metadata loading and bond-specific calculations.

Metadata is maintained in bonds_metadata.yaml at the project root.
The Tradernet API returns Yield: 0 for all bonds — use coupon_rate from
the YAML file instead.
"""

from datetime import date
from pathlib import Path
from typing import Any

import yaml

BONDS_FILE = Path(__file__).parent.parent / "bonds_metadata.yaml"


def load_bond_metadata() -> dict[str, dict[str, Any]]:
    """Load bond metadata from bonds_metadata.yaml.

    Returns:
        Dict keyed by ticker. Empty dict if file not found.
    """
    if not BONDS_FILE.exists():
        return {}
    with BONDS_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def days_to_maturity(maturity_date_str: str) -> int:
    """Calculate calendar days from today to maturity date.

    Args:
        maturity_date_str: ISO date string e.g. "2028-06-26".

    Returns:
        Days remaining. Negative if already matured.
    """
    maturity = date.fromisoformat(maturity_date_str)
    return (maturity - date.today()).days


def current_yield(coupon_rate: float, current_price: float, face_value: float) -> float | None:
    """Current yield = annual coupon income / current price × 100.

    This is simpler than YTM — it ignores price appreciation to par at maturity.
    Useful for quick comparison of income return across bonds.

    Args:
        coupon_rate: Annual coupon rate as % (e.g. 21.0 for 21%).
        current_price: Current price in currency per unit.
        face_value: Par/face value per unit.

    Returns:
        Current yield as %, or None if current_price is 0.
    """
    if current_price == 0 or face_value == 0:
        return None
    annual_coupon = coupon_rate / 100 * face_value
    return (annual_coupon / current_price) * 100


def annual_income(coupon_rate: float, face_value: float, quantity: float) -> float:
    """Total annual coupon income for a position.

    Args:
        coupon_rate: Annual coupon rate as % (e.g. 21.0 for 21%).
        face_value: Par/face value per unit.
        quantity: Number of units held.

    Returns:
        Annual coupon income in currency.
    """
    return coupon_rate / 100 * face_value * quantity
