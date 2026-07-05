from pydantic import BaseModel


class StockItemSchema(BaseModel):
    name: str
    stock_group: str | None = None
    closing_balance: float
    closing_value: float
    closing_rate: float


class StockGroupSchema(BaseModel):
    name: str
    parent: str | None = None


class StockSummarySchema(BaseModel):
    total_items: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
