from dataclasses import dataclass
from decimal import Decimal
from datetime import date


@dataclass
class MonthlySales:
    month: date
    item: str
    sold_qty: Decimal
    sold_amount: Decimal


@dataclass
class GroupSales:
    month: date
    stock_group: str
    sold_qty: Decimal
    sold_amount: Decimal
