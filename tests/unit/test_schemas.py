from datetime import date
import pytest
from pydantic import ValidationError

from app.schemas.sales import MonthlySalesSchema, GroupSalesSchema, TopMoverSchema
from app.schemas.forecast import (
    ForecastPointSchema,
    ReorderAlertSchema,
    ForecastRunResponseSchema,
)
from app.schemas.stock import StockItemSchema, StockGroupSchema, StockSummarySchema
from app.schemas.ledger import LedgerHealthSchema, PnlMonthlySchema


# ── Sales schemas ────────────────────────────────────────────────────────────

class TestMonthlySalesSchema:
    def test_valid(self):
        s = MonthlySalesSchema(
            month=date(2024, 1, 1),
            item="Widget A",
            stock_group="Electronics",
            sold_qty=10.5,
            sold_amount=1050.0,
        )
        assert s.item == "Widget A"
        assert s.sold_qty == 10.5

    def test_stock_group_optional(self):
        s = MonthlySalesSchema(
            month=date(2024, 1, 1),
            item="Widget A",
            stock_group=None,
            sold_qty=10.0,
            sold_amount=100.0,
        )
        assert s.stock_group is None

    def test_invalid_month(self):
        with pytest.raises(ValidationError):
            MonthlySalesSchema(
                month="not-a-date", item="X", sold_qty=1.0, sold_amount=1.0
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            MonthlySalesSchema(month=date(2024, 1, 1), sold_qty=1.0, sold_amount=1.0)


class TestGroupSalesSchema:
    def test_valid(self):
        s = GroupSalesSchema(
            month=date(2024, 1, 1),
            stock_group="Electronics",
            sold_qty=100.0,
            sold_amount=10000.0,
        )
        assert s.stock_group == "Electronics"
        assert s.sold_amount == 10000.0


class TestTopMoverSchema:
    def test_valid_with_group(self):
        s = TopMoverSchema(
            item="Widget A",
            stock_group="Electronics",
            total_qty=50.0,
            total_amount=5000.0,
            months_active=6,
        )
        assert s.months_active == 6

    def test_stock_group_optional(self):
        s = TopMoverSchema(
            item="Widget A",
            stock_group=None,
            total_qty=10.0,
            total_amount=100.0,
            months_active=2,
        )
        assert s.stock_group is None


# ── Forecast schemas ─────────────────────────────────────────────────────────

class TestForecastPointSchema:
    def test_valid(self):
        s = ForecastPointSchema(
            item="Widget A",
            stock_group="Electronics",
            forecast_month=date(2024, 7, 1),
            forecast_qty=12.5,
            lower_bound=8.0,
            upper_bound=17.0,
        )
        assert s.forecast_qty == 12.5
        assert s.lower_bound == 8.0

    def test_stock_group_optional(self):
        s = ForecastPointSchema(
            item="Widget A",
            forecast_month=date(2024, 7, 1),
            forecast_qty=5.0,
            lower_bound=2.0,
            upper_bound=8.0,
        )
        assert s.stock_group is None


class TestReorderAlertSchema:
    def test_needs_reorder_true(self):
        s = ReorderAlertSchema(
            item="Widget A",
            current_stock=10.0,
            reorder_point=15.0,
            reorder_qty=30.0,
            needs_reorder=True,
        )
        assert s.needs_reorder is True

    def test_needs_reorder_false(self):
        s = ReorderAlertSchema(
            item="Widget A",
            current_stock=100.0,
            reorder_point=15.0,
            reorder_qty=30.0,
            needs_reorder=False,
        )
        assert s.needs_reorder is False


class TestForecastRunResponseSchema:
    def test_valid(self):
        s = ForecastRunResponseSchema(items_processed=7, message="Done for 7 items")
        assert s.items_processed == 7
        assert "7" in s.message


# ── Stock schemas ────────────────────────────────────────────────────────────

class TestStockItemSchema:
    def test_valid(self):
        s = StockItemSchema(
            name="Widget A",
            stock_group="Electronics",
            closing_balance=100.0,
            closing_value=5000.0,
            closing_rate=50.0,
        )
        assert s.closing_rate == 50.0

    def test_group_optional(self):
        s = StockItemSchema(
            name="Widget A",
            closing_balance=100.0,
            closing_value=5000.0,
            closing_rate=50.0,
        )
        assert s.stock_group is None


class TestStockGroupSchema:
    def test_with_parent(self):
        s = StockGroupSchema(name="Sub Group", parent="Root Group")
        assert s.parent == "Root Group"

    def test_root_group_no_parent(self):
        s = StockGroupSchema(name="Root Group", parent=None)
        assert s.parent is None


class TestStockSummarySchema:
    def test_valid(self):
        s = StockSummarySchema(
            total_items=100,
            total_value=50000.0,
            low_stock_count=5,
            out_of_stock_count=2,
        )
        assert s.total_items == 100
        assert s.out_of_stock_count == 2

    def test_invalid_total_items_type(self):
        with pytest.raises(ValidationError):
            StockSummarySchema(
                total_items="not-an-int",
                total_value=50000.0,
                low_stock_count=5,
                out_of_stock_count=2,
            )

    def test_zero_counts(self):
        s = StockSummarySchema(
            total_items=0,
            total_value=0.0,
            low_stock_count=0,
            out_of_stock_count=0,
        )
        assert s.total_value == 0.0


# ── Ledger schemas ───────────────────────────────────────────────────────────

class TestLedgerHealthSchema:
    def _make(self, **kwargs):
        defaults = dict(
            customer="Customer A",
            outstanding_amount=10000.0,
            credit_days=30,
            dso_estimate=None,
            revenue_12m=100000.0,
            last_invoice_date=date(2024, 6, 1),
            last_receipt_date=None,
            days_since_last_receipt=15,
            has_overdue=False,
            total_invoices=10,
            total_receipts=8,
            total_invoiced=50000.0,
            total_received=40000.0,
            score_dso=25.0,
            score_overdue=25.0,
            score_recency=20.0,
            score_engagement=15.0,
            score_balance_ratio=10.0,
            health_score=95.0,
            health_rag="Green",
        )
        defaults.update(kwargs)
        return LedgerHealthSchema(**defaults)

    def test_valid(self):
        s = self._make()
        assert s.customer == "Customer A"
        assert s.health_score == 95.0
        assert s.has_overdue is False

    def test_optional_dates_null(self):
        s = self._make(last_receipt_date=None, dso_estimate=None)
        assert s.last_receipt_date is None
        assert s.dso_estimate is None

    def test_health_rag_values(self):
        for rag in ("Green", "Amber", "Red"):
            s = self._make(health_rag=rag)
            assert s.health_rag == rag


class TestPnlMonthlySchema:
    def test_valid_with_margins(self):
        s = PnlMonthlySchema(
            month=date(2024, 1, 1),
            revenue=100000.0,
            cogs=60000.0,
            gross_profit=40000.0,
            gross_margin_pct=40.0,
            fixed_costs=10000.0,
            loan_interest=2000.0,
            total_overhead=12000.0,
            net_profit=28000.0,
            net_margin_pct=28.0,
        )
        assert s.gross_profit == 40000.0
        assert s.net_margin_pct == 28.0

    def test_optional_margins_default_to_none(self):
        s = PnlMonthlySchema(
            month=date(2024, 1, 1),
            revenue=0.0,
            cogs=0.0,
            gross_profit=0.0,
            fixed_costs=0.0,
            loan_interest=0.0,
            total_overhead=0.0,
            net_profit=0.0,
        )
        assert s.gross_margin_pct is None
        assert s.net_margin_pct is None
