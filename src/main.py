import os
import threading

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.routes import router

PORT = int(os.environ.get("PORT", 8000))


def _warm_cache():
    """Pre-fetch market data on startup so first /scan request is fast."""
    try:
        from src.data import client
        from src.scanner.screener import get_default_universe
        symbols = get_default_universe()
        client.get_multi_bars(symbols, days=200)
        client.get_bars("SPY", days=200)
    except Exception:
        pass  # Non-fatal: cache warming is best-effort


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm cache in background thread so server starts accepting requests immediately
    threading.Thread(target=_warm_cache, daemon=True).start()
    yield


app = FastAPI(
    title="Momentum Signal Engine",
    description="Stock trading analysis platform for high-probability momentum setups",
    version="0.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
