"""Tests for snapshot persistence and comparison."""

from datetime import datetime

import pytest

from growgrow.portfolio import PortfolioSummary, Position
from growgrow.snapshot import (
    _round_position_row,
    compare_snapshots,
    load_snapshot,
    save_snapshot,
)


@pytest.fixture
def sample_summary():
    return PortfolioSummary(
        positions=[
            Position("AAPL.US", "Apple Inc", 10, 150.00, 175.50, "USD"),
            Position("GOOGL.US", "Alphabet", 5, 2800.00, 2950.00, "USD"),
        ],
        timestamp=datetime(2026, 3, 17, 14, 30),
    )


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Override DATA_DIR to use a temp directory."""
    import growgrow.config as config_mod
    import growgrow.snapshot as snap_mod

    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(snap_mod, "ensure_data_dir", lambda: tmp_path)
    return tmp_path


class TestRounding:
    def test_usd_rounded_to_1_decimal(self):
        row = {"currency": "USD", "avg_price": 150.2567, "current_price": 175.555,
               "cost_basis": 1502.567, "market_value": 1755.55, "unrealized_pnl": 252.983,
               "pnl_pct": 16.834}
        result = _round_position_row(row)
        assert result["avg_price"] == 150.3
        assert result["current_price"] == 175.6
        assert result["market_value"] == 1755.5
        assert result["pnl_pct"] == 16.8

    def test_kzt_rounded_to_integer(self):
        row = {"currency": "KZT", "avg_price": 5033.2105, "current_price": 4531.0,
               "cost_basis": 704649.47, "market_value": 634340.0, "unrealized_pnl": -70309.47,
               "pnl_pct": -9.977}
        result = _round_position_row(row)
        assert result["avg_price"] == 5033
        assert result["cost_basis"] == 704649
        assert result["unrealized_pnl"] == -70309
        assert result["pnl_pct"] == -10.0

    def test_weight_pct_always_1_decimal(self):
        row = {"currency": "KZT", "avg_price": 1000, "current_price": 1000,
               "cost_basis": 1000, "market_value": 1000, "unrealized_pnl": 0,
               "pnl_pct": 0, "weight_pct": 38.912}
        result = _round_position_row(row)
        assert result["weight_pct"] == 38.9


class TestSaveAndLoad:
    def test_save_creates_csv(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        assert filepath.exists()
        assert filepath.suffix == ".csv"
        assert "portfolio_2026-03-17_1430" in filepath.name

    def test_csv_has_metadata_header(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        content = filepath.read_text()
        assert "# snapshot_date:" in content
        assert "# positions: 2" in content

    def test_csv_has_subtotal_rows(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        content = filepath.read_text()
        assert "SUBTOTAL_EQUITY_USD" in content

    def test_csv_has_weight_pct_column(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        content = filepath.read_text()
        assert "weight_pct" in content

    def test_roundtrip_skips_subtotals(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        loaded = load_snapshot(filepath)
        assert loaded.position_count == 2  # subtotals not counted as positions

    def test_roundtrip(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        loaded = load_snapshot(filepath)
        assert loaded.positions[0].ticker == "AAPL.US"
        assert loaded.positions[0].current_price == pytest.approx(175.5, abs=0.1)
        assert loaded.positions[1].quantity == 5

    def test_timestamp_from_filename(self, sample_summary, tmp_data_dir):
        filepath = save_snapshot(sample_summary)
        loaded = load_snapshot(filepath)
        assert loaded.timestamp.year == 2026
        assert loaded.timestamp.month == 3
        assert loaded.timestamp.day == 17


class TestCompareSnapshots:
    def test_no_changes(self):
        positions = [Position("AAPL.US", "Apple", 10, 150.0, 175.0)]
        old = PortfolioSummary(positions=positions)
        new = PortfolioSummary(positions=positions)
        changes = compare_snapshots(new, old)
        assert len(changes) == 1
        assert changes[0].status == "unchanged"

    def test_added_position(self):
        old = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
            ]
        )
        new = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
                Position("MSFT.US", "Microsoft", 5, 300.0, 310.0),
            ]
        )
        changes = compare_snapshots(new, old)
        added = [c for c in changes if c.status == "added"]
        assert len(added) == 1
        assert added[0].ticker == "MSFT.US"

    def test_removed_position(self):
        old = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
                Position("MSFT.US", "Microsoft", 5, 300.0, 310.0),
            ]
        )
        new = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
            ]
        )
        changes = compare_snapshots(new, old)
        removed = [c for c in changes if c.status == "removed"]
        assert len(removed) == 1
        assert removed[0].ticker == "MSFT.US"

    def test_price_change(self):
        old = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
            ]
        )
        new = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 185.0),
            ]
        )
        changes = compare_snapshots(new, old)
        assert changes[0].status == "changed"
        assert changes[0].price_change_pct == pytest.approx(5.714, rel=1e-2)

    def test_quantity_change(self):
        old = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 10, 150.0, 175.0),
            ]
        )
        new = PortfolioSummary(
            positions=[
                Position("AAPL.US", "Apple", 15, 150.0, 175.0),
            ]
        )
        changes = compare_snapshots(new, old)
        assert changes[0].status == "changed"
        assert changes[0].old_quantity == 10
        assert changes[0].new_quantity == 15
