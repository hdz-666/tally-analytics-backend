from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.core.auth import get_current_user
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

_auth = [Depends(get_current_user)]

app.include_router(
    stock.router, prefix="/api/stock", tags=["stock"], dependencies=_auth
)
app.include_router(
    sales.router, prefix="/api/sales", tags=["sales"], dependencies=_auth
)
app.include_router(
    purchases.router,
    prefix="/api/purchases",
    tags=["purchases"],
    dependencies=_auth,
)
app.include_router(
    forecast.router, prefix="/api/forecast", tags=["forecast"], dependencies=_auth
)


@app.get("/health")
async def health():
    return {"status": "ok"}
