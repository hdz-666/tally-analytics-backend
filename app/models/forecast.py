from dataclasses import dataclass
from decimal import Decimal
from datetime import date


@dataclass
class ForecastPoint:
    item: str
    stock_group: str
    forecast_month: date
    forecast_qty: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


@dataclass
class ReorderAlert:
    item: str
    stock_group: str
    current_stock: Decimal
    reorder_point: Decimal
    reorder_qty: Decimal
    needs_reorder: bool
