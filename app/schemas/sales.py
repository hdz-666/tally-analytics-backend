from pydantic import BaseModel
from datetime import date


class MonthlySalesSchema(BaseModel):
    month: date
    item: str
    stock_group: str | None = None
    sold_qty: float
    sold_amount: float


class GroupSalesSchema(BaseModel):
    month: date
    stock_group: str
    sold_qty: float
    sold_amount: float


class TopMoverSchema(BaseModel):
    item: str
    stock_group: str | None = None
    total_qty: float
    total_amount: float
    months_active: int
