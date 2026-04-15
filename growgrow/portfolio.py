"""Portfolio data models and transformation logic.

Defines Position and PortfolioSummary dataclasses. Transforms raw API
responses into clean, typed structures with P&L calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Position:
    """A single portfolio position with P&L tracking."""

    ticker: str
    name: str
    quantity: float
    avg_price: float
    current_price: float
    currency: str = "USD"
    asset_type: str = "equity"  # "equity" or "bond"
    accrued_per_unit: float = 0.0  # bonds only: accrued interest per unit (API: accruedint_a)

    @property
    def cost_basis(self) -> float:
        """Total cost of the position."""
        return self.quantity * self.avg_price

    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss in currency terms."""
        return self.market_value - self.cost_basis

    @property
    def pnl_pct(self) -> float:
        """Unrealized P&L as a percentage. Returns 0.0 if cost_basis is zero."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def to_dict(self, weight_pct: float | None = None) -> dict[str, Any]:
        """Convert to dict for CSV serialization.

        Args:
            weight_pct: Optional pre-computed weight within currency group (%).
                        Requires PortfolioSummary context to calculate.
        """
        result: dict[str, Any] = {
            "ticker": self.ticker,
            "name": self.name,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "currency": self.currency,
            "asset_type": self.asset_type,
            "cost_basis": self.cost_basis,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "pnl_pct": self.pnl_pct,
        }
        if weight_pct is not None:
            result["weight_pct"] = weight_pct
        return result


@dataclass
class PortfolioSummary:
    """Aggregated portfolio with all positions and totals."""

    positions: list[Position] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_cost_basis(self) -> float:
        return sum(p.cost_basis for p in self.positions)

    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def total_unrealized_pnl(self) -> float:
        return self.total_market_value - self.total_cost_basis

    @property
    def total_pnl_pct(self) -> float:
        if self.total_cost_basis == 0:
            return 0.0
        return (self.total_unrealized_pnl / self.total_cost_basis) * 100

    @property
    def position_count(self) -> int:
        return len(self.positions)

    def weight(self, position: Position) -> float:
        """Calculate a position's weight within its currency group (%).

        Cross-currency weight is meaningless without FX conversion, so weight
        is calculated relative to all positions sharing the same currency.
        """
        currency_total = sum(
            p.market_value for p in self.positions if p.currency == position.currency
        )
        if currency_total == 0:
            return 0.0
        return (position.market_value / currency_total) * 100


def parse_positions(raw_data: dict[str, Any]) -> PortfolioSummary:
    """Transform raw API response from account_summary() into PortfolioSummary.

    The exact response shape from getPositionJson is not fully documented.
    This function handles the known structure and logs warnings for unknown fields.
    Adjust field mappings once we can inspect a real API response.

    Expected raw_data structure (best guess from API docs):
        {
            "ps": {  # positions
                "pos": [
                    {
                        "i": "AAPL.US",    # instrument/ticker
                        "n": "Apple Inc",  # name
                        "q": 10,           # quantity
                        "fv": 150.25,      # face value / avg price
                        "cur": "USD",      # currency
                        "lp": 175.50,      # last price
                        ...
                    },
                    ...
                ]
            }
        }

    If the structure doesn't match, returns an empty PortfolioSummary.
    """
    positions = []

    # Try to extract positions from known API response structures
    # Structure 1: nested under "ps" -> "pos"
    pos_list = _extract_positions_list(raw_data)

    for item in pos_list:
        pos = _parse_single_position(item)
        if pos:
            positions.append(pos)

    return PortfolioSummary(positions=positions)


def _extract_positions_list(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Try multiple known response structures to find the positions list."""
    # Unwrap top-level "result" envelope (actual Tradernet API response)
    if "result" in raw_data:
        raw_data = raw_data["result"]

    # Try: raw_data["ps"]["pos"]
    if "ps" in raw_data:
        ps = raw_data["ps"]
        if isinstance(ps, dict) and "pos" in ps:
            return ps["pos"] if isinstance(ps["pos"], list) else []
        if isinstance(ps, list):
            return ps

    # Try: raw_data["positions"]
    if "positions" in raw_data:
        val = raw_data["positions"]
        if isinstance(val, list):
            return val

    # Try: raw_data is itself a list
    if isinstance(raw_data, list):
        return raw_data

    # Try: iterate top-level values for any list of dicts
    for val in raw_data.values():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            return val

    return []


def _parse_single_position(item: dict[str, Any]) -> Position | None:
    """Parse a single position dict. Tries multiple field name conventions.

    Bond prices (bal_price_a, mkt_price) are expressed as % of par value.
    Equity prices are expressed in actual currency units.
    """
    ticker = item.get("i") or item.get("ticker") or item.get("symbol") or ""
    name = item.get("name") or item.get("n") or item.get("descr") or ticker
    quantity = float(item.get("q", 0) or item.get("quantity", 0) or 0)
    currency = item.get("curr") or item.get("cur") or item.get("currency") or "USD"
    # t=1: equity (stocks/ETFs), t=2: bond; default to equity
    asset_type = "bond" if item.get("t") == 2 else "equity"

    accrued_per_unit = 0.0
    if asset_type == "bond":
        # Bond prices are % of par — multiply by face value to get currency amount per unit
        face_val = float(item.get("face_val_a") or 1)
        avg_pct = float(item.get("bal_price_a") or item.get("price_a") or 0)
        cur_pct = float(item.get("mkt_price") or item.get("close_price") or 0)
        avg_price = avg_pct / 100 * face_val
        current_price = cur_pct / 100 * face_val
        accrued_per_unit = float(item.get("accruedint_a") or 0)
    else:
        # Equity prices are already in currency units
        avg_price = float(
            item.get("bal_price_a") or item.get("avg_price") or item.get("avgPrice") or 0
        )
        current_price = float(
            item.get("mkt_price") or item.get("lp")
            or item.get("current_price") or item.get("lastPrice") or 0
        )

    if not ticker or quantity == 0:
        return None

    return Position(
        ticker=ticker,
        name=name,
        quantity=quantity,
        avg_price=avg_price,
        current_price=current_price,
        currency=currency,
        asset_type=asset_type,
        accrued_per_unit=accrued_per_unit,
    )
