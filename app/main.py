from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.routers import stock, sales, purchases, forecast


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title="Tally Analytics API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(sales.router, prefix="/api/sales", tags=["sales"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["purchases"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["forecast"])


@app.get("/health")
async def health():
    return {"status": "ok"}
