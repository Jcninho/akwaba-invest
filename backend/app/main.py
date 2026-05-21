import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.firebase import init_firebase
from app.api.routes import admin, auth, stocks, portfolio, alerts, payments

logger = logging.getLogger(__name__)

app = FastAPI(title="Akwaba Invest API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(stocks.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    init_firebase()
    logger.info("Akwaba Invest API started")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0", "env": settings.APP_ENV}
