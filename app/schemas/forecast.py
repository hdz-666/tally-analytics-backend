from pydantic import BaseModel
from datetime import date


class ForecastPointSchema(BaseModel):
    item: str
    stock_group: str | None = None
    forecast_month: date
    forecast_qty: float
    lower_bound: float
    upper_bound: float


class ReorderAlertSchema(BaseModel):
    item: str
    stock_group: str | None = None
    current_stock: float
    reorder_point: float
    reorder_qty: float
    needs_reorder: bool


class ForecastRunResponseSchema(BaseModel):
    items_processed: int
    message: str
