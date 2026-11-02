from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.core.auth import ADMIN, COMPANY_EXEC, EXECUTIVE, require_roles
from app.routers import stock, sales, purchases, forecast, ledger, users


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

# Every router needs a signed-in user with a role; each list below is who
# may reach it. Finer per-endpoint rules live in the routers themselves.
_all_roles = [Depends(require_roles(ADMIN, EXECUTIVE, COMPANY_EXEC))]
_staff = [Depends(require_roles(ADMIN, EXECUTIVE))]
_admin = [Depends(require_roles(ADMIN))]

app.include_router(
    stock.router, prefix="/api/stock", tags=["stock"], dependencies=_all_roles
)
app.include_router(
    sales.router, prefix="/api/sales", tags=["sales"], dependencies=_all_roles
)
app.include_router(
    purchases.router,
    prefix="/api/purchases",
    tags=["purchases"],
    dependencies=_admin,
)
app.include_router(
    forecast.router,
    prefix="/api/forecast",
    tags=["forecast"],
    dependencies=_staff,
)
app.include_router(
    ledger.router,
    prefix="/api/ledger",
    tags=["ledger"],
    dependencies=_admin,
)
app.include_router(
    users.me_router, prefix="/api/me", tags=["users"], dependencies=_all_roles
)
app.include_router(
    users.router, prefix="/api/users", tags=["users"], dependencies=_admin
)


@app.get("/health")
async def health():
    return {"status": "ok"}
