from pydantic import BaseModel


class StockItemSchema(BaseModel):
    name: str
    stock_group: str | None = None
    closing_balance: float
    # None when withheld from a company exec.
    closing_value: float | None = None
    closing_rate: float | None = None


class StockGroupSchema(BaseModel):
    name: str
    parent: str | None = None


class StockSummarySchema(BaseModel):
    total_items: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
