"""Tests for portfolio data models and parsing."""

import pytest

from growgrow.portfolio import PortfolioSummary, Position, _parse_single_position, parse_positions


@pytest.fixture
def sample_position():
    return Position(
        ticker="AAPL.US",
        name="Apple Inc",
        quantity=10,
        avg_price=150.00,
        current_price=175.50,
        currency="USD",
    )


@pytest.fixture
def sample_positions():
    return [
        Position("AAPL.US", "Apple Inc", 10, 150.00, 175.50, "USD"),
        Position("GOOGL.US", "Alphabet Inc", 5, 2800.00, 2950.00, "USD"),
        Position("MSFT.US", "Microsoft Corp", 20, 300.00, 310.00, "USD"),
    ]


class TestPosition:
    def test_cost_basis(self, sample_position):
        assert sample_position.cost_basis == 1500.00

    def test_market_value(self, sample_position):
        assert sample_position.market_value == 1755.00

    def test_unrealized_pnl(self, sample_position):
        assert sample_position.unrealized_pnl == 255.00

    def test_pnl_pct(self, sample_position):
        assert sample_position.pnl_pct == pytest.approx(17.0)

    def test_pnl_pct_zero_cost(self):
        pos = Position("X", "Test", 0, 0, 100.00)
        assert pos.pnl_pct == 0.0

    def test_negative_pnl(self):
        pos = Position("X", "Test", 10, 200.00, 180.00)
        assert pos.unrealized_pnl == -200.00
        assert pos.pnl_pct == pytest.approx(-10.0)

    def test_to_dict(self, sample_position):
        d = sample_position.to_dict()
        assert d["ticker"] == "AAPL.US"
        assert d["market_value"] == 1755.00
        assert d["unrealized_pnl"] == 255.00
        assert "pnl_pct" in d
        assert "weight_pct" not in d

    def test_to_dict_with_weight(self, sample_position):
        d = sample_position.to_dict(weight_pct=12.5)
        assert d["weight_pct"] == 12.5


class TestPortfolioSummary:
    def test_totals(self, sample_positions):
        summary = PortfolioSummary(positions=sample_positions)
        assert summary.total_cost_basis == 1500.00 + 14000.00 + 6000.00
        assert summary.total_market_value == 1755.00 + 14750.00 + 6200.00

    def test_total_pnl(self, sample_positions):
        summary = PortfolioSummary(positions=sample_positions)
        expected_pnl = (1755 + 14750 + 6200) - (1500 + 14000 + 6000)
        assert summary.total_unrealized_pnl == expected_pnl

    def test_position_count(self, sample_positions):
        summary = PortfolioSummary(positions=sample_positions)
        assert summary.position_count == 3

    def test_weight(self, sample_positions):
        summary = PortfolioSummary(positions=sample_positions)
        total_value = 1755 + 14750 + 6200
        expected_weight = (1755 / total_value) * 100
        assert summary.weight(sample_positions[0]) == pytest.approx(expected_weight, rel=1e-2)

    def test_empty_portfolio(self):
        summary = PortfolioSummary()
        assert summary.total_cost_basis == 0
        assert summary.total_market_value == 0
        assert summary.total_pnl_pct == 0.0


class TestBondPrices:
    def test_kzt_bond_price_conversion(self):
        """Bond prices are % of par — must multiply by face_val to get KZT per unit."""
        item = {
            "i": "MFRFB19.KZ", "name": "МФО R-Finance", "q": 320,
            "t": 2, "curr": "KZT",
            "face_val_a": 1000, "bal_price_a": 95.48, "mkt_price": 91.5,
        }
        pos = _parse_single_position(item)
        assert pos is not None
        assert pos.asset_type == "bond"
        assert pos.avg_price == pytest.approx(954.8)
        assert pos.current_price == pytest.approx(915.0)
        assert pos.market_value == pytest.approx(320 * 915.0)

    def test_usd_bond_price_conversion(self):
        """USD bond with face=100: prices are still % of par."""
        item = {
            "i": "FFSPC3.0527.AIX.KZ", "name": "Freedom Finance SPC", "q": 10,
            "t": 2, "curr": "USD",
            "face_val_a": 100, "bal_price_a": 100.88, "mkt_price": 100.7,
        }
        pos = _parse_single_position(item)
        assert pos is not None
        assert pos.avg_price == pytest.approx(100.88)
        assert pos.current_price == pytest.approx(100.7)

    def test_equity_price_not_converted(self):
        """Equity prices are already in currency units, no conversion."""
        item = {
            "i": "HSBK.KZ", "name": "Народный банк", "q": 3740,
            "t": 1, "curr": "KZT",
            "bal_price_a": 302.2, "mkt_price": 387.41, "face_val_a": 1,
        }
        pos = _parse_single_position(item)
        assert pos is not None
        assert pos.asset_type == "equity"
        assert pos.avg_price == pytest.approx(302.2)
        assert pos.current_price == pytest.approx(387.41)


class TestParsePositions:
    def test_parse_tradernet_format(self):
        raw = {
            "ps": {
                "pos": [
                    {
                        "i": "AAPL.US",
                        "name": "Apple Inc",
                        "q": 10,
                        "t": 1,
                        "bal_price_a": 150.0,
                        "mkt_price": 175.5,
                        "curr": "USD",
                    },
                    {
                        "i": "MSFT.US",
                        "name": "Microsoft",
                        "q": 5,
                        "t": 1,
                        "bal_price_a": 300.0,
                        "mkt_price": 310.0,
                        "curr": "USD",
                    },
                ]
            }
        }
        summary = parse_positions(raw)
        assert summary.position_count == 2
        assert summary.positions[0].ticker == "AAPL.US"
        assert summary.positions[0].current_price == 175.5

    def test_parse_flat_list(self):
        raw = {
            "positions": [
                {
                    "ticker": "AAPL.US",
                    "name": "Apple",
                    "quantity": 10,
                    "avg_price": 150.0,
                    "current_price": 175.0,
                },
            ]
        }
        summary = parse_positions(raw)
        assert summary.position_count == 1

    def test_parse_empty(self):
        summary = parse_positions({})
        assert summary.position_count == 0

    def test_skip_zero_quantity(self):
        raw = {
            "positions": [
                {
                    "ticker": "AAPL.US",
                    "name": "Apple",
                    "quantity": 0,
                    "avg_price": 150.0,
                    "current_price": 175.0,
                },
            ]
        }
        summary = parse_positions(raw)
        assert summary.position_count == 0
