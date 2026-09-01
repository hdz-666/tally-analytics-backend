from pydantic import BaseModel


class AreaSalesSchema(BaseModel):
    area: str
    lat: float
    lon: float
    state: str | None = None
    resolution_level: str
    sold_qty: float
    sold_amount: float
    client_count: int


class AreaClientSchema(BaseModel):
    party_name: str
    sold_qty: float
    sold_amount: float
    item_count: int


class ClientItemSchema(BaseModel):
    item: str
    stock_group: str | None = None
    sold_qty: float
    sold_amount: float


class PincodeSalesSchema(BaseModel):
    pincode: str
    area: str
    state: str | None = None
    sold_qty: float
    sold_amount: float
    client_count: int
