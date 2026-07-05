from dataclasses import dataclass
from decimal import Decimal


@dataclass
class StockItem:
    name: str
    stock_group: str
    closing_balance: Decimal
    closing_value: Decimal
    closing_rate: Decimal


@dataclass
class StockGroup:
    name: str
    parent: str | None
